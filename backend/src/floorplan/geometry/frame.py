"""Converts a spec from image convention (origin top-left, +y down) to the world frame
(origin at the footprint centre, +y up) used by the geometry and by Unity."""

from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from floorplan.models import Bounds, PlanSpec, Point


def to_world_frame(spec: PlanSpec) -> PlanSpec:
    xs = [p.x for room in spec.rooms for p in room.polygon]
    ys = [p.y for room in spec.rooms for p in room.polygon]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    def convert(p: Point) -> Point:
        return Point(x=round(p.x - cx, 4), y=round(cy - p.y, 4))

    rooms = [
        room.model_copy(update={"polygon": _counter_clockwise([convert(p) for p in room.polygon])})
        for room in spec.rooms
    ]
    openings = [o.model_copy(update={"position": convert(o.position)}) for o in spec.openings]
    return spec.model_copy(update={"rooms": rooms, "openings": openings})


def bounds_of(spec: PlanSpec) -> Bounds:
    xs = [p.x for room in spec.rooms for p in room.polygon]
    ys = [p.y for room in spec.rooms for p in room.polygon]
    return Bounds(min=Point(x=min(xs), y=min(ys)), max=Point(x=max(xs), y=max(ys)))


def _counter_clockwise(polygon: list[Point]) -> list[Point]:
    oriented = orient(Polygon([(p.x, p.y) for p in polygon]), sign=1.0)
    return [Point(x=x, y=y) for x, y in oriented.exterior.coords[:-1]]
