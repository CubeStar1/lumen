# AR Floor Plan Visualizer — Implementation Plan (v1: pure LLM)

Turn a photo of a 2D floor plan into an interactive 3D model placed in the real world with AR.
Plan parsing is done entirely by an OpenAI vision model (`gpt-5.6-luna`); deterministic code
only cleans up and builds geometry.

---

## 1. Current state

| Item | Status |
|---|---|
| Unity Editor | 6000.6.3f1, open and reachable via Unity CLI (Pipeline package installed) |
| Project | `unity-project/floor-plan-viz`, URP 17.6, Input System 1.20, uGUI |
| AR Foundation / ARKit | **Not installed** — added in M2 |
| iOS Build Support module | **Not installed** (only Web) — required before the first device build |
| Target devices | iPhone 12 (A14) and iPad Air M2 — both ARKit-capable, **no LiDAR** |
| Mac + Xcode | Available (borrowed) — needed only to compile/sign the exported Xcode project |
| Python tooling | uv 0.11 |
| Git | Not initialised — recommend `git init` at repo root with a Unity `.gitignore` |

Template leftovers (`Assets/TutorialInfo`, `Readme.asset`, `SampleScene`) will be deleted.

---

## 2. Repository layout

```
ar-el/
├─ PLAN.md
├─ backend/                       # FastAPI + OpenAI, managed by uv
└─ unity-project/floor-plan-viz/  # Unity app
```

---

## 3. System architecture

```
Unity app (iPhone / iPad)                   Backend (laptop, same Wi-Fi)
──────────────────                          ───────────────────────────
pick / capture image ── POST /plans/parse ─► resize image
                                             OpenAI vision → PlanSpec (structured output)
                                             cleanup + wall derivation → PlanGeometry
preview 2D  ◄──────── PlanResponse ────────┘
place in AR
"add a window…" ───── POST /plans/edit ────► OpenAI (spec + instruction) → PlanSpec → PlanGeometry
rebuild     ◄──────── PlanResponse ────────┘
```

The API key lives only on the backend. The phone reaches the laptop via its LAN IP
(configurable in the app).

---

## 4. Data contract

Two layers keep the LLM's job small and the geometry exact:

- **`PlanSpec`** — what the LLM produces and edits: rooms + openings, in metres.
- **`PlanGeometry`** — what Unity renders: derived walls with openings attached. Never produced by the LLM.

### Coordinate system
Metres. +x = right on the page, +y = up on the page. The backend re-centres the plan so the
footprint's centre is at (0, 0). Unity maps plan `(x, y)` → world `(x, 0, y)`.
(The LLM uses a top-left origin with +y down, since that is how images are read; the backend converts.)

### `PlanSpec` (LLM output, strict JSON schema)
Points are `{x, y}` objects everywhere (strict structured outputs handle objects better than tuples).
```json
{
  "wall_height": 3.0,
  "rooms": [
    { "id": "r1", "name": "Kitchen", "type": "kitchen",
      "polygon": [{"x": 0, "y": 0}, {"x": 4.2, "y": 0}, {"x": 4.2, "y": 3.1}, {"x": 0, "y": 3.1}] }
  ],
  "openings": [
    { "id": "o1", "type": "door",   "rooms": ["r1", "r2"],       "position": {"x": 4.2, "y": 1.5}, "width": 0.9 },
    { "id": "o2", "type": "window", "rooms": ["r1", "exterior"], "position": {"x": 2.0, "y": 0.0}, "width": 1.2 }
  ],
  "notes": "Scale taken from the 4.2 m kitchen dimension."
}
```
`type` ∈ `living | bedroom | kitchen | bathroom | dining | hallway | balcony | utility | other`.

### `PlanGeometry` (backend output, consumed by Unity)
```json
{
  "bounds": { "min": [-6, -4.5], "max": [6, 4.5] },
  "rooms": [
    { "id": "r1", "name": "Kitchen", "type": "kitchen",
      "polygon": [...], "centroid": {"x": 0, "y": 0}, "area": 13.0 }
  ],
  "walls": [
    { "id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 4, "y": 0}, "thickness": 0.2, "height": 3.0,
      "exterior": true,
      "openings": [ { "id": "o2", "type": "window", "offset": 2.0, "width": 1.2,
                      "sill": 0.9, "head": 2.1 } ] }
  ]
}
```
`offset` is the distance from `start` to the opening's centre along the wall.

