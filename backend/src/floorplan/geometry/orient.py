"""Finds a plan's dominant wall directions and fits every edge onto a shared line.

Edges within a few degrees of a dominant direction take that direction exactly, and parallel
edges whose offsets are close share one line. Neighbouring rooms therefore meet on exactly the
same wall, while angled wings keep their angle instead of being forced onto the x/y axes.
"""

import math
from collections import defaultdict
from dataclasses import dataclass

from floorplan.geometry.vec import Vec

Segment = tuple[Vec, Vec]

ANGLE_TOLERANCE = math.radians(4)
SAME_ANGLE = math.radians(0.5)
AXIS_SNAP = math.radians(2)
RIGHT_ANGLE_SNAP = math.radians(3)
MIN_PEAK_SHARE = 0.05
OFFSET_TOLERANCE = 0.15
GRID = 0.05
BIN = math.radians(1)


@dataclass(frozen=True)
class Line:
    """The line {p : normal · p = offset}, with direction angle in [0, π)."""

    angle: float
    offset: float

    @property
    def direction(self) -> Vec:
        return (math.cos(self.angle), math.sin(self.angle))

    @property
    def normal(self) -> Vec:
        return (-math.sin(self.angle), math.cos(self.angle))

    def project(self, p: Vec) -> Vec:
        n = self.normal
        distance = n[0] * p[0] + n[1] * p[1] - self.offset
        return (p[0] - n[0] * distance, p[1] - n[1] * distance)

    def intersect(self, other: "Line") -> Vec | None:
        (a, b), (c, d) = self.normal, other.normal
        determinant = a * d - b * c
        if abs(determinant) < 1e-9:
            return None
        return (
            (self.offset * d - b * other.offset) / determinant,
            (a * other.offset - self.offset * c) / determinant,
        )


def angle_of(segment: Segment) -> float:
    (x0, y0), (x1, y1) = segment
    return math.atan2(y1 - y0, x1 - x0) % math.pi


def angle_between(a: float, b: float) -> float:
    return abs((a - b + math.pi / 2) % math.pi - math.pi / 2)


def dominant_angles(segments: list[Segment]) -> list[float]:
    """Length-weighted peaks of the segment angle histogram, strongest first."""
    weighted = [(angle_of(s), _length(s)) for s in segments if _length(s) > 0]
    total = sum(w for _, w in weighted)
    remaining = list(weighted)
    peaks: list[float] = []
    while remaining:
        centre = max(
            (i * BIN for i in range(round(math.pi / BIN))),
            key=lambda c: sum(w for a, w in remaining if angle_between(a, c) <= 2 * BIN),
        )
        members = [(a, w) for a, w in remaining if angle_between(a, centre) <= ANGLE_TOLERANCE]
        if sum(w for _, w in members) < MIN_PEAK_SHARE * total:
            break
        peaks.append(_mean_angle(members))
        remaining = [(a, w) for a, w in remaining if angle_between(a, centre) > ANGLE_TOLERANCE]
    return _square_up(peaks)


def fit_lines(segments: list[Segment], peaks: list[float]) -> list[Line]:
    """One line per segment: its angle snapped to a peak, its offset shared with parallel
    neighbours."""
    angles = _snapped_angles(segments, peaks)
    groups: dict[float, list[int]] = defaultdict(list)
    for index, angle in enumerate(angles):
        groups[angle].append(index)

    lines: list[Line | None] = [None] * len(segments)
    for angle, indices in groups.items():
        probe = Line(angle, 0.0)
        offsets = [(_offset(probe, segments[i]), _length(segments[i]), i) for i in indices]
        for cluster in _cluster(offsets):
            mean = sum(o * w for o, w, _ in cluster) / max(sum(w for _, w, _ in cluster), 1e-9)
            line = Line(angle, _round_offset(angle, mean))
            for _, _, i in cluster:
                lines[i] = line
    return [line for line in lines if line is not None]


def _snapped_angles(segments: list[Segment], peaks: list[float]) -> list[float]:
    angles: list[float] = []
    loose: list[float] = []
    for segment in segments:
        raw = angle_of(segment)
        peak = min(peaks, key=lambda p: angle_between(raw, p), default=None)
        if peak is not None and angle_between(raw, peak) <= ANGLE_TOLERANCE:
            angles.append(peak)
            continue
        match = next((a for a in loose if angle_between(a, raw) <= SAME_ANGLE), None)
        if match is None:
            loose.append(raw)
            match = raw
        angles.append(match)
    return angles


def _square_up(peaks: list[float]) -> list[float]:
    squared: list[float] = []
    for peak in peaks:
        for axis in (0.0, math.pi / 2):
            if angle_between(peak, axis) <= AXIS_SNAP:
                peak = axis
        for anchor in squared:
            perpendicular = (anchor + math.pi / 2) % math.pi
            if angle_between(peak, perpendicular) <= RIGHT_ANGLE_SNAP:
                peak = perpendicular
        if all(angle_between(peak, other) > ANGLE_TOLERANCE for other in squared):
            squared.append(peak % math.pi)
    return squared


def _cluster(offsets: list[tuple[float, float, int]]) -> list[list[tuple[float, float, int]]]:
    clusters: list[list[tuple[float, float, int]]] = []
    for item in sorted(offsets):
        if clusters and item[0] - clusters[-1][0][0] <= OFFSET_TOLERANCE:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def _round_offset(angle: float, offset: float) -> float:
    axis_aligned = angle_between(angle, 0.0) < 1e-9 or angle_between(angle, math.pi / 2) < 1e-9
    step = GRID if axis_aligned else 0.001
    return round(round(offset / step) * step, 4)


def _mean_angle(members: list[tuple[float, float]]) -> float:
    x = sum(w * math.cos(2 * a) for a, w in members)
    y = sum(w * math.sin(2 * a) for a, w in members)
    return (math.atan2(y, x) / 2) % math.pi


def _offset(line: Line, segment: Segment) -> float:
    (x0, y0), (x1, y1) = segment
    n = line.normal
    return n[0] * (x0 + x1) / 2 + n[1] * (y0 + y1) / 2


def _length(segment: Segment) -> float:
    (x0, y0), (x1, y1) = segment
    return math.hypot(x1 - x0, y1 - y0)
