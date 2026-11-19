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
| `POST /plans/parse` | multipart `image` | `PlanResponse` |
| `POST /plans/edit` | `{ "spec": PlanSpec, "instruction": "..." }` | `PlanResponse` |

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

1. `llm/` asks the model for a `PlanSpec`: rooms and openings in metres (image convention, +y down).
2. `geometry/normalize` snaps coordinates so shared walls line up exactly.
3. `geometry/validate` reports errors (retried once with feedback) and warnings.
4. `geometry/build` converts to the world frame (+y up, centred), derives walls from room edges
   and attaches doors and windows.
