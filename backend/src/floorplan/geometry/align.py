"""Finds where an upper floor sits over the one below it.

Each floor is read from its own drawing, so their coordinates differ by an unknown shift. The
shift is chosen from a few candidates (stairs over stairs, matching outline corners and centres),
then refined, by how much of the upper floor's outer walls lands on walls of the floor below.
"""

from dataclasses import dataclass

from shapely.geometry import LineString, MultiLineString
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import unary_union
from shapely.prepared import prep

from floorplan.geometry.stairs import footprint
from floorplan.geometry.vec import Vec
from floorplan.models import FloorSpec, Point, WallKind

COINCIDENT = 0.15
MIN_SCORE = 0.4
SAMPLE_STEP = 0.25
REFINE = ((0.3, 0.1), (0.1, 0.025))


@dataclass(frozen=True)
class Alignment:
    offset: Point
    score: float
    confident: bool


def align(lower: FloorSpec, upper: FloorSpec) -> Alignment:
    """The shift to add to the upper floor's coordinates to place it over the lower floor."""
    below = _walls(lower, outer_only=False)
    above = _walls(upper, outer_only=True)
    if above.is_empty:
        above = _walls(upper, outer_only=False)
    if below.is_empty or above.is_empty:
        return Alignment(Point(x=0, y=0), 0.0, False)

    samples = _samples(above)
    reach = prep(below.buffer(COINCIDENT))

    def score(shift: Vec) -> float:
        return sum(reach.contains(_shifted(p, shift)) for p in samples) / len(samples)

    best = max(_candidates(lower, upper, below, above), key=score)
    for radius, step in REFINE:
        steps = round(radius / step)
        grid = [
            (best[0] + i * step, best[1] + j * step)
            for i in range(-steps, steps + 1)
            for j in range(-steps, steps + 1)
        ]
        best = max(grid, key=lambda s: (score(s), -abs(s[0] - best[0]) - abs(s[1] - best[1])))

    found = score(best)
    if found < MIN_SCORE:
        centre = _centre_shift(below, above)
        return Alignment(Point(x=round(centre[0], 3), y=round(centre[1], 3)), found, False)
    return Alignment(Point(x=round(best[0], 3), y=round(best[1], 3)), found, True)


def _walls(floor: FloorSpec, outer_only: bool) -> MultiLineString:
    kinds = (WallKind.EXTERIOR,) if outer_only else tuple(WallKind)
    lines = [
        LineString([(w.start.x, w.start.y), (w.end.x, w.end.y)])
        for w in floor.walls
        if w.kind in kinds
    ]
    if not lines and not floor.walls:
        lines = [
            LineString([(p.x, p.y) for p in r.polygon] + [(r.polygon[0].x, r.polygon[0].y)])
            for r in floor.rooms
            if not r.outdoor and len(r.polygon) >= 3
        ]
    return MultiLineString(lines) if lines else MultiLineString()


def _candidates(lower: FloorSpec, upper: FloorSpec, below, above) -> list[Vec]:
    candidates = [(0.0, 0.0), _centre_shift(below, above)]
    lx0, ly0, lx1, ly1 = below.bounds
    ux0, uy0, ux1, uy1 = above.bounds
    for lx, ux in ((lx0, ux0), (lx1, ux1)):
        for ly, uy in ((ly0, uy0), (ly1, uy1)):
            candidates.append((lx - ux, ly - uy))
    for a in lower.stairs:
        for b in upper.stairs:
            pa, pb = footprint(a), footprint(b)
            if not pa.is_empty and not pb.is_empty:
                candidates.append((pa.centroid.x - pb.centroid.x, pa.centroid.y - pb.centroid.y))
    return candidates


def _centre_shift(below, above) -> Vec:
    lx0, ly0, lx1, ly1 = below.bounds
    ux0, uy0, ux1, uy1 = above.bounds
    return ((lx0 + lx1) / 2 - (ux0 + ux1) / 2, (ly0 + ly1) / 2 - (uy0 + uy1) / 2)


def _samples(lines: MultiLineString) -> list[Vec]:
    merged = unary_union(lines)
    points: list[Vec] = []
    for line in getattr(merged, "geoms", [merged]):
        count = max(1, round(line.length / SAMPLE_STEP))
        for i in range(count):
            p = line.interpolate((i + 0.5) / count, normalized=True)
            points.append((p.x, p.y))
    return points


def _shifted(p: Vec, shift: Vec) -> ShapelyPoint:
    return ShapelyPoint(p[0] + shift[0], p[1] + shift[1])
