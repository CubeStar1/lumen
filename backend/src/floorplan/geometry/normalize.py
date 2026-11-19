"""Snaps the model's approximate coordinates onto a clean, shared grid.

Vertex x and y values are clustered independently across all rooms, so edges that the
model drew almost straight become exactly axis-aligned and walls shared by neighbouring
rooms land on identical coordinates.
"""

from floorplan.models import PlanSpec, Point, RoomSpec

GRID = 0.05
CLUSTER_TOLERANCE = 0.15


def normalize(spec: PlanSpec) -> PlanSpec:
    vertices = [p for room in spec.rooms for p in room.polygon]
    x_map = _cluster([p.x for p in vertices])
    y_map = _cluster([p.y for p in vertices])
    rooms = [_snap_room(room, x_map, y_map) for room in spec.rooms]
    return spec.model_copy(update={"rooms": rooms})


def _snap_room(room: RoomSpec, x_map: dict[float, float], y_map: dict[float, float]) -> RoomSpec:
    snapped = [Point(x=x_map[p.x], y=y_map[p.y]) for p in room.polygon]
    return room.model_copy(update={"polygon": _drop_repeats(snapped)})


def _cluster(values: list[float]) -> dict[float, float]:
    mapping: dict[float, float] = {}
    group: list[float] = []
    for value in sorted(set(values)):
        if group and value - group[0] > CLUSTER_TOLERANCE:
            _assign(group, mapping)
            group = []
        group.append(value)
    if group:
        _assign(group, mapping)
    return mapping


def _assign(group: list[float], mapping: dict[float, float]) -> None:
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
