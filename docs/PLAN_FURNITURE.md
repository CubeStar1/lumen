# AR Floor Plan Visualizer — Plan V9: furnished models

Builds on [PLAN_V2.md](PLAN_V2.md) (V0–V8) and [progress.md](progress.md).
Goal: turn the empty shell into a furnished home you can walk through in AR.

1. **Furniture drawn on the plan.** Most residential plans draw beds, sofas, tables, toilets, tubs
   and kitchen counters. Read them, keep their position and orientation, and render a low-poly
   model for each.
2. **Auto-furnish.** Rooms with nothing drawn get a layout suggested by the LLM. A deterministic
   solver then places the pieces against walls and keeps them clear of doors, windows and stairs.
3. **Style themes** (stretch). Material presets for furniture, floors and walls.

Reference inputs: the 9 templates in `backend/samples/aiai/`. They all have furniture symbols,
come in a mix of single- and two-storey plans, and some have no dimensions. `3bed_garage`,
`two_story` and `laundry_room` become the labelled furniture cases. Plans with nothing drawn, such
as `samples/real/ground_floor.png`, test auto-furnish.

---

## 1. Design choices

| Question | Choice | Why |
|---|---|---|
| Same LLM call as walls, or a separate one? | **A separate fixture pass** on the same crop, run in parallel with the floor pass | Keeps the wall prompt focused, so it can't regress the V3 wall/room numbers. Can be re-run on its own and adds no latency |
| How does the model give orientation? | It points at the **back edge** (the side against the wall: headboard, sofa back, toilet cistern, counter back) and the **front-centre point** | Models point at things more reliably than they estimate angles. Rotation and depth then come from code |
| Which room is a fixture in? | Found in code, by point-in-polygon against the room regions | The fixture pass doesn't need room ids, so it can run before the regions exist |
| Dining chairs | `seats` count on the table; Unity places the chairs | Far fewer tokens. The chairs always fit the table |
| Furniture models | **Procedural low-poly recipes in C#** (boxes, rounded boxes, cylinders), merged per material per level | Matches the rest of the model, which is generated, not imported. No asset licences. A few draw calls per level, which matters on the iPhone 12 |
| Sizes | A per-type catalogue gives default, minimum and maximum sizes plus height | A bad scale or misread symbol can't produce a 4 m bed. Heights are never drawn on plans anyway |
| Auto-furnish layout | **The LLM picks the items and their anchor; code places them** | The LLM is good at deciding a bedroom gets a double bed on the wall opposite the door. Code is better at exact clearances |

---

## 2. Data contract

### 2.1 Fixture types (`FixtureType`)
```
bed_single  bed_double  wardrobe  nightstand  dresser
sofa  armchair  coffee_table  tv_unit  bookshelf  rug
dining_table  chair  desk  office_chair
kitchen_counter  kitchen_island  fridge  stove  sink
toilet  washbasin  bathtub  shower
washing_machine  car  plant  other
```
`kitchen_counter` is one straight run. An L-shaped counter is two fixtures. `stove` and `sink` set
into a counter are kept as separate fixtures and drawn on top of it.

### 2.2 Fixture pass (LLM output, pixels)
```jsonc
{
  "fixtures": [
    { "id": "f1", "type": "bed_double",
      "back":  { "start": {"x": 140, "y": 170}, "end": {"x": 140, "y": 275} },  // edge against the wall
      "front": {"x": 270, "y": 222},                                           // centre of the opposite edge
      "seats": null },
    { "id": "f2", "type": "dining_table",
      "back":  { "start": {"x": 560, "y": 190}, "end": {"x": 682, "y": 190} },
      "front": {"x": 621, "y": 268}, "seats": 6 }
  ],
  "notes": "..."
}
```
For free-standing pieces (tables, islands, rugs), `back` is just the edge the model treats as the
back. Its choice only sets which way the piece faces.

