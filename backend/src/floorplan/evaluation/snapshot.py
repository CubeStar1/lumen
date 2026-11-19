"""A pipeline-independent view of a plan, in metres with +y up, that metrics compare."""

from dataclasses import dataclass, replace

from shapely import affinity
from shapely.geometry import Polygon

from floorplan.evaluation.reference import Reference
from floorplan.geometry.vec import Vec, add, normalized, scale, sub, vec
from floorplan.models import LevelGeometry, Point

Segment = tuple[Vec, Vec]

ROOM_CATEGORIES = {
    "toilet": "bathroom",
    "store": "utility",
    "garage": "utility",
    "porch": "balcony",
    "terrace": "balcony",
    "staircase": "hallway",
}
OPENING_CATEGORIES = {"sliding_door": "door"}


@dataclass(frozen=True)
class SnapshotRoom:
    type: str
    shape: Polygon


@dataclass(frozen=True)
class SnapshotOpening:
    type: str
    position: Vec
    width: float


@dataclass(frozen=True)
class SnapshotStair:
    shape: Polygon
    risers: int | None


@dataclass(frozen=True)
class Snapshot:
    walls: list[Segment]
    rooms: list[SnapshotRoom]
    openings: list[SnapshotOpening]
    stairs: list[SnapshotStair]

    def translated(self, offset: Vec) -> "Snapshot":
        def move(p: Vec) -> Vec:
            return add(p, offset)

        return replace(
            self,
            walls=[(move(a), move(b)) for a, b in self.walls],
            rooms=[replace(r, shape=_shift(r.shape, offset)) for r in self.rooms],
            openings=[replace(o, position=move(o.position)) for o in self.openings],
            stairs=[replace(s, shape=_shift(s.shape, offset)) for s in self.stairs],
        )


def from_reference(reference: Reference) -> Snapshot:
    unit = reference.metres_per_unit

    def convert(p: Point) -> Vec:
        return (p.x * unit, -p.y * unit)

    def shape(polygon: list[Point]) -> Polygon:
        return Polygon([convert(p) for p in polygon])

    return Snapshot(
        walls=[(convert(w.start), convert(w.end)) for w in reference.walls],
        rooms=[SnapshotRoom(room_category(r.type), shape(r.polygon)) for r in reference.rooms],
        openings=[
            SnapshotOpening(opening_category(o.type), convert(o.position), o.width * unit)
            for o in reference.openings
        ],
        stairs=[SnapshotStair(shape(s.polygon), s.risers) for s in reference.stairs],
    )


def from_geometry(geometry: LevelGeometry) -> Snapshot:
    walls: list[Segment] = []
    openings: list[SnapshotOpening] = []
    for wall in geometry.walls:
        start, end = vec(wall.start), vec(wall.end)
        walls.append((start, end))
        direction = normalized(sub(end, start))
        for opening in wall.openings:
            position = add(start, scale(direction, opening.offset))
            openings.append(
                SnapshotOpening(opening_category(opening.type), position, opening.width)
            )

    rooms = [
        SnapshotRoom(room_category(r.type), Polygon([vec(p) for p in r.polygon]))
        for r in geometry.rooms
    ]
    stairs = [
        SnapshotStair(Polygon([vec(p) for p in s.footprint]), len(s.steps) or None)
        for s in geometry.stairs
        if len(s.footprint) >= 3
    ]
    return Snapshot(walls=walls, rooms=rooms, openings=openings, stairs=stairs)


def room_category(kind: str) -> str:
    return ROOM_CATEGORIES.get(kind, kind)


def opening_category(kind: str) -> str:
    return OPENING_CATEGORIES.get(kind, kind)


def _shift(shape: Polygon, offset: Vec) -> Polygon:
    return affinity.translate(shape, xoff=offset[0], yoff=offset[1])