### `PlanResponse`
```json
{ "spec": { ... }, "geometry": { ... }, "warnings": ["Opening o7 had no wall within 0.4 m; dropped."] }
```
The app keeps `spec` so it can send it back for edits.

---

## 5. Backend

### 5.1 Stack
Python 3.12, uv, FastAPI + uvicorn, `openai` SDK, Pydantic v2 + pydantic-settings, Pillow,
Shapely (polygon validity/area/centroid). Dev: pytest, ruff, matplotlib (debug renders).

### 5.2 Layout
```
backend/
├─ pyproject.toml
├─ .env.example                 # OPENAI_API_KEY, OPENAI_MODEL=gpt-5.6-luna
├─ src/floorplan/
│  ├─ main.py                   # FastAPI app + routes
│  ├─ config.py                 # Settings (pydantic-settings, .env)
│  ├─ models.py                 # PlanSpec, PlanGeometry, PlanResponse (Pydantic)
│  ├─ errors.py                 # errors mapped to HTTP responses
│  ├─ service.py                # PlanService: model call → normalize → validate (+1 repair retry) → build
│  ├─ imaging.py                # load, EXIF-rotate, downscale to ≤ 2048 px, data URL
│  ├─ llm/
│  │  ├─ client.py              # OpenAIPlanModel: extract(image) / edit(spec, instruction)
│  │  └─ prompts.py             # instructions as constants
│  ├─ geometry/
│  │  ├─ normalize.py           # cluster x/y coordinates onto a 5 cm grid (aligns shared walls)
│  │  ├─ validate.py            # structural checks → errors / warnings
│  │  ├─ frame.py               # image convention → world frame (+y up, centred, CCW rooms)
│  │  ├─ walls.py               # room edges → wall segments (interior/exterior)
│  │  ├─ openings.py            # attach openings to walls
│  │  └─ build.py               # spec → PlanGeometry
│  ├─ render.py                 # debug PNG of a PlanGeometry
│  └─ cli.py                    # `uv run try-plan <image | spec.json>` → JSON + PNG
├─ samples/                     # two_bedroom.png (synthetic drawing) + two_bedroom.spec.json
└─ tests/                       # pytest: geometry, service retry, API (fake model)
```

### 5.3 Endpoints
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | `{status, model}` |
| POST | `/plans/parse` | multipart `image` | `PlanResponse` |
| POST | `/plans/edit` | `{spec, instruction}` | `PlanResponse` |

Errors: `422` invalid input, `502` LLM failure or unusable output after retry, with a short message
the app can display.

### 5.4 LLM usage
- OpenAI Responses API with structured output bound to the `PlanSpec` Pydantic model, so the
  response always matches the schema.
- Image is sent as a base64 data URL after downscaling.
- **Extraction prompt** covers: coordinate convention; use printed dimensions for scale, otherwise
  assume a 0.9 m door; keep edges axis-aligned unless clearly angled; adjacent rooms must share
  edges exactly; every door/window must lie on a room edge; include corridors as rooms so the
  plan has no gaps.
- **Edit prompt** gets the current spec + instruction and returns a full updated spec; it must keep
  ids stable for untouched elements.
- **One repair retry**: if validation produces hard errors (e.g. self-intersecting polygon, no rooms),
  re-ask with the error list appended. Still failing → `502`.

### 5.5 Geometry pipeline (`pipeline.py`)
1. **Normalize** — flip y; snap vertices to a 5 cm grid; make edges within 5° of an axis exactly
   axis-aligned; merge vertices closer than 10 cm; drop zero-length edges; re-centre on footprint.
2. **Validate** — each polygon valid with area ≥ 1 m²; overlaps between rooms > 5% of the smaller
   room → warning; opening widths within 0.5–3 m.
3. **Derive walls** — group all room edges by supporting line (direction + offset, with tolerance).
   On each line, sweep the 1D intervals: a stretch covered by two rooms → interior wall (0.12 m),
   by one room → exterior wall (0.2 m). Merge contiguous same-kind stretches into segments.
