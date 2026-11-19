"""Converts specs from image convention (origin top-left, +y down) to the world frame used by
the geometry and by Unity: +y up, with the whole building's footprint centred on the origin."""

from collections.abc import Callable
from dataclasses import dataclass

from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from floorplan.models import BuildingSpec, FloorSpec, LandingSpec, Point


@dataclass(frozen=True)
class Frame:
    centre_x: float
    centre_y: float

    def convert(self, p: Point, offset: Point) -> Point:
        return Point(
            x=round(p.x + offset.x - self.centre_x, 4), y=round(self.centre_y - p.y - offset.y, 4)
        )


def building_frame(spec: BuildingSpec) -> Frame:
    points = [
        (p.x + level.offset.x, p.y + level.offset.y)
        for level in spec.levels
        for room in level.floor.rooms
        for p in room.polygon
    ]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return Frame((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def to_world(floor: FloorSpec, frame: Frame, offset: Point) -> FloorSpec:
    moved = map_floor(floor, lambda p: frame.convert(p, offset))
    rooms = [r.model_copy(update={"polygon": counter_clockwise(r.polygon)}) for r in moved.rooms]
    return moved.model_copy(update={"rooms": rooms})


def map_floor(floor: FloorSpec, move: Callable[[Point], Point], lengths: float = 1.0) -> FloorSpec:
    """The floor with every point moved by `move` and every width multiplied by `lengths`."""

    def size(value: float) -> float:
        return round(value * lengths, 4)

    rooms = [
        r.model_copy(
            update={
                "polygon": [move(p) for p in r.polygon],
                "label": move(r.label) if r.label else None,
            }
        )
        for r in floor.rooms
    ]
    walls = [
        w.model_copy(
            update={
                "start": move(w.start),
                "end": move(w.end),
                "thickness": size(w.thickness) if w.thickness else None,
            }
        )
        for w in floor.walls
    ]
    openings = [
        o.model_copy(update={"position": move(o.position), "width": size(o.width)})
        for o in floor.openings
    ]
    stairs = [
        s.model_copy(
            update={
                "flights": [
                    f.model_copy(
                        update={
                            "start": move(f.start),
                            "end": move(f.end),
                            "via": move(f.via) if f.via else None,
                            "width": size(f.width),
                        }
                    )
                    for f in s.flights
                ],
                "landings": [
                    LandingSpec(polygon=[move(p) for p in landing.polygon])
                    for landing in s.landings
                ],
            }
        )
        for s in floor.stairs
    ]
    columns = [
        c.model_copy(update={"position": move(c.position), "size": size(c.size)})
        for c in floor.columns
    ]
    return floor.model_copy(
        update={
            "rooms": rooms,
            "walls": walls,
            "openings": openings,
            "stairs": stairs,
            "columns": columns,
        }
    )


def counter_clockwise(polygon: list[Point]) -> list[Point]:
    oriented = orient(Polygon([(p.x, p.y) for p in polygon]), sign=1.0)
    return [Point(x=x, y=y) for x, y in oriented.exterior.coords[:-1]]