### 2.3 `FloorSpec` (metres, editable)
```python
class FixtureSpec(BaseModel):
    id: str
    type: FixtureType
    position: Point          # footprint centre
    width: float             # along the back edge
    depth: float             # back edge to front
    rotation: float          # degrees, direction the front faces, plan frame
    seats: int | None
    source: FixtureSource    # drawn | suggested
```
`FloorSpec.fixtures: list[FixtureSpec]`, default `[]`, so older records and `BuildingAnswers` still load.

### 2.4 `LevelGeometry` (what Unity renders)
```python
class Fixture(BaseModel):
    id: str
    type: FixtureType
    room: str | None
    position: Point          # world frame, as everything else in LevelGeometry
    width: float
    depth: float
    height: float            # from the catalogue
    rotation: float          # degrees about +Y
    seats: int | None
    source: FixtureSource
```

---

## 3. Backend

### 3.1 Modules
| Module | Responsibility |
|---|---|
| `furniture/catalog.py` | Per type: default `(w, d, h)`, min/max `w` and `d`, `against_wall` flag, front clearance (bed 0.6, counter 0.9, toilet 0.5 m), allowed room types |
| `furniture/extract.py` | `PixelFixture` / `FixtureExtraction` schemas, conversion to `FixtureSpec` with the floor's shared scale |
| `furniture/fit.py` | Deterministic clean-up of drawn fixtures (§3.2) |
| `furniture/furnish.py` | Room context for the LLM, placement solver (§4) |
| `llm/prompts.py` | `FIXTURE_INSTRUCTIONS`, `FURNISH_INSTRUCTIONS`; `EDIT_INSTRUCTIONS` gains fixtures |

`building.py` runs the fixture pass next to `_read_floors`. Its answer goes in `FloorAnswer` so
`--rebuild` replays it with no LLM call.

### 3.2 Fitting drawn fixtures
In order, per level, after walls and regions:
1. **Convert.** `width = |back|`, `depth` = distance from `front` to the back line,
   `rotation` = direction from the back line to `front`.
2. **Snap rotation** to the nearest dominant wall angle from `orient` (within 12°). Diagonal
   armchairs stay as drawn.
3. **Clamp size** to the catalogue range. Warn when a clamp exceeds 30 %: that usually means a
   misread symbol or a bad scale.
4. **Back to wall.** For `against_wall` types, if the back edge is parallel to a wall face and
   within 0.25 m of it, move the piece flush with the face (wall centre ± thickness / 2).
5. **Assign a room** by the centre point. Drop pieces outside every room or on a stair footprint,
   with a warning.
6. **Deduplicate.** Same type with more than 50 % footprint overlap: keep the larger.

Drawn fixtures are never moved to clear doors. What's drawn is what the architect intended.

### 3.3 Edits
`EDIT_INSTRUCTIONS` describes fixtures in metres, with their meaning and the `source` field, so
"add a sofa facing the TV", "remove the bathtub" or "turn the bed to face the window" work through
the existing `/plans/edit` flow. Edited fixtures go through steps 2–6 again.

---

## 4. Auto-furnish

### 4.1 Which rooms
Indoor rooms with no fixtures, excluding hallway, staircase and outdoor types. The user decides
when to run it (§6), and it never touches drawn fixtures.

### 4.2 What the LLM sees (text only, cheap)
Per room, in a room-local frame aligned to its dominant wall angle:
- id, name, type, area, polygon in metres;
- its edges as numbered wall segments, each with its doors (offset and width), windows (offset,
  width, sill height) and whether the far side is another room or the exterior;
- stair footprints and columns inside it.

