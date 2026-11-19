# Progress — AR Floor Plan Visualizer

Last updated: 2026-11-19. Read alongside [PLAN.md](PLAN.md), which has the design, data contract and milestones.

## v2: flexible plans and whole buildings (started 2026-11-19)

Plan: [PLAN_V2.md](PLAN_V2.md). Decisions: building input supports one sheet **and** a photo per floor;
the OpenCV wall refinement waits for the eval; single floor (V0–V5) ships before buildings (V6–V7).

**V0 eval harness: done.** `backend/src/floorplan/evaluation/` (reference format, metrics, overlays, report).
`uv run eval [cases] [--repeat N] [--model M] [--effort E] [--name RUN] [--rescore RUN]` writes
`backend/eval/runs/<run>/`. References are traced in pixels with one `metres_per_unit`; each case has a
`reference_overlay.png` for checking. Six floor cases in `backend/eval/cases/`:
- `two_bedroom` (synthetic, exact) and `ground_floor_imperial` (the user's ft-in plan, hand-traced);
- `indian_30x35` and `bungalow_2bhk` (Commons, traced from printed dimensions);
- `curved_stair_first_floor` (approximate: no dimensions, textured render, curved stair, angled bay);
- `angled_sketch` (coarse: low-res hand sketch with two angled wings).
`backend/eval/buildings/somerville_four_floors` is kept for V6. Sources and licences: `backend/eval/ATTRIBUTION.md`.

**Model comparison (2026-11-19, v1 pipeline, 2 runs per case, mean over 6 cases):**

| Model | Wall F1 | Room IoU | Types | Opening R | Opening err m |
|---|---|---|---|---|---|
| gpt-5.6-luna | 0.48 | 0.56 | 0.68 | 0.34 | 0.14 |
| gpt-6-luna | 0.58 | 0.56 | 0.65 | 0.41 | 0.09 |
| **gpt-6.2-sol** | **0.71** | **0.73** | 0.74 | **0.82** | **0.05** |

The default is now **gpt-6.2-sol** (20x Luna's token price, still cents per plan). On the real ground floor it
reaches wall F1 0.93 and opening recall 0.88 (gpt-5.6-luna: 0.36 / 0.05). Every model still fails the angled and
curved cases (wall F1 ≤ 0.23) and finds no stairs: those are v1 pipeline limits (global x/y snapping, no
stair type), which V1–V4 address. Runs: `eval/runs/cmp-*`.

**V1 contract v2: done (2026-11-19).**
- Backend: `FloorSpec` (rooms with an `outdoor` flag, extra walls with a kind, openings incl. `sliding_door` and
  `opening`, stairs with flights/landings, columns) inside a `BuildingSpec` of levels; geometry is
  `BuildingGeometry` → `LevelGeometry[]`, all levels in one world frame. New room types: toilet, staircase, porch,
  terrace, store, garage.
- Outdoor rooms get no walls, so porches and sit-outs stay open; extra walls (stubs, low walls, parapets) are
  built with their own height and thickness. Stairs and columns are extracted and stored but not yet built (V4).
- Edits take a `level` (default 0). Old saved records and v1 spec files are upgraded on read (`legacy.py`). The
  sample spec and the Unity sample JSON are in the new format. Library counts and area exclude outdoor rooms.
- Unity: `BuildingGeometry`/`LevelGeometry` data, one child per level at its elevation, roof on the top level, label
  groups per level; the spec is kept as an opaque object and sent back unchanged for edits; new enum values are
  appended (materials store them as ints) and borrow an older type's material and style.
- Verified: 42 backend tests, 13 Unity EditMode tests, clean compile; a live gpt-6.2-sol parse of the real ground
  floor (13 rooms incl. 2 outdoor, 31 openings, 1 stair, 3 columns) rendered correctly in `PlanDebug`.
- Still v1 behaviour: walls come from room edges, so open-plan boundaries (dining hall / stair hall) still get
  walls. That is V2.

## Where things stand

| Milestone | State |
|---|---|
| M0 Repo hygiene | Done. Template leftovers removed. User is setting up git. |
| M1 Backend | Done. Tested with the real LLM (results below). |
| M2 Unity packages + core geometry | Done |
| M3 Desktop debug scene | Done |
| M4 AR placement (XR Simulation) | Done |
| M5 App flow (home → preview → AR) | Done |
| M6 iOS device build | **Done.** Runs on the iPad Air M2 (2026-11-19). On-device AR flow still to be exercised |
| M7 Natural-language edits + walkthrough | Code done; edits not yet tried with a real key inside the app |
| M8 Polish | **Done** (2026-11-19): iOS-style UI, plan history, materials and lighting. Needs a device check |

## First thing to do next session

1. ~~Restart the Editor~~ and ~~export~~: done. `unity-project/floor-plan-viz/Builds/iOS` holds the Xcode
   project (1.4 GB, with the camera, photo library and local network entries in Info.plist).
2. Copy `Builds/iOS` to the Mac (zip it, or re-export there) and follow PLAN.md §6.8: open
   `Unity-iPhone.xcodeproj`, sign with a free Apple ID, enable Developer Mode on the device, trust the
   developer profile.
3. Optional: load the LLM output (`backend/out/llm/two_bedroom.json`) into the `PlanDebug` scene to see it in 3D.
4. Try **real floor plan photos/scans**. So far only the clean synthetic sample has been tested.

## Real LLM test (2026-11-19)

Model `gpt-5.6-luna`, input `backend/samples/two_bedroom.png`, a synthetic drawing generated from
`two_bedroom.spec.json`, so the correct answer is known. Command: `uv run try-plan samples/two_bedroom.png --out out/llm`.

- **38 s** per call.
- **Scale:** correct, taken from the "10.0 m" width label and the room dimension text.
- **Rooms: 7/7 with exact coordinates**, correct types. Names are kept in capitals as printed ("LIVING ROOM").
- **Openings: 13/13 found**, each on the correct wall with the correct room pair, and no pipeline warnings.
- **Weak spot:** door/window positions and widths are off by 0.25–0.4 m in places. For example, the entrance
  door is at y 2.75 instead of 2.5, the living room window is 1.6 m wide instead of 1.8, and the bathroom
  window is 0.9 m instead of 0.6.
- Outputs: `backend/out/llm/two_bedroom.json` and `two_bedroom.png` (side-by-side input/reconstruction).

## What has been verified

- **Backend:** 28 pytest tests pass (geometry, service retry, API with a fake model). Ruff is clean.
- **Unity:** 11 EditMode tests pass (wall slicer, triangulator, JSON round trip). All assemblies compile
  with 0 warnings.
- **`PlanDebug` scene** renders the sample: walls, door/window openings, floors coloured by room type, labels.
- **XR Simulation in Play mode:** home → *Try sample plan* → preview (2D outline) → *View in AR* → plane
  found → tap-to-place (0.6 m tabletop) → roof/labels toggles → walkthrough at 1:1, standing in the
  largest room, at floor height.
- **Network path:** with the backend running and a dummy key, an in-app edit request reached `/plans/edit`.
  The snake_case spec passed validation, and OpenAI's 401 came back as a 502 whose message appeared in the AR hint.

## M8 polish (2026-11-19)

- **Plan history.** The backend saves every parsed plan in `backend/data/<id>/` (record JSON, image, thumbnail).
  New endpoints: list, get, rename, delete, edit by id, and thumbnail/image. See `backend/README.md`. The sample
  plan stays local and uses the stateless `/plans/edit`.
- **UI rebuilt in an iOS style.** Inter font (4 weights) and Material Icons Round, generated rounded sprites, iOS system
  colours (`UI/Theme.cs`). `DensityScaler` sizes the UI in iOS points per device, so the iPad no longer looks
  oversized, and `ResponsivePadding` caps content at 680 pt on wide screens. Pages: Library (start card, connection
  badge, recent plans with thumbnails), Plan detail (2D plan, stat tiles, room list, notes, sticky "View in AR"), AR HUD
  (glass close button, title and hint pills, Place button, five-item glass toolbar). Overlays: edit sheet with
  suggestions, server settings sheet, action sheet (Rename / Delete), rename alert, progress card with stages, toast.
  Screens fade or slide in; buttons shrink slightly when pressed; sheets move up above the keyboard.
- **Model look.** Procedural textures (`Editor/Assets/Procedural.cs`): oak/ash planks, three tile sizes, deck,
  plaster, concrete. Walls have dark section-cut caps, windows have glass and frames, doors have frames, and the model
  sits on a white base board. A transparent **shadow catcher** (`Shaders/ShadowCatcher.shader`) shows the model's shadow
  on the real surface. Room labels are rounded white cards in title case, lowered to 2.3 m in walkthrough.
- **Lighting.** A warm sun with soft shadows, trilight ambient, and `LightEstimator`, which follows ARKit's ambient
  intensity and colour temperature. URP: MSAA 4x, render scale 1, 2048 shadow map, 2 cascades over 20 m, soft
  shadows, transparent objects receive shadows (the Mobile renderer had this off).
- **AR flow.** A placement reticle follows the screen centre; "Place model" places at the reticle, or tap a spot. The
  model pops in with an ease-out-back animation. Tap-to-move is disabled in walkthrough. Planes found after placement
  stay hidden. The AR session only runs while the AR view is open, and the screen doesn't sleep during AR.

Verified in the Editor (XR Simulation, backend running): library, detail, rename (saved on the server), action sheet,
settings sheet, placement with the reticle, roof/labels/walk toggles, edit sheet, progress card and error toast.
**Not yet verified on a device**: keyboard avoidance, iPad/iPhone point scaling, light estimation, real edits.

## Known issues / open items

- **Mac build steps** (full guide for Claude Code on the Mac: [MAC_BUILD.md](MAC_BUILD.md)): after copying the Windows export to the Mac, run
  `xattr -dr com.apple.quarantine . && chmod -R +x Il2CppOutputProject/IL2CPP && find . -name "*.sh" -exec chmod +x {} +`
  in `Builds/iOS`, or UnityFramework fails with `PhaseScriptExecution`. Decline Xcode's
  "Update to recommended settings" prompt. The device must be plugged in once before the free
  Personal Team can create a profile.
- **Edits with a real key** haven't been tried in the app (only via the dummy-key error path).
- **Real-world plans untested.** Expect worse results on photos, hand-drawn plans or plans without dimension text.
- In the Editor, the app's server URL was set to `http://127.0.0.1:8000` in PlayerPrefs during testing. On
  the device, type the laptop's LAN IP on the home screen.
- Ideas not done: furniture, voice input, image-tracked mode, AR environment probes for glass reflections.
- When setting up git: ignore `unity-project/floor-plan-viz/Builds/`, `Library/`, `Temp/`, `Logs/`,
  `UserSettings/`. `backend/.env` and `backend/out/` are already in `backend/.gitignore`.

## Decisions made

- **iOS only** (no Android device): iPhone 12 and iPad Air M2. Neither has LiDAR, so only human occlusion is used.
  The Mac is only used for Xcode signing.
- **Pure-LLM parsing** with the OpenAI Responses API and structured output (`responses.parse(text_format=PlanSpec)`),
  model `gpt-5.6-luna` (switched to `gpt-6.2-sol` on 2026-11-19 after the eval).
- The LLM outputs **rooms and openings only**; walls are derived in code. Points are `{x, y}` objects.
- **One repair retry** with validation feedback, then a 502.
- Image input via **NativeGallery 1.9.5** (git package) plus a bundled sample plan.
- Bundle id `com.thecubestar.floorplanviz`. Existing Unity packages are kept.
- Clean, modular code with minimal comments (the user's standing preference).

## How to run

```
# backend (needs backend/.env with OPENAI_API_KEY)
cd backend
uv run uvicorn floorplan.main:app --host 0.0.0.0 --port 8000
uv run try-plan samples/two_bedroom.png          # through the LLM
uv run try-plan samples/two_bedroom.spec.json    # geometry only, no LLM
uv run pytest
```

Unity editor menu **Floor Plan Viz**:
- *Configure iOS*: Player settings, ARKit/Simulation loaders, URP AR background feature
- *Build Assets*: textures, materials, palette, label/plane/reticle prefabs, API settings. Generated textures and
  fonts are kept once created; delete the PNG or `* SDF.asset` to regenerate it.
- *Configure Rendering*: URP quality, transparent shadows, colour temperature, visible status bar
- *Rebuild Scenes*: runs the two items above, then regenerates `Main` and `PlanDebug`. Scenes are generated, so edit
  `Editor/Ui/*Builder.cs` and `SceneBuilder`, not the scenes.
- *Build iOS Xcode Project*: writes `Builds/iOS`

## Gotchas learned (Unity CLI / Editor automation)

- **Play mode stalls when the Editor is unfocused** (`Time.frameCount` stays at 1). Run
  `UnityEngine.Application.runInBackground = true;` via eval after entering Play mode.
- Portrait test captures: `UnityEditor.PlayModeWindow.SetCustomRenderingResolution(780, 1688, "iPhone")`.
- TMP text with Ellipsis overflow renders **nothing** if its box is even slightly shorter than one line. `UiKit.Label`
  gives non-wrapping labels a one-line minimum height for this reason.
- A sliced `Image` reports its sprite borders as its preferred size, which inflates layouts. Backgrounds use `ShapeImage`.
- Avoid `using static UiKit` names that clash with Unity types (`Rect`, `Text`, `Button`, `Input`); hence `Node`, `Label`,
  `TextButton`, `TextField`.

- **Auto-tick:** run `unity command editor set_auto_tick --enabled true --persist true` once (already
  done, persisted). Without it the unfocused Editor stops ticking and every command times out.
- Use `unity command script eval --code '<C#>' --result-only --caller plugin --skill unity-cli --timeout N`.
  Passing the code as a bare positional argument hangs.
- After package adds, recompiles or Play mode changes, the Pipeline server briefly returns
  `PIPELINE_UNREACHABLE` / "Invalid response format". Run `unity status --until-ready` and retry.
- `unity recompile` returning `up_to_date` can mean "already compiled". Check `Library/ScriptAssemblies`
  timestamps, or read errors with `unity command console get --level error`.
- Tests: `unity command test run --mode EditMode --filter FloorPlanViz` (`unity test` refuses while the Editor is open).
- Screenshots: `unity command capture game_view --output-path <png>`. The Game view is landscape, so a portrait
  capture is squished; judge layout from the maths, not the pixels.
- **XR Simulation finds planes only while the simulated camera moves.** In automation, rotate the
  `SimulationCamera` GameObject (e.g. pitch 45°, sweep the yaw), then aim down (`Euler(70, 200, 0)`) and call
  `PlacementController.TryPlace` via reflection with the plane centre's screen point.
- `FindAnyObjectByType` skips inactive objects (the model is inactive until placed). Pass `FindObjectsInactive.Include`.
- Avoid `\"` inside eval code in bash single quotes; it breaks compilation.
- URP needs `ARBackgroundRendererFeature` on the renderer, or the camera feed isn't drawn (now automated).
- The "XR Origin (Mobile AR)" menu item already creates an AR Session. Don't add a second one.
- Custom `MaskableGraphic` subclasses need `[RequireComponent(typeof(CanvasRenderer))]` here.
- Install new Unity modules with the Editor closed, or restart it afterwards.
