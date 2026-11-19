"""Snaps the model's approximate outlines onto clean, shared lines.

Every room edge and extra wall is fitted to a line (see `orient`). Room vertices are rebuilt as
the intersections of consecutive edge lines, so edges the model drew almost straight become
exact, shared walls coincide, and angled walls keep their angle.
"""

import math

from shapely.geometry import Polygon

from floorplan.geometry.orient import Line, Segment, dominant_angles, fit_lines
from floorplan.geometry.vec import Vec, vec
from floorplan.models import FloorSpec, Point, RoomSpec, WallSpec

MIN_EDGE = 0.1
MAX_CORNER_SHIFT = 0.6
MAX_AREA_CHANGE = 0.2


def normalize(floor: FloorSpec) -> FloorSpec:
    outlines = [_without_short_edges([vec(p) for p in room.polygon]) for room in floor.rooms]
    room_edges = [list(zip(o, o[1:] + o[:1], strict=True)) for o in outlines]
    wall_segments: list[Segment] = [(vec(w.start), vec(w.end)) for w in floor.walls]
    segments = [e for edges in room_edges for e in edges] + wall_segments

    lines = fit_lines(segments, dominant_angles(segments))
    rooms: list[RoomSpec] = []
    cursor = 0
    for room, outline in zip(floor.rooms, outlines, strict=True):
        room_lines = lines[cursor : cursor + len(outline)]
        cursor += len(outline)
        rooms.append(room.model_copy(update={"polygon": _rebuild(outline, room_lines)}))

    walls = [
        snapped
        for wall, line in zip(floor.walls, lines[cursor:], strict=True)
        if (snapped := _snap_wall(wall, line)).start != snapped.end
    ]
    return floor.model_copy(update={"rooms": rooms, "walls": walls})


def _rebuild(outline: list[Vec], lines: list[Line]) -> list[Point]:
    if len(outline) < 3:
        return [_point(p) for p in outline]
    corners: list[Vec] = []
    for i, original in enumerate(outline):
        before, after = lines[i - 1], lines[i]
        if before == after:
            continue
        crossing = before.intersect(after)
        if crossing is None or math.dist(crossing, original) > MAX_CORNER_SHIFT:
            corners += [before.project(original), after.project(original)]
        else:
            corners.append(crossing)
    rebuilt = _drop_repeats([_point(c) for c in corners])
    return rebuilt if _acceptable(outline, rebuilt) else _drop_repeats([_point(p) for p in outline])


def _acceptable(original: list[Vec], rebuilt: list[Point]) -> bool:
    if len(rebuilt) < 3:
        return False
    before = Polygon(original)
    after = Polygon([(p.x, p.y) for p in rebuilt])
    if not after.is_valid or before.area <= 0:
        return False
    return abs(after.area - before.area) <= MAX_AREA_CHANGE * before.area


def _snap_wall(wall: WallSpec, line: Line) -> WallSpec:
    return wall.model_copy(
        update={
            "start": _point(line.project(vec(wall.start))),
            "end": _point(line.project(vec(wall.end))),
        }
    )


def _without_short_edges(points: list[Vec]) -> list[Vec]:
    kept: list[Vec] = []
    for p in points:
        if not kept or math.dist(p, kept[-1]) >= MIN_EDGE:
            kept.append(p)
    while len(kept) > 1 and math.dist(kept[0], kept[-1]) < MIN_EDGE:
        kept.pop()
    return kept


def _point(p: Vec) -> Point:
    return Point(x=round(p[0], 4) + 0.0, y=round(p[1], 4) + 0.0)


def _drop_repeats(polygon: list[Point]) -> list[Point]:
    result: list[Point] = []
    for p in polygon:
        if not result or p != result[-1]:
            result.append(p)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result
