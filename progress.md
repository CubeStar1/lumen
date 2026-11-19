# Progress — AR Floor Plan Visualizer

Last updated: 2026-11-19. Read alongside [PLAN.md](PLAN.md), which has the design, data contract and milestones.

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
| M8 Polish | Not started |

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
- After placement, planes detected later stay visible. Minor; hide them via `trackablesChanged` if it bothers.
- Not started (M8): light estimation, door/window frames, furniture, voice input, image-tracked mode.
- When setting up git: ignore `unity-project/floor-plan-viz/Builds/`, `Library/`, `Temp/`, `Logs/`,
  `UserSettings/`. `backend/.env` and `backend/out/` are already in `backend/.gitignore`.

## Decisions made

- **iOS only** (no Android device): iPhone 12 and iPad Air M2. Neither has LiDAR, so only human occlusion is used.
  The Mac is only used for Xcode signing.
- **Pure-LLM parsing** with the OpenAI Responses API and structured output (`responses.parse(text_format=PlanSpec)`),
  model `gpt-5.6-luna`.
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
- *Build Assets*: materials, palette, label/plane prefabs, API settings
- *Rebuild Scenes*: regenerates `Main` and `PlanDebug`. Scenes are generated, so edit `ScreenBuilder`/`SceneBuilder`, not the scenes.
- *Build iOS Xcode Project*: writes `Builds/iOS`

## Gotchas learned (Unity CLI / Editor automation)

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
