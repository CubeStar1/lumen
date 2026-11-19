import io
import time

import pytest
from factories import two_room_drawing
from fastapi.testclient import TestClient
from PIL import Image
from test_service import ScriptedModel

from floorplan.config import Settings, get_settings
from floorplan.main import app, get_service, get_store
from floorplan.service import PlanService, single_floor
from floorplan.store import PlanStore


@pytest.fixture
def client(two_rooms, tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(openai_api_key="test")
    app.dependency_overrides[get_service] = lambda: PlanService(ScriptedModel(two_room_drawing()))
    store = PlanStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def upload(client) -> dict:
    response = client.post("/plans/parse", files={"image": ("plan.png", png_bytes(), "image/png")})
    assert response.status_code == 200
    return response.json()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_parse_saves_and_returns_the_plan(client):
    record = upload(client)

    assert {"spec", "geometry", "warnings"} <= record["plan"].keys()
    assert len(record["plan"]["geometry"]["levels"][0]["walls"]) == 5
    assert record["kind"] == "floor"
    assert record["level_count"] == 1
    assert record["name"] == "2-room plan"
    assert record["room_count"] == 2
    assert record["has_image"]


def test_parse_rejects_non_images(client):
    response = client.post("/plans/parse", files={"image": ("plan.txt", b"hello", "text/plain")})

    assert response.status_code == 422


def test_saved_plans_are_listed_newest_first(client):
    first = upload(client)
    second = upload(client)

    listed = client.get("/plans").json()

    assert [p["id"] for p in listed] == [second["id"], first["id"]]
    assert "plan" not in listed[0]


def test_saved_plan_can_be_fetched_renamed_and_deleted(client):
    plan_id = upload(client)["id"]

    assert client.get(f"/plans/{plan_id}").json()["id"] == plan_id
    assert client.patch(f"/plans/{plan_id}", json={"name": " Flat "}).json()["name"] == "Flat"
    assert client.delete(f"/plans/{plan_id}").status_code == 204
    assert client.get(f"/plans/{plan_id}").status_code == 404


def test_thumbnail_is_served(client):
    plan_id = upload(client)["id"]

    response = client.get(f"/plans/{plan_id}/thumbnail")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_unknown_or_malformed_ids_are_not_found(client):
    assert client.get("/plans/0123456789ab").status_code == 404
    assert client.get("/plans/..%2Fsecret").status_code in (404, 422)


def test_edit_saved_plan_updates_it(client):
    plan_id = upload(client)["id"]

    response = client.post(f"/plans/{plan_id}/edit", json={"instruction": "add a window"})

    assert response.status_code == 200
    assert response.json()["id"] == plan_id


def test_edit_unsaved_plan_round_trips_the_spec(client, two_rooms):
    payload = {
        "spec": single_floor(two_rooms).model_dump(mode="json"),
        "instruction": "add a window",
    }

    response = client.post("/plans/edit", json=payload)

    assert response.status_code == 200
    assert response.json()["spec"]["levels"][0]["floor"]["rooms"][0]["id"] == "r1"


def test_edit_of_a_missing_level_is_not_found(client, two_rooms):
    payload = {
        "spec": single_floor(two_rooms).model_dump(mode="json"),
        "instruction": "add a window",
        "level": 3,
    }

    assert client.post("/plans/edit", json=payload).status_code == 404


def test_jobs_parse_in_the_background_and_save_the_plan(client):
    image = ("plan.png", png_bytes(), "image/png")
    response = client.post("/jobs", data={"kind": "floor"}, files=[("images", image)])

    assert response.status_code == 202
    job = response.json()
    for _ in range(200):
        job = client.get(f"/jobs/{job['id']}").json()
        if job["state"] != "running":
            break
        time.sleep(0.01)
    assert job["state"] == "done", job
    assert job["stages"] == [{"name": "Reading plan", "state": "done"}]
    assert client.get(f"/plans/{job['plan_id']}").json()["kind"] == "floor"


def test_a_floor_job_takes_one_image(client):
    image = ("plan.png", png_bytes(), "image/png")
    response = client.post("/jobs", data={"kind": "floor"}, files=[("images", image)] * 2)

    assert response.status_code == 422


def test_unknown_job_is_not_found(client):
    assert client.get("/jobs/0123456789ab").status_code == 404
