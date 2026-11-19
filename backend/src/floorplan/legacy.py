"""Reads plans saved before multi-level support, where the spec was a single PlanSpec with
`wall_height`, rooms and openings."""

from typing import Any

from floorplan.models import BuildingSpec, FloorSpec
from floorplan.service import from_spec, single_floor

LEGACY_LEVEL_NAME = "Ground floor"


def is_legacy(spec: dict[str, Any]) -> bool:
    return "wall_height" in spec


def upgrade_spec(data: dict[str, Any]) -> BuildingSpec:
    if not is_legacy(data):
        return BuildingSpec.model_validate(data)
    floor = FloorSpec(
        name=LEGACY_LEVEL_NAME,
        height=data["wall_height"],
        rooms=[{**room, "outdoor": False} for room in data["rooms"]],
        walls=[],
        openings=data["openings"],
        stairs=[],
        columns=[],
        notes=data.get("notes", ""),
    )
    return single_floor(floor)


def upgrade_record(data: dict[str, Any]) -> dict[str, Any]:
    spec = data["plan"]["spec"]
    if not is_legacy(spec):
        return data
    plan = from_spec(upgrade_spec(spec))
    return {**data, "plan": plan.model_dump(mode="json")}
