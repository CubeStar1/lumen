"""Hand-labelled ground truth for one evaluation case.

Coordinates are in drawing units with the image convention (origin top-left, +y down),
so a plan can be traced in pixels and given a single scale.
"""

from pathlib import Path

from pydantic import BaseModel

from floorplan.models import Point


class ReferenceWall(BaseModel):
    start: Point
    end: Point


class ReferenceRoom(BaseModel):
    name: str
    type: str
    polygon: list[Point]


class ReferenceOpening(BaseModel):
    type: str
    position: Point
    width: float


class ReferenceStair(BaseModel):
    polygon: list[Point]
    risers: int | None = None


class Reference(BaseModel):
    metres_per_unit: float = 1.0
    walls: list[ReferenceWall]
    rooms: list[ReferenceRoom]
    openings: list[ReferenceOpening] = []
    stairs: list[ReferenceStair] = []
    notes: str = ""


def load_reference(path: Path) -> Reference:
    return Reference.model_validate_json(path.read_text(encoding="utf-8"))