### 4.3 What it returns
```jsonc
{ "rooms": [
  { "room": "r3", "items": [
      { "type": "bed_double", "wall": 2, "along": 0.5 },          // back against segment 2, centred
      { "type": "nightstand", "beside": 0, "side": "left" },      // next to item 0
      { "type": "wardrobe",   "wall": 4, "along": 0.15 },
      { "type": "rug",        "centre": {"x": 1.8, "y": 2.1} } ] } ],
  "notes": "..." }
```
An item is anchored to a wall, placed beside another item, or (for rugs, coffee tables and dining
sets) free with a centre point. Sizes come from the catalogue, not the LLM.

### 4.4 Placement solver (`furnish.py`)
1. Build **keep-out zones** for the room:
   - each door: a `width × width` square on both sides of the wall. We don't know the swing side,
     so this is the conservative choice;
   - each window, for items taller than its sill (wardrobes, fridges, bookshelves);
   - stair footprints plus 0.6 m in front of the bottom step; columns.
2. Place items in the order given. Wall items sit flush with the segment's inner face at `along`.
   `beside` items sit flush next to their anchor. Free items sit at their centre.
3. **On a collision** with a keep-out zone, the room edge, an earlier item or its front
   clearance, slide along the wall in 0.1 m steps, alternating left and right, up to the segment
   length. Then try the catalogue's minimum size. Otherwise drop the item with a warning.
4. Mark everything `source: suggested`.

The solver is pure geometry and fully unit-tested. If the LLM call fails, the room stays empty and
a warning is shown. No silent fallback layouts.

### 4.5 API
`POST /plans/{id}/furnish {level: int | null, replace_suggested: bool}`. Runs one text call for all
target rooms on a level, or one per level in parallel, and returns a `PlanResponse`. It finishes in
seconds, so it needs no job.

---

## 5. Unity

| Piece | Responsibility |
|---|---|
| `Data/PlanGeometry.cs` | `FixtureGeometry`, `FixtureType` / `FixtureSource` enums, JSON fields |
| `Geometry/FurnitureRecipes.cs` | One function per type: `(w, d, h) → parts`, each part a primitive with a local transform and a material slot. Fixed details (legs 0.04 m, mattress 0.2 m, cushion inset) don't stretch with the footprint |
| `Geometry/FurnitureMeshBuilder.cs` | Places each fixture's parts (position, rotation about +Y), merges them into one `MeshData` per material slot per level. Dining chairs are generated around the table from `seats` |
| `Geometry/Primitives.cs` | Box, rounded box (bevelled for cushions and mattresses), cylinder, with UVs. Reuses `MeshData` |
| `MaterialPalette` + `MaterialFactory` | Slots: `Fabric`, `Linen`, `Wood`, `WoodDark`, `Ceramic`, `Metal`, `Appliance`, `Rug`, `Glass` (shared with windows), `CarPaint`, `Foliage` |
| `FloorPlanBuilder.AddLevel` | Adds `Furniture_<slot>` parts under the level root, so the level picker, explode and visible-up-to work unchanged |
| `FloorPlanModel.FurnitureVisible` | Toggle, like `RoofVisible` |
| `PlanOutlineGraphic` | Draws fixtures as light outlines in the 2D preview. Suggested ones are dashed |

Look: soft matte materials, one colour family per slot, slightly rounded edges. It's a dollhouse,
not a catalogue render, and it should match the existing walls and floors. The polygon budget is
about 300 triangles per piece and about 15k per furnished level.

---

## 6. App UI

- **Detail screen:** a Furniture switch next to Roof/Labels. A **Furnish empty rooms** row runs
  `/furnish` for the selected level, shows progress inline, then *Undo* (it restores the previous
  spec).
- **AR HUD:** a Furniture toggle in the existing control group.
- **Edit sheet:** example prompts gain "Add a sofa in the living room" and "Remove suggested furniture".
- Native iOS feel: `UiKit` switches and rows, no new visual language.

---

## 7. Evaluation

- **Labels.** Add `fixtures: [{type, polygon (4 corners), front}]` to `Reference` for the three
  labelled aiai cases, traced in pixels like the walls.
