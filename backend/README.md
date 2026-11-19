# Floor Plan API

Turns a floor plan image into 3D-ready geometry for the AR app.

## Setup

```
uv sync
cp .env.example .env        # then set OPENAI_API_KEY
```

## Run

```
uv run uvicorn floorplan.main:app --host 0.0.0.0 --port 8000
```

The phone connects to `http://<laptop-lan-ip>:8000`.

| Endpoint | Body | Returns |
|---|---|---|
| `GET /health` | — | status and model name |
| `POST /plans/parse` | multipart `image` | `PlanRecord` (the plan, saved) |
| `GET /plans` | — | `PlanSummary[]`, newest first |
| `GET /plans/{id}` | — | `PlanRecord` |
| `PATCH /plans/{id}` | `{ "name": "..." }` | `PlanRecord` |
| `DELETE /plans/{id}` | — | 204 |
| `POST /plans/{id}/edit` | `{ "instruction": "...", "level": 0 }` | `PlanRecord` (saved over the old plan) |
| `GET /plans/{id}/image`, `/thumbnail` | — | JPEG of the uploaded plan |
| `POST /plans/edit` | `{ "spec": BuildingSpec, "instruction": "...", "level": 0 }` | `PlanResponse` (unsaved plans, e.g. the sample) |

Saved plans live in `data/<id>/` (`record.json`, `image.jpg`, `thumbnail.jpg`). Set `DATA_DIR` to store them elsewhere.
Records saved before multi-level support are upgraded when read (`legacy.py`).

A plan is a `BuildingSpec` of one or more levels, each holding a `FloorSpec` (rooms, extra walls,
openings, stairs, columns). Its geometry is a `BuildingGeometry` with one `LevelGeometry` per level.
A single floor plan is a building with one level.

## Try a plan from the command line

```
uv run try-plan samples/two_bedroom.png         # through the language model
uv run try-plan samples/two_bedroom.spec.json   # skip the model, geometry only
```

Writes `out/<name>.json` and a preview `out/<name>.png`.

## Test

```
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Pipeline

1. `llm/` sends the image (and its pixel size) and gets back a `FloorExtraction` in pixels: every
   wall, openings on their walls, a label point per room (outlines only for outdoor and open-plan
   rooms), stairs, columns and the printed dimensions with their end points.
2. `extraction.py` computes the scale from those dimensions (`geometry/scale`; door widths and then
   the model's own guess as fallbacks) and converts everything to a metric `FloorSpec`.
3. `geometry/normalize` fits walls and outlines onto shared lines along the plan's dominant
   directions (`geometry/orient`), so corners meet exactly and angled walls keep their angle.
4. `geometry/layout` joins the walls into a graph (`geometry/wallgraph`), merges walls the model
   stopped at a door, and finds each room as the face of the graph around its label point
   (`geometry/regions`). Open-plan faces are split along the traced room outlines.
5. `geometry/validate` reports errors (retried once with feedback, in the model's own format) and
   warnings.
6. `geometry/build` converts every level to one shared world frame (+y up, centred on the building),
   decides exterior or interior from the rooms on each side of a wall, and attaches openings.

Specs with `derive_walls: true` (older plans and the hand-written sample) instead derive walls from
room outlines, plus their extra stub and low walls.

## Evaluate

```
uv run eval --repeat 2                  # all cases in eval/cases, mean of 2 parses each
uv run eval bungalow_2bhk --model gpt-6-luna
uv run eval --rescore <run>             # rescore saved predictions without calling the model
uv run eval --rebuild <run>             # rerun saved raw model answers through the current geometry
```

`eval/` holds the hand-traced references and run outputs. It is kept locally and not committed.
