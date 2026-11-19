import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_service import ScriptedModel

from floorplan.config import Settings, get_settings
from floorplan.main import app, get_service
from floorplan.service import PlanService


@pytest.fixture
def client(two_rooms):
    app.dependency_overrides[get_settings] = lambda: Settings(openai_api_key="test")
    app.dependency_overrides[get_service] = lambda: PlanService(ScriptedModel(two_rooms, two_rooms))
    yield TestClient(app)
    app.dependency_overrides.clear()


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_parse_returns_geometry(client):
    response = client.post("/plans/parse", files={"image": ("plan.png", png_bytes(), "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert {"spec", "geometry", "warnings"} <= body.keys()
    assert len(body["geometry"]["walls"]) == 5


def test_parse_rejects_non_images(client):
    response = client.post("/plans/parse", files={"image": ("plan.txt", b"hello", "text/plain")})

    assert response.status_code == 422


def test_edit_round_trips_the_spec(client, two_rooms):
    payload = {"spec": two_rooms.model_dump(mode="json"), "instruction": "add a window"}

    response = client.post("/plans/edit", json=payload)

    assert response.status_code == 200
    assert response.json()["spec"]["rooms"][0]["id"] == "r1"