- **Metric.** Greedy matching by type with centre distance < 0.4 m after the existing
  `align`. Report fixture precision, recall and F1, mean centre error, and orientation accuracy
  (front within 20°).
- **Target before V9.2 counts as done:** F1 ≥ 0.75 and orientation ≥ 0.85 on the three cases.
- Live eval runs only happen when asked. Day to day, `--rescore` / `--rebuild` replay stored answers.
- Auto-furnish isn't scored. The solver tests cover its rules, and the device check is visual.

---

## 8. Milestones

| # | Milestone | Done when |
|---|---|---|
| V9.0 | Labels | 3 aiai cases labelled with walls, rooms and fixtures; `Reference.fixtures` loads |
| V9.1 | Contract + fitting | `FixtureType`, `FixtureSpec`, `Fixture`, catalogue, `fit.py` with tests (rotation snap, clamp, flush to wall, room assignment, dedupe); old records load with no fixtures |
| V9.2 | Fixture pass | Prompt + schema, parallel call in `building.py`, stored in `FloorAnswer`, fixture metric in the eval report; target in §7 met |
| V9.3 | Unity furniture | Recipes for every type, merged meshes, palette slots, `FurnitureVisible`; `PlanDebug` shows `3bed_garage` and `two_story` furnished; EditMode tests for recipe bounds and the JSON round trip |
| V9.4 | Auto-furnish backend | Room context, `FURNISH_INSTRUCTIONS`, solver with tests (door square, window-height rule, slide, drop), `/furnish` endpoint with the fake model |
| V9.5 | App UI | Furniture toggles, Furnish row with Undo, fixture edits through the edit sheet, 2D outlines |
| V9.6 | Device check | iPad run: one drawn-furniture plan, one auto-furnished plan; frame time and triangle counts in progress.md |
| V9.7 | Style themes (stretch) | 3 presets swap the furniture, floor and wall materials from the detail screen |

V9.1–V9.3 deliver item 1 on their own. V9.4–V9.5 add item 2 on top.

---

## 9. Testing

- **Backend (pytest, no LLM):**
  - `fit`: back-edge → rotation and depth; 45° armchair kept; 3 m bed clamped with a warning;
    bed 0.15 m off a wall pulled flush; fixture outside rooms dropped; duplicate merge;
  - `furnish`: room-local frame round trip; wall anchor flush at `along`; `beside` placement;
    door square blocks a wardrobe, which slides; a tall item avoids a window and a low one doesn't;
    a room too small for a double bed tries the minimum size, then drops with a warning;
  - `/furnish` with the fake model; `--rebuild` reproduces fixtures from stored answers.
- **Unity EditMode:** every recipe's mesh fits inside its `(w, d, h)` box; chair count matches
  `seats`; fixtures merge into one mesh per slot; `BuildingGeometry` JSON round trip with fixtures.
- **Manual:** `try-plan` debug PNG draws fixture footprints with a front tick over the crop.

---

## 10. Risks

- **Symbol variety.** These templates use clean CAD symbols. Hand-drawn or Indian-style plans draw
  furniture differently, or not at all. Auto-furnish covers the second case. The eval shows how bad
  the first is.
- **Door swing side is unknown**, so the keep-out square is generous and may push items out of small
  rooms. If that happens often, add `swing` to `PixelOpening` (hinge side and direction). The
  plans draw swings clearly.
- **Scale errors carry into furniture**, and plans with no dimensions (e.g. `3bed_garage`) rely on
  door widths. The catalogue clamp hides mild errors. Large clamps are a useful scale warning in
  their own right.
- **Cost:** one extra vision call per floor for the fixture pass, plus one text call per level for
  auto-furnish.

## 11. Open decisions

- Run auto-furnish automatically after every parse, or only when the user asks? The plan assumes
  **only when asked**, so parses stay as fast and cheap as today.
- Should the fixture pass be optional per parse (a toggle on the plan-type sheet)? The plan assumes it always runs.
