"""Derives walls from room outlines.

Every room edge lies on some infinite line. Edges are grouped by line, and each line is
swept as a set of 1D intervals: a stretch covered by two rooms is an interior wall, a
stretch covered by one room is an exterior wall.
"""

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

from floorplan.geometry.vec import Vec, add, dot, edges, normalized, scale, sub
from floorplan.models import RoomSpec

MIN_SEGMENT = 0.02

LineKey = tuple[float, float, float]


@dataclass(frozen=True)
class Line:
    direction: Vec
    normal: Vec
    offset: float

    @property
    def key(self) -> LineKey:
        return (round(self.direction[0], 3), round(self.direction[1], 3), round(self.offset, 3))

    def at(self, t: float) -> Vec:
        return add(scale(self.normal, self.offset), scale(self.direction, t))


@dataclass(frozen=True)
class WallSegment:
    start: Vec
    end: Vec
    exterior: bool
    rooms: frozenset[str]


@dataclass(frozen=True)
class _Interval:
    start: float
    end: float
    room: str


def derive_walls(rooms: list[RoomSpec]) -> list[WallSegment]:
    lines: dict[LineKey, Line] = {}
    intervals: dict[LineKey, list[_Interval]] = defaultdict(list)

    for room in rooms:
        for a, b in edges(room.polygon):
            if a == b:
                continue
            line = _line_through(a, b)
            line = lines.setdefault(line.key, line)
            t0, t1 = sorted((dot(a, line.direction), dot(b, line.direction)))
            intervals[line.key].append(_Interval(t0, t1, room.id))

    return [segment for key, line in lines.items() for segment in _sweep(line, intervals[key])]


def _line_through(a: Vec, b: Vec) -> Line:
    direction = normalized(sub(b, a))
    if direction[0] < -1e-9 or (abs(direction[0]) <= 1e-9 and direction[1] < 0):
        direction = scale(direction, -1)
    normal = (-direction[1], direction[0])
    return Line(direction, normal, dot(normal, a))


def _sweep(line: Line, intervals: list[_Interval]) -> list[WallSegment]:
    cuts = sorted({t for interval in intervals for t in (interval.start, interval.end)})
    segments: list[WallSegment] = []
    run_start = run_end = 0.0
    run_exterior: bool | None = None
    run_rooms: frozenset[str] = frozenset()

    def flush() -> None:
        if run_exterior is not None:
            segments.append(
                WallSegment(line.at(run_start), line.at(run_end), run_exterior, run_rooms)
            )

    for t0, t1 in pairwise(cuts):
        if t1 - t0 < MIN_SEGMENT:
            continue
        middle = (t0 + t1) / 2
        rooms = frozenset(i.room for i in intervals if i.start <= middle <= i.end)
        exterior = len(rooms) == 1
        if rooms and exterior == run_exterior and t0 - run_end < MIN_SEGMENT:
            run_end, run_rooms = t1, run_rooms | rooms
            continue
        flush()
        if rooms:
            run_start, run_end, run_exterior, run_rooms = t0, t1, exterior, rooms
        else:
            run_exterior = None

    flush()
    return segments
