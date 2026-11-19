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
        return BuildingSpec.model_validate(_with_new_fields(data))
    floor = FloorSpec(
        name=LEGACY_LEVEL_NAME,
        height=data["wall_height"],
        derive_walls=True,
        rooms=[{**room, "outdoor": False, "label": None} for room in data["rooms"]],
        walls=[],
        openings=[{**opening, "wall": None} for opening in data["openings"]],
        stairs=[],
        columns=[],
        notes=data.get("notes", ""),
    )
    return single_floor(floor)


def upgrade_record(data: dict[str, Any]) -> dict[str, Any]:
    return {**data, "plan": upgrade_plan(data["plan"])}


def upgrade_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """A saved PlanResponse in the current format."""
    spec = plan["spec"]
    if not is_legacy(spec):
        return {**plan, "spec": _with_new_fields(spec)}
    return from_spec(upgrade_spec(spec)).model_dump(mode="json")


def _with_new_fields(spec: dict[str, Any]) -> dict[str, Any]:
    """Fills fields added after the multi-level format: derive_walls, room labels, opening walls."""
    levels = []
    for level in spec["levels"]:
        floor = dict(level["floor"])
        floor.setdefault("derive_walls", True)
        floor["rooms"] = [{"label": None, **room} for room in floor["rooms"]]
        floor["openings"] = [{"wall": None, **opening} for opening in floor["openings"]]
        levels.append({**level, "floor": floor})
    return {**spec, "levels": levels}
