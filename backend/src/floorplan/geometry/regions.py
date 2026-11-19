"""Finds rooms as the faces enclosed by the wall graph and gives them the model's room labels.

A face holding one label is that room. A face holding several labels is an open-plan space
whose first label sets the floor; the others are kept as labels only. A label in no face falls
back to the polygon the model drew, or a small square. Larger unlabelled faces are kept as
unnamed spaces; small ones are shafts and ducts and are dropped.
"""

from dataclasses import dataclass

from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import polygonize, unary_union

from floorplan.geometry.orient import Segment
from floorplan.geometry.vec import Vec, add, normalized, scale, sub

MIN_UNLABELLED_AREA = 1.5
FALLBACK_SIZE = 2.5
SIDE_PROBE = 0.3


@dataclass(frozen=True)
class Label:
    id: str
    point: Vec
    fallback: Polygon | None = None


@dataclass(frozen=True)
class Region:
    shape: Polygon
    labels: tuple[str, ...]

    @property
    def primary(self) -> str | None:
        return self.labels[0] if self.labels else None


def faces(walls: list[Segment]) -> list[Polygon]:
    lines = [LineString(segment) for segment in walls if segment[0] != segment[1]]
    if not lines:
        return []
    return [face for face in polygonize(unary_union(lines)) if face.area > 0]


def assign(labels: list[Label], walls: list[Segment]) -> tuple[list[Region], list[str]]:
    found = faces(walls)
    claimed: dict[int, list[str]] = {}
    regions: list[Region] = []
    warnings: list[str] = []

    for label in labels:
        index = next(
            (i for i, face in enumerate(found) if face.covers(ShapelyPoint(label.point))), None
        )
        if index is not None:
            claimed.setdefault(index, []).append(label.id)
            continue
        shape = label.fallback if label.fallback is not None else _square(label.point)
        source = "its drawn outline" if label.fallback is not None else "a default square"
        warnings.append(f"Room {label.id} is not enclosed by walls; using {source}.")
        regions.append(Region(shape, (label.id,)))

    for index, face in enumerate(found):
        if index in claimed:
            regions.append(Region(face, tuple(claimed[index])))
        elif face.area >= MIN_UNLABELLED_AREA:
            regions.append(Region(face, ()))
    return regions, warnings


def exterior_flags(walls: list[Segment], indoor: list[Polygon]) -> list[bool]:
    """A wall is exterior when one side of its midpoint lies outside every indoor space."""
    inside = unary_union(indoor) if indoor else Polygon()
    flags = []
    for start, end in walls:
        middle = scale(add(start, end), 0.5)
        direction = normalized(sub(end, start))
        normal = (-direction[1], direction[0])
        left = ShapelyPoint(add(middle, scale(normal, SIDE_PROBE)))
        right = ShapelyPoint(add(middle, scale(normal, -SIDE_PROBE)))
        flags.append(not (inside.covers(left) and inside.covers(right)))
    return flags


def _square(centre: Vec) -> Polygon:
    half = FALLBACK_SIZE / 2
    x, y = centre
    return Polygon(
        [(x - half, y - half), (x + half, y - half), (x + half, y + half), (x - half, y + half)]
    )
