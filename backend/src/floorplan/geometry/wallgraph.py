"""Joins loose wall segments into a connected wall graph.

The model's walls rarely meet exactly. Loose walls are cleaned against fixed ones (walls already
derived from room outlines) and against each other: duplicates of an existing wall are dropped,
nearby endpoints are merged, and dangling ends are extended or trimmed onto the wall they almost
touch. Ends that stay free are genuine stub walls.
"""

import math
from dataclasses import dataclass

from floorplan.geometry.vec import Vec, add, dot, length, normalized, point, scale, sub, vec
from floorplan.models import Wall, WallSpec

ENDPOINT_SNAP = 0.25
JUNCTION_REACH = 0.3
DUPLICATE_DISTANCE = 0.05
DUPLICATE_SHARE = 0.8
PARALLEL = math.radians(3)
MIN_LENGTH = 0.1


@dataclass
class _Segment:
    start: Vec
    end: Vec

    @property
    def axis(self) -> Vec:
        return sub(self.end, self.start)

    @property
    def span(self) -> float:
        return length(self.axis)

    def direction(self) -> Vec:
        return normalized(self.axis)


def connect[W: (Wall, WallSpec)](fixed: list[Wall], loose: list[W]) -> list[W]:
    """`loose` walls moved onto the graph formed with `fixed`; `fixed` walls never move."""
    anchors = [_segment(w) for w in fixed]
    kept = [w for w in loose if not any(_duplicates(_segment(w), a) for a in anchors)]
    segments = [_segment(w) for w in kept]

    _merge_endpoints(segments, [p for a in anchors for p in (a.start, a.end)])
    for index, segment in enumerate(segments):
        others = anchors + segments[:index] + segments[index + 1 :]
        for end in ("start", "end"):
            if not _is_joined(getattr(segment, end), others):
                _reach_junction(segment, end, others)

    return [
        w.model_copy(update={"start": point(s.start), "end": point(s.end)})
        for w, s in zip(kept, segments, strict=True)
        if s.span >= MIN_LENGTH
    ]


def _merge_endpoints(segments: list[_Segment], anchors: list[Vec]) -> None:
    ends = [(s, end) for s in segments for end in ("start", "end")]
    groups: list[list[tuple[_Segment, str]]] = []
    for item in ends:
        p = getattr(*item)
        group = next((g for g in groups if math.dist(getattr(*g[0]), p) <= ENDPOINT_SNAP), None)
        if group is None:
            groups.append([item])
        else:
            group.append(item)

    for group in groups:
        points = [getattr(*item) for item in group]
        centre = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
        target = min(anchors, key=lambda a: math.dist(a, centre), default=None)
        if target is None or math.dist(target, centre) > ENDPOINT_SNAP:
            target = centre if len(group) > 1 else points[0]
        for segment, end in group:
            setattr(segment, end, target)


def _reach_junction(segment: _Segment, end: str, others: list[_Segment]) -> None:
    tip = getattr(segment, end)
    outward = segment.direction() if end == "end" else scale(segment.direction(), -1)
    best: tuple[float, Vec] | None = None
    for other in others:
        hit = _crossing(tip, outward, other)
        if hit is None:
            continue
        travel = dot(sub(hit, tip), outward)
        if abs(travel) <= JUNCTION_REACH and (best is None or abs(travel) < abs(best[0])):
            best = (travel, hit)
    if best is not None:
        setattr(segment, end, best[1])


def _crossing(origin: Vec, direction: Vec, other: _Segment) -> Vec | None:
    """Where the line through `origin` along `direction` crosses `other` (within its span)."""
    axis = other.axis
    denominator = direction[0] * axis[1] - direction[1] * axis[0]
    if other.span < 1e-9 or abs(denominator) < math.sin(PARALLEL) * other.span:
        return None
    relative = sub(other.start, origin)
    t = (relative[0] * axis[1] - relative[1] * axis[0]) / denominator
    u = (relative[0] * direction[1] - relative[1] * direction[0]) / denominator
    if not -1e-6 <= u <= 1 + 1e-6:
        return None
    return add(origin, scale(direction, t))


def _is_joined(p: Vec, others: list[_Segment]) -> bool:
    return any(_distance_to(p, o) < 1e-6 for o in others)


def _duplicates(segment: _Segment, existing: _Segment) -> bool:
    if segment.span < 1e-9 or existing.span < 1e-9:
        return False
    cross = abs(
        segment.direction()[0] * existing.direction()[1]
        - segment.direction()[1] * existing.direction()[0]
    )
    if cross > math.sin(PARALLEL):
        return False
    samples = [add(segment.start, scale(segment.axis, (i + 0.5) / 10)) for i in range(10)]
    close = sum(_distance_to(p, existing) <= DUPLICATE_DISTANCE for p in samples)
    return close >= DUPLICATE_SHARE * len(samples)


def _distance_to(p: Vec, segment: _Segment) -> float:
    if segment.span < 1e-9:
        return math.dist(p, segment.start)
    t = min(max(dot(sub(p, segment.start), segment.axis) / segment.span**2, 0.0), 1.0)
    return math.dist(p, add(segment.start, scale(segment.axis, t)))


def _segment(wall: Wall | WallSpec) -> _Segment:
    return _Segment(vec(wall.start), vec(wall.end))