4. **Attach openings** — project each opening onto the nearest wall within 0.4 m, preferring
   exterior walls for `"exterior"` openings; compute `offset`; clamp so it fits; drop with a
   warning otherwise. Defaults: door head 2.1 m; window sill 0.9 m, head 2.1 m.
5. **Package** — room centroid/area, bounds.

All of this is pure functions over Pydantic models and fully unit-tested without the LLM.

### 5.6 Running
```
cd backend
uv sync
uv run uvicorn floorplan.main:app --host 0.0.0.0 --port 8000
uv run try-plan samples/two_bedroom.png         # writes out/two_bedroom.json + .png
uv run pytest
```

---

## 6. Unity app

### 6.1 Packages to add
| Package | Why |
|---|---|
| `com.unity.xr.arfoundation` | AR abstraction (planes, raycasts, anchors) |
| `com.unity.xr.arkit` | iOS provider |
| `com.unity.xr.management` | XR plug-in management (pulled in by AR Foundation) |
| `com.unity.nuget.newtonsoft-json` | JSON with nested arrays (`JsonUtility` can't do `float[][]`) |
| `com.unity.textmeshpro` / uGUI TMP | Room labels and UI text (bundled in uGUI 2.x) |
| NativeGallery (yasirkula, git URL) | Pick a plan image from the photo library — **see open question 1** |

Existing packages are left as they are.

Versions are resolved against 6000.6 at install time with the package-management tooling.

### 6.2 Folder & assembly layout
```
Assets/FloorPlanViz/
├─ Scripts/
│  ├─ Core/        FloorPlanViz.Core.asmdef      — data + geometry, no MonoBehaviours
│  │  ├─ Data/       PlanResponse, PlanSpec, PlanGeometry, WallData, RoomData, OpeningData
│  │  └─ Geometry/   MeshData, BoxBuilder, WallSlicer, PolygonTriangulator
│  ├─ Runtime/     FloorPlanViz.Runtime.asmdef   — builds and controls the model
│  │  ├─ Api/        PlanApiClient, ApiSettings (ScriptableObject)
│  │  └─ Model/      FloorPlanBuilder, FloorPlanModel, MaterialPalette (ScriptableObject), RoomLabel
│  ├─ AR/          FloorPlanViz.AR.asmdef        — AR Foundation dependent
│  │                 ScreenInput, PlacementController, ModelGestures, ViewModeController
│  ├─ UI/          FloorPlanViz.UI.asmdef        — screens and flow
│  │                 AppFlow, AppScreen, HomeScreen, ProcessingScreen, PreviewScreen, ArHud,
│  │                 EditPanel, PlanOutlineGraphic, SafeAreaPanel, ImagePicker
│  └─ Editor/      FloorPlanViz.Editor.asmdef    — project setup automation
│                    AssetBuilder, SceneBuilder, ScreenBuilder, UiKit, PlatformSetup,
│                    IosPostProcess, IosBuild
├─ Tests/EditMode/ FloorPlanViz.Tests.asmdef     — WallSlicer, Triangulator, JSON round-trip
├─ Materials/  Prefabs/  Scenes/  Settings/
└─ Samples/        sample plan JSONs (TextAssets) for the debug scene
```
Assemblies enforce the dependency direction: `Core ← Runtime ← AR / UI`. Core has no Unity
scene dependencies, so geometry is testable in EditMode.

### 6.3 Key components
| Class | Responsibility |
|---|---|
| `PlanApiClient` | `ParseAsync(byte[] image)`, `EditAsync(PlanSpec, string)` via `UnityWebRequest` + `Awaitable`; returns `PlanResponse` or throws `PlanApiException` with a displayable message |
| `ApiSettings` | ScriptableObject: base URL, timeout. Editable at runtime from a settings field on the home screen |
| `WallSlicer` | Pure: wall + openings → list of boxes (solid, lintel above door, sill + lintel for window) |
| `BoxBuilder` / `MeshData` | Pure: accumulate oriented boxes and polygons into vertex/index/UV lists |
| `PolygonTriangulator` | Pure: ear-clipping for room floors (handles concave rooms) |
| `FloorPlanBuilder` | `Build(PlanGeometry) → FloorPlanModel`: one mesh per material group (exterior walls, interior walls, floor per room type), ceiling mesh, labels |
| `FloorPlanModel` | Root component of a built plan: `ShowCeiling`, `ShowLabels`, `Bounds`, `Dispose` |
| `MaterialPalette` | Maps wall kinds / room types to URP materials |
| `RoomLabel` | World-space TMP label at room centroid, billboards toward camera |
| `PlacementController` | Plane raycast on tap → place / move the model, attach `ARAnchor` |
| `ModelGestures` | Pinch scale, two-finger twist rotate (EnhancedTouch, Input System) |
| `ViewModeController` | **Tabletop**: fits the model to ~0.6 m on its longest side. **Walkthrough**: 1:1, ceiling hidden, model placed so the user stands at the plan centre facing +y |
| `AppFlow` | Explicit state machine: `Home → Processing → Preview → Placing → Viewing` (+ `Editing`), toggles screens |
| `PlanOutlineGraphic` | uGUI `MaskableGraphic` drawing room outlines + openings over the source image for the preview step |

Rules: one MonoBehaviour per file; no singletons/`FindObjectOfType`; references are serialized and
wired by `SceneBuilder`; async code uses `Awaitable` with cancellation on destroy.

### 6.4 Mesh generation details
- Walls are built at 1 unit = 1 m. Each wall is extended by `thickness/2` at both ends so
  corners close without mitre logic.
- Door: gap from floor to `head`, lintel `head → height`. Window: solid `0 → sill`, gap,
  lintel `head → height`. Openings are left as holes in v1 (frames/glass are a stretch goal).
- Floors: triangulated per room, slightly inset to avoid z-fighting with walls; materials by room type.
- Ceiling: single mesh from the union of room polygons; hidden by default in tabletop mode.
- UVs in world metres so tiled materials keep a consistent scale.
- Meshes are combined per material → a handful of draw calls regardless of plan size.

### 6.5 Scenes
| Scene | Purpose |
|---|---|
| `Main.unity` | The app: AR Session, XR Origin (camera with `ARCameraManager`, `ARCameraBackground`), `ARPlaneManager` (horizontal), `ARRaycastManager`, `ARAnchorManager`, directional light, UI canvas, `AppFlow` |
| `PlanDebug.unity` | Desktop only: orbit camera + `FloorPlanBuilder` fed by a sample JSON TextAsset or a live backend call. Used to develop and screenshot geometry without a phone |

AR is tested in the Editor with **XR Simulation** before going to a device.

### 6.6 Building scenes via the Unity CLI
Scene, prefab and material construction lives in `Editor/` as idempotent static methods, run
against the open Editor with `unity command script eval` and also exposed as menu items:

| Menu item | Does |
|---|---|
| Floor Plan Viz → Configure iOS | Player settings, ARKit / XR Simulation loaders, URP AR background feature |
| Floor Plan Viz → Build Assets | Materials, material palette, room label + AR plane prefabs, API settings |
| Floor Plan Viz → Rebuild Scenes | Build Assets, then regenerate `Main` and `PlanDebug` scenes |
| Floor Plan Viz → Build iOS Xcode Project | Configure iOS, then export `Builds/iOS` |

Scenes are regenerated rather than hand-edited, so make layout changes in `ScreenBuilder` / `SceneBuilder`.

### 6.7 iOS configuration
Applied by `PlatformSetup` (Player, XR and URP settings) and `IosPostProcess` (Info.plist edits after build):
- `ARBackgroundRendererFeature` added to the URP renderers — without it the camera feed is not drawn.
- XR Plug-in Management → ARKit enabled for iOS; ARKit requirement *Required*.
- Target device **iPhone + iPad** (universal), minimum iOS 15, ARM64, Metal.
- Bundle id `com.thecubestar.floorplanviz`.
- `NSCameraUsageDescription` (AR camera), `NSPhotoLibraryUsageDescription` (picking plans),
  `NSLocalNetworkUsageDescription` (reaching the laptop backend on the LAN).
- **Allow downloads over HTTP** → ATS exception, since the backend is plain HTTP on the LAN.
- Portrait and landscape enabled; UI uses a `CanvasScaler` (scale with screen size) and a
  safe-area panel so it works on both the iPhone notch and the iPad's larger screen.
- No LiDAR on either device: `AROcclusionManager` is used for **human occlusion** only;
  environment depth and scene meshing are out of scope.

### 6.8 Device build workflow (Windows → Mac → device)
1. On Windows: menu **Floor Plan Viz → Build iOS Xcode Project** → writes an Xcode project to
   `unity-project/floor-plan-viz/Builds/iOS/`.
2. Copy the folder to the Mac (zip / USB drive / git).
3. On the Mac: open `Unity-iPhone.xcodeproj` → *Signing & Capabilities* → Team = your personal
   Apple ID → connect the iPhone/iPad → Run.
4. On the device (first time): enable *Developer Mode* (Settings → Privacy & Security) and trust
   the developer profile (Settings → General → VPN & Device Management).

Free-account limits: the app expires after **7 days** (just re-run from Xcode), max 3 sideloaded
apps per device. Rebuild and re-run before the demo day. The Mac's Xcode must support the
devices' iOS version.

Since device sessions need the Mac, day-to-day AR testing uses **XR Simulation** in the Editor;
device builds happen at milestone checkpoints.

---

## 7. Milestones

| # | Milestone | Done when |
|---|---|---|
| M0 | Repo hygiene | Template leftovers removed (git set up by you) |
| M1 | Backend core | `try_plan.py` turns 5 sample plans into JSON + overlay PNGs; geometry tests pass |
| M2 | Unity packages + Core geometry | Packages installed, project compiles, EditMode tests for slicer/triangulator pass |
| M3 | Debug scene | `PlanDebug` renders sample JSONs and a live backend response correctly |
| M4 | AR placement | In XR Simulation, tap a plane → model placed, scale/rotate, ceiling and label toggles |
| M5 | App flow | Home → pick image → processing → 2D preview → AR, with error states and retry |
| M6 | Device build | App runs on the iPhone and iPad (via Mac/Xcode) against the laptop backend |
| M7 | Edits + walkthrough | Natural-language edits rebuild the model; walkthrough mode at 1:1 |
| M8 | Polish | Materials, lighting estimation, small UX fixes, demo recording |

### Status (2026-11-18)

| # | State | Verified by |
|---|---|---|
| M0 | Done | Template leftovers removed |
| M1 | Done, except a live LLM run (needs `OPENAI_API_KEY`) | 28 pytest tests; `try-plan` on the sample spec |
| M2 | Done | 11 EditMode tests (slicer, triangulator, JSON) |
| M3 | Done | `PlanDebug` screenshot |
| M4 | Done | XR Simulation: planes found, tap-to-place, roof/labels toggles, walkthrough |
| M5 | Done | Home → sample → preview → AR in Play mode; edit request reaches backend and shows its error |
| M6 | Blocked on an Editor restart (iOS module was installed while it was open); then export + Mac run | — |
| M7 | Code done; needs a real API key to exercise edits end to end | — |
| M8 | Not started | — |

Stretch: image-tracked mode (model rises from the printed plan), door/window frames, furniture,
voice input, glTF export, comparing the LLM against an OpenCV baseline for the report.

---

## 8. Testing

- **Backend**: pytest on `normalize`, `walls`, `openings`, `validate` using small hand-written specs
  (L-shaped room, two adjacent rooms, opening off any wall). The LLM is not called in tests.
- **Unity**: EditMode tests for `WallSlicer` (no openings, door, window, adjacent openings, opening
  at edge), `PolygonTriangulator` (convex, concave, collinear points), and JSON deserialization of a
  sample `PlanResponse`.
- **Manual**: `try_plan.py` overlays for prompt iteration; `PlanDebug` screenshots via the CLI.

---

## 9. Decisions

- Target **iOS** (iPhone 12 + iPad Air M2), compiled and signed on a borrowed Mac.
- Image input via **NativeGallery** + bundled sample plans.
- **iOS Build Support** installed on Windows (needed to export the Xcode project).
- Existing Unity packages kept.
- Device and laptop on the **same Wi-Fi**; backend URL set in the app.
- **Git** set up by the user.
- Bundle id **`com.thecubestar.floorplanviz`**.
