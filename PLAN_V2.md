# AR Floor Plan Visualizer — Plan v2: flexible plans and whole buildings

Builds on [PLAN.md](PLAN.md) (v1, done through M8) and [progress.md](progress.md).
Two goals:

1. **Flexible single-floor reconstruction**: plans that aren't one closed rectangle, such as L-shapes,
   angled walls and bays, open-plan halls, porches and sit-outs, stub walls, columns, and **staircases**.
2. **Whole-building reconstruction**: one sheet with several drawings (ground, first and terrace plans,
   section, elevation), or one photo per floor, turned into stacked, aligned levels joined by stairs.
   The user picks the plan type when creating a plan.

Reference inputs: the imperial ground-floor plan (`samples/real/ground_floor.png`) and the metric
full-building sheet (`samples/real/building_sheet.png`). Both get added to `backend/samples/real/`.

---

## 1. Why v1 struggles with real plans

| v1 assumption | Where | What happens on the real ground-floor plan |
|---|---|---|
| Rooms tile the footprint, and every room edge is a wall | `walls.py` | The open L-shaped hall, the porch and the sit-out get walls on every edge. Open-plan boundaries become solid walls, and gaps between rooms become missing walls |
| All x and all y values are clustered together on one global grid (0.15 m tolerance) | `normalize.py` | Angled walls get pulled sideways. Two parallel walls less than 0.15 m apart merge into one |
| Edges only share a wall if their lines match after rounding to 3 decimals | `walls.py` `Line.key` | Shared angled edges produce two overlapping walls |
| A room's walls only come from its own outline | spec shape | Stub walls, wing walls and free-standing columns can't be expressed |
| Only `door` / `window` | `OpeningType` | Archways and plain wall gaps (the 2'-6" and 3'-6" gaps) turn into doors or get dropped |
| No stair concept | spec + Unity | A staircase becomes a "room" with four walls, or disappears |
| The LLM measures in metres directly | prompts | The plan is in feet and inches and printed dimensions are what count. Positions are off by 0.25–0.4 m even on the clean sample |
| One plan per image, with the whole image downscaled to 2048 px | `imaging.py` | A building sheet is about 6 drawings. Each floor ends up at roughly 600 px and the text is unreadable |

**The fix:** walls become first-class data instead of being derived from rooms. Rooms become labelled
regions found from the wall graph, stairs and other features get their own types, and scale is
computed in code from the dimension strings the LLM reads.

---

## 2. Data contract v2

### 2.1 Coordinates
The LLM works in **pixel coordinates of the image it is sent**. The prompt states the width and height
(e.g. 1843×2048), with the origin at top-left and +y down. Models point at things on the page more
reliably than they convert to metres in their head. The backend converts pixels to metres using a
scale derived from dimension annotations (§3.2).

### 2.2 `FloorSpec` (LLM output for one floor; replaces `PlanSpec`)
```jsonc
{
  "level_name": "Ground floor",
  "walls": [
    { "id": "w1", "start": {"x": 148, "y": 118}, "end": {"x": 630, "y": 118},
      "kind": "exterior",                 // exterior | interior | partition | low | parapet
      "thickness_px": 14 }
  ],
  "openings": [
    { "id": "o1", "type": "door", "wall": "w1", "position": {"x": 410, "y": 118}, "width_px": 52 }
    // type: door | sliding_door | window | opening (archway / plain gap)
  ],
  "rooms": [
    { "id": "r1", "name": "Living", "type": "living", "label": {"x": 380, "y": 450},
      "outdoor": false, "polygon": null }     // polygon only for areas without enclosing walls
  ],
  "stairs": [
    { "id": "s1", "direction": "up",           // up | down (as drawn on this floor)
      "flights": [ { "start": {...}, "end": {...}, "width_px": 60, "risers": 9, "via": null } ],
      "landings": [ [ {...}, {...}, {...}, {...} ] ] }
  ],
  "columns": [ { "position": {...}, "size_px": 12 } ],
  "dimensions": [
    { "text": "15'-3\"", "start": {"x": 220, "y": 510}, "end": {"x": 448, "y": 510} }
  ],
  "notes": "..."
}
```
- `room.type` adds `staircase`, `porch`, `terrace`, `store`, `toilet`, `garage` to the v1 set.
- `flight.via`, when set, makes a flight curved (the arc through start, via and end). This covers
  the curved stair on the first floor of the building sheet.
- `rooms[].label` is required and `polygon` is nullable, so most rooms come out of the wall graph (§3.3).

### 2.3 `BuildingSpec` (whole building) and the single-floor case
```jsonc
{
  "kind": "building",                 // "floor" for a single plan: one level, same code paths
  "levels": [
    { "index": 0, "name": "Ground floor", "elevation": 0.0, "height": 3.0,
      "slab": 0.15, "offset": {"x": 0, "y": 0}, "floor": { /* FloorSpec in metres */ } }
  ],
  "roof": { "parapet_height": 1.0, "hip_roofs": [ { "polygon": [...], "ridge_height": 1.8 } ] },
  "notes": "Heights from Section AA: 3.0 m floor to floor."
}
```
The backend stores specs **in metres** after conversion, and edits operate on metres. Only extraction
uses pixels.

### 2.4 `BuildingGeometry` (what Unity renders)
```jsonc
{
  "bounds": {...},
  "levels": [
    { "index": 0, "name": "Ground floor", "elevation": 0.0, "height": 3.0,
      "rooms": [...], "walls": [...],            // same shapes as v1, plus wall.height / wall.base
      "slab": { "outline": [...], "holes": [[...]] },   // floor slab with stair voids
      "stairs": [ { "steps": [ { "corners": [4 pts], "bottom": 0.0, "top": 0.17 } ], "landings": [...],
                    "railings": [[...]] } ],
      "columns": [...] }
  ],
  "roofs": [ { "kind": "hip", "outline": [...], "ridge": [...], "height": 1.8 } ]
}
```
Steps are pre-computed boxes, so Unity doesn't need stair logic: it extrudes quads just like wall pieces.

### 2.5 Compatibility
- `PlanRecord` gets `kind: "floor" | "building"` and holds a `BuildingResponse`
  (`spec`, `geometry`, `warnings`).
- `store.py` migrates v1 records on read: v1 `PlanSpec` becomes one level, and walls are derived from
  rooms with the existing `walls.py`, which is kept as the fallback for specs without walls (including
  the hand-written sample).
- The Unity `PlanGeometry` becomes `LevelGeometry`, wrapped in `BuildingGeometry`. The bundled sample
  JSON gets regenerated.

---

## 3. Backend pipeline v2

```
image ─► (building) layout pass ─► crop + rotate each drawing at full resolution
      ─► per-floor extraction (parallel)  ─► scale ─► wall graph ─► rooms ─► stairs
      ─► (building) section/elevation pass for heights ─► level alignment ─► geometry
```

### 3.1 New module layout
```
src/floorplan/
├─ llm/
│  ├─ client.py          # + extract_floor(image, size), read_sheet(image), read_heights(image)
│  └─ prompts.py         # FLOOR_RULES, SHEET_RULES, HEIGHT_RULES, EDIT rules per level
├─ geometry/
│  ├─ scale.py           # parse dimension strings (ft-in, m, cm, mm) → robust metres/pixel
│  ├─ wallgraph.py       # snap, extend/trim to junctions, split at intersections, dedupe
│  ├─ regions.py         # polygonize the wall graph, assign room labels, find outdoor/exterior
│  ├─ orient.py          # replaces global clustering: dominant-angle snap per wall + offset merge
│  ├─ stairs.py          # flights/landings → step boxes, railings, slab voids
│  ├─ align.py           # stack levels: stair + outline matching
│  ├─ walls.py           # v1 room-edge derivation, kept as fallback
│  ├─ openings.py        # attach by wall id first, then by nearest wall
│  └─ build.py           # BuildingSpec → BuildingGeometry
├─ sheet.py              # crop/rotate drawings from the full-resolution upload
└─ jobs.py               # background parse jobs with stage reporting
```

### 3.2 Scale (`scale.py`)
- Parse each `dimensions[].text`: `15'-3"`, `15'3"`, `4'-10"`, `3.5 m`, `350`, `350 cm`, `3500 mm`.
  Unitless numbers use the unit most common on the sheet. The building sheet says "all dimensions in cm".
- metres/pixel = parsed length ÷ pixel length of each annotation. Take the **median**, and flag any
  annotation more than 8% off as a warning ("dimension 7'-6\" disagrees with the rest").
- Fallbacks, in order: the scale bar or note (`SCALE 1:100` only helps if the DPI is known, so it is
  ignored), the median door width = 0.9 m, then the LLM's own estimate. The method used goes into `notes`.

### 3.3 Wall graph and rooms (`orient.py`, `wallgraph.py`, `regions.py`)
1. **Orientation snap.** Build a length-weighted histogram of wall angles mod 180°. The peaks are the
   plan's dominant directions (0°/90° plus e.g. 45° for the bay walls). Each wall within 4° of a
   peak gets rotated onto it about its midpoint; other walls stay as drawn.
2. **Offset merge.** Among walls with the same direction, merge collinear ones whose offsets differ
   by less than half a wall thickness and whose spans touch or overlap. Parallel walls further apart
   stay separate, which fixes v1's global 0.15 m clustering.
3. **Junctions.** Snap endpoints within 0.25 m to the nearest endpoint, or project them onto a
   nearby wall (T-junction). Extend or trim dangling ends that are within 0.3 m of another wall.
   Ends that stay free are **stub walls**, which is fine.
4. **Split** walls at every intersection to get a planar graph.
5. **Regions.** Run `shapely.polygonize` on the wall centrelines. Each label point goes to the face
   that contains it:
   - one label → that face is the room;
   - two labels in one face (open-plan living/dining) → one floor region and two labels, using the
     first label's type;
   - a label in no face, or in the unbounded face → use the LLM polygon, or failing that a 2.5 m
     square around the label, with a warning;
   - faces with no label and an area under 1.5 m² → shafts/ducts, left out;
   - larger unlabelled faces → `other`.
   `outdoor` rooms (porch, sit-out, terrace) come from their LLM polygon, get an outdoor floor
   material, and no walls are added around them.
6. **Exterior flag.** A wall is exterior if, sampling ±0.3 m along its normal at the midpoint, one
   side falls in no indoor region. This picks the material and the default thickness, unless the
   LLM's `kind` says otherwise.
7. **Thickness.** `thickness_px × scale`, clamped to 0.075–0.35 m. Missing values use the kind's
   default: 0.23 exterior, 0.115 interior (Indian brick sizes), 0.075 partition.

### 3.4 Openings
- If `opening.wall` is a valid id, project onto that wall. Otherwise use the v1 nearest-wall search.
- `opening` (archway/gap) gets head = wall height (a full gap) or 2.1 m. `sliding_door` gets a wider
  frame and split glass in Unity.
- Wall splitting in step 3.3.4 can cut a wall under an opening. Openings are attached **after** the
  split and may straddle a split point. In that case the opening goes on the longer piece and the
  other piece is trimmed back.

### 3.5 Stairs (`stairs.py`)
- Total rise = level height + slab. Risers are spread over the flights in proportion to their counts.
  Riser height is `rise / Σrisers`, and a warning is raised if it falls outside 0.14–0.20 m.
- Each flight becomes step boxes along start → end (or along the arc through `via`), each step
  `width` wide. Landings become flat slabs at the cumulative height.
- Railings are polylines along the open side(s) of each flight: sides not within 0.1 m of a wall.
- **Single floor:** a stair marked `up` rises to the ceiling. A stair marked `down` is drawn as a
  stair well (a void) with a railing.
- **Building:** an `up` stair on level *n* is paired with the `down` stair on level *n+1* that
  overlaps it most after alignment. The upper stair's footprint becomes a hole in level *n+1*'s slab,
  and only the lower one produces steps.

### 3.6 Whole-building extraction
1. **Sheet pass** (`read_sheet`, one LLM call on a 2048 px version of the sheet). Returns every
   drawing as `{kind: floor_plan | section | elevation | site | schedule | title, title, level_index,
   bbox_px, rotation: 0|90|180|270}`. The example sheet is rotated 90°, so rotation matters.
2. **Crop** each `floor_plan` and `section`/`elevation` from the **full-resolution upload**, rotate it
   upright, add 3% padding, and downscale to ≤ 2048 px. The upload limit stays at 15 MB, and the
   stored image keeps full resolution for building sheets (`stored_image_side` per kind).
3. **Per-floor extraction**, one call per floor plan, run in parallel (`asyncio.gather` with the
   async OpenAI client). Each call gets the same `FLOOR_RULES` plus "this is level *n*: *title*".
4. **Heights pass** (`read_heights`) on the section and elevation crops: floor-to-floor heights,
   slab thickness, parapet height, and the shape and height of any sloped roof. If there is no
   section, default to 3.0 m floor to floor, a 0.15 m slab and a 1.0 m parapet.
5. **Terrace / roof level.** A plan whose title says terrace or roof becomes a roof level: walls
   become parapets (`low`, 1.0 m), the stair headroom room keeps full-height walls, and hip roofs
   from the plan's hatched roof areas become roof meshes.
6. **Alignment** (`align.py`). For each level *n+1*, find the translation (and a 0/90/180/270
   rotation, in case crops disagree) that best overlays it on level *n*. Candidates: paired stair
   centres, outline bounding-box corners, and the section-line markers if present. Score =
   length of exterior walls that coincide within 0.15 m. Below 40% coincidence, flag a warning and
   fall back to aligning bounding-box centres.
7. **Multiple photos** (one per floor) skip steps 1–2. The level order comes from each image's title
   ("FIRST FLOOR PLAN"), falling back to the order the photos were picked.

### 3.7 Jobs and endpoints
A building parse is 3–6 LLM calls (roughly 60–100 s even in parallel), longer than a safe HTTP wait on
a phone. So parsing moves to background jobs:

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/plans/parse` | multipart `image`, `kind=floor\|building` | `202 {job_id}` |
| POST | `/plans/parse` | multipart `images[]` (several), `kind=building` | `202 {job_id}` |
| GET | `/jobs/{id}` | — | `{state, stage, progress, plan_id?, error?}` |
| POST | `/plans/{id}/edit` | `{instruction, level?}` | `PlanRecord` (sync; one level at a time) |

The other v1 endpoints stay. `stage` reports the real work (e.g. "Reading sheet", "Ground floor",
"First floor", "Aligning floors"), so the progress card stops faking its stages.

### 3.8 Edits
The edit call gets the whole `BuildingSpec` **summary** (levels, room names, stair ids) plus the full
`FloorSpec` of the target level. That level is the one picked in the AR level picker, or the LLM
chooses it from the instruction ("add a window to the first-floor bedroom"). The LLM returns that
level's `FloorSpec` in metres, and the rest of the building is left unchanged.

---

## 4. Unity

### 4.1 Core / Runtime
| Change | Files |
|---|---|
| `BuildingGeometry`, `LevelGeometry`, `StairData`, `SlabData`, `RoofData` + JSON round-trip tests | `Core/Data/` |
| `PlanMeshBuilder.Slab(outline, holes)` using the triangulator with holes (bridge holes into the outer ring for ear clipping) | `Core/Geometry/PolygonTriangulator.cs`, `PlanMeshBuilder.cs` |
| `PlanMeshBuilder.Stairs(stairs)`: step boxes, landings, railing posts + handrail | `PlanMeshBuilder.cs` |
| `PlanMeshBuilder.Walls` honours `wall.base` / `wall.height` (parapets, low walls) | `WallSlicer.cs` |
| Columns as boxes; hip roofs as four-sided pyramids/prisms from outline + ridge | `PlanMeshBuilder.cs` |
| `FloorPlanBuilder` → `BuildingBuilder`: builds one `LevelModel` per level under a `BuildingModel` root, at `elevation` | `Runtime/Model/` |
| `BuildingModel`: `VisibleUpTo(level)` (dollhouse cut-away: hide levels above, show the selected level's roof off), `Exploded` (levels spread vertically by 0.6× height in tabletop), `Footprint`, `MainRoomCentre(level)` | `Runtime/Model/BuildingModel.cs` |
| Materials: `Stair`, `Railing`, `Slab`, `Floor_Outdoor`, `Column` | `MaterialPalette`, `Editor/Assets/MaterialFactory.cs` |

A single floor is a one-level building, so there is one code path. The floor-only toggles (roof,
labels) carry over per level.

### 4.2 UI (native iOS feel, using `UiKit` / `Theme`)
- **New plan.** The Library's start card opens an **action sheet** (the iOS way to pick a type, not a
  dropdown): *Single floor plan*, *Whole building (one sheet)*, *Whole building (photo per floor)*.
  The last option uses NativeGallery's multi-select.
- **Processing card** polls `/jobs/{id}` and shows the real stages, plus a per-floor checklist for
  buildings.
- **Plan detail.** Buildings get a **segmented control** of levels above the 2D plan
  (`G · 1 · Terrace`). The stat tiles show total and per-level area, and the room list is grouped
  by level. `PlanOutlineGraphic` draws walls (not just room outlines), stairs and columns.
- **AR HUD.** Buildings add a level picker pill (vertical glass stack of floor chips). Picking a level
  hides the levels above it. A toolbar item toggles **Explode** in tabletop mode. Walkthrough asks
  which level to stand on and drops the model to that level's floor. Stairs are visual only, with no
  floor change from walking up them.
- **Library rows** show a small "3 floors" badge for buildings.

### 4.3 AR
`ViewModeController` fits the tabletop scale to the whole building's bounding box, height included,
and in walkthrough it offsets by the chosen level's elevation. `PlacementController` doesn't change.

---

## 5. Evaluation (do this first, it drives the decisions)

There's no way to know whether a prompt change helps without a baseline. Add `backend/eval/`:

- **Ground truth:** hand-label 6–8 plans as v2 `FloorSpec`s in metres. Include the two real images
  above, the synthetic sample, an L-shaped plan, a plan with an angled bay, a plan with a curved
  stair, and 2 hand-drawn photos. One labelled building (the sheet above).
- **Metrics** (`uv run eval`):
  - wall F1: length-weighted, a match is within 0.15 m and 5°;
  - room IoU: mean over matched rooms;
  - room type accuracy;
  - opening recall/precision: type matches and position within 0.3 m;
  - stair detection and riser count error;
  - for buildings, level alignment error in metres.
- **Comparisons to run:**
  - v1 vs v2 on the same set;
  - pixel coordinates vs metres coordinates (validates §2.1 — if pixels lose, keep the v2 structure
    but switch the units);
  - reasoning effort low vs high;
  - whole sheet vs cropped floors.
- The output is a markdown table per run, saved under `eval/runs/`. This also makes good material for
  the project report.

---

## 6. Milestones

| # | Milestone | Done when |
|---|---|---|
| V0 ✅ | Eval harness + labelled set | `uv run eval` scores v1 on 6+ plans, table saved |
| V1 ✅ | Contract v2 + migration | `FloorSpec` / `BuildingSpec` / `BuildingGeometry` models; v1 records and the sample load as one-level buildings; all v1 tests still pass |
| V2 | Wall graph + regions | `orient`, `wallgraph`, `regions`, `scale` with unit tests (L-shape, 45° bay, stub wall, open-plan two-label face, porch, parallel walls 0.12 m apart, ft-in parsing) |
| V3 | v2 floor extraction | New prompts with pixel coordinates; eval beats v1 on wall F1 and room IoU on the real ground-floor plan |
| V4 | Stairs (single floor) | Straight, L, U and curved flights → steps, landings, railings; debug renders correct |
| V5 | Unity levels + stairs | `BuildingBuilder`, slab holes, stairs, columns, parapets; `PlanDebug` shows the real ground-floor plan correctly |
| V6 | Building pipeline | Sheet pass, crop/rotate, parallel floors, heights, alignment, jobs API; the example sheet produces 3 aligned levels |
| V7 | App UI | Plan-type action sheet, job progress, level control in detail, level picker + explode in AR, per-level edits |
| V8 | Device check + polish | iPad run of both example plans; hip roof; eval numbers in progress.md |

V0–V5 fix the single-floor problem without touching the building flow, so they're worth shipping on
their own. V6–V7 add buildings on top.

---

## 7. Testing

- **Backend (pytest, no LLM):**
  - `scale`: unit parsing, outlier rejection;
  - `orient`: angle peaks, parallel walls kept apart;
  - `wallgraph`: T-junction snap, dangling extension, intersection split;
  - `regions`: label assignment, shafts dropped, outdoor areas;
  - `stairs`: riser distribution, arc steps, void pairing;
  - `align`: known offset and rotation recovered;
  - `sheet`: bbox crop + rotation on a synthetic sheet;
  - jobs API with the fake model;
  - v1 record migration.
- **Unity EditMode:**
  - triangulation with holes;
  - stair mesh step count and heights;
  - wall base/height slicing;
  - `BuildingGeometry` JSON round trip;
  - `BuildingModel.VisibleUpTo`.
- **Manual:** `try-plan` writes a per-level debug PNG with walls, stairs and labels drawn over the
  crop. `PlanDebug` screenshots of both reference plans.

---

## 8. Decisions (2026-11-19)

- Whole-building input supports **both** one sheet and one photo per floor.
- The OpenCV wall refinement is **deferred** until the V3 eval shows wall position is the main error.
- Order confirmed: **V0–V5 (single floor) first**, then V6–V7 (buildings).

## 9. Risks

- **Pixel accuracy of the model (`gpt-6.2-sol` since the V0 eval) is unknown.** V0/V3 measure it before anything else depends on it.
  The pipeline after §3.2 works in metres either way.
- **Optional CV refinement (stretch, after V3).** Most real plans draw walls as thick dark strokes.
  An OpenCV step could build a wall mask (threshold, then a morphological opening sized to the wall
  thickness) and nudge each LLM wall to the parallel offset with the most mask coverage within
  ±0.2 m. This targets the 0.25–0.4 m errors seen in v1. Only worth doing if the eval shows wall
  positions are still the main source of error.
- **Long building parses** need the jobs API (§3.7). The app polls every 2 s and the backend keeps
  jobs in memory, which is fine for a single-laptop demo.
- **Cost:** a building costs about 5 vision calls instead of 1.
- **Terrace and hip roofs** are drawn simply (parapets, plus hip roofs from an outline and ridge
  height). Detailed roofs, sunshades and chajjas are out of scope.
