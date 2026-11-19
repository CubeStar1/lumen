"""Snaps the model's approximate coordinates onto a clean, shared grid.

Vertex x and y values of rooms and walls are clustered independently, so edges that the model
drew almost straight become exactly axis-aligned and walls shared by neighbouring rooms land on
identical coordinates.
"""

from floorplan.models import FloorSpec, Point, RoomSpec, WallSpec

GRID = 0.05
CLUSTER_TOLERANCE = 0.15

Snap = dict[float, float]


def normalize(floor: FloorSpec) -> FloorSpec:
    vertices = [p for room in floor.rooms for p in room.polygon]
    vertices += [p for wall in floor.walls for p in (wall.start, wall.end)]
    x_map = _cluster([p.x for p in vertices])
    y_map = _cluster([p.y for p in vertices])
    rooms = [_snap_room(room, x_map, y_map) for room in floor.rooms]
    walls = [
        w for w in (_snap_wall(wall, x_map, y_map) for wall in floor.walls) if w.start != w.end
    ]
    return floor.model_copy(update={"rooms": rooms, "walls": walls})


def _snap(p: Point, x_map: Snap, y_map: Snap) -> Point:
    return Point(x=x_map[p.x], y=y_map[p.y])


def _snap_room(room: RoomSpec, x_map: Snap, y_map: Snap) -> RoomSpec:
    snapped = [_snap(p, x_map, y_map) for p in room.polygon]
    return room.model_copy(update={"polygon": _drop_repeats(snapped)})


def _snap_wall(wall: WallSpec, x_map: Snap, y_map: Snap) -> WallSpec:
    return wall.model_copy(
        update={"start": _snap(wall.start, x_map, y_map), "end": _snap(wall.end, x_map, y_map)}
    )


def _cluster(values: list[float]) -> Snap:
    mapping: Snap = {}
    group: list[float] = []
    for value in sorted(set(values)):
        if group and value - group[0] > CLUSTER_TOLERANCE:
            _assign(group, mapping)
            group = []
        group.append(value)
    if group:
        _assign(group, mapping)
    return mapping


def _assign(group: list[float], mapping: Snap) -> None:
    centre = round(round(sum(group) / len(group) / GRID) * GRID, 4)
    for value in group:
        mapping[value] = centre


def _drop_repeats(polygon: list[Point]) -> list[Point]:
    result: list[Point] = []
    for p in polygon:
        if not result or p != result[-1]:
            result.append(p)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result
