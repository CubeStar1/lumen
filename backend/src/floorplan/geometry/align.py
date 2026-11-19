"""Finds where an upper floor sits over the one below it.

Each floor is read from its own drawing, so their coordinates differ by an unknown shift, and
sometimes by a quarter turn or (between photos) a slightly different scale. Candidate placements
are scored by how much of the upper floor lands on the floor below:

- its outline (the outer edge of everything drawn, parapets included) on the lower outline;
- all of its walls on the lower walls;
- its stairs on the lower stairs, since a staircase continues straight up.

Each is counted at a loose and two tighter distances, so the fit peaks where the walls coincide.

The shift is searched on a coarse grid over every placement where the two outlines overlap,
then refined. A turn is taken only if it fits clearly better than none, and a scale only if it
fits better than the drawing's own.
"""

import math
from dataclasses import dataclass

import numpy as np
from shapely import contains_xy, prepare
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from floorplan.geometry.frame import map_floor
from floorplan.geometry.stairs import footprint
from floorplan.models import FloorSpec, Point

REACHES = (0.2, 0.08, 0.03)
MIN_SCORE = 0.4
OUTLINE_STEP = 0.2
WALL_STEP = 0.25
STAIR_STEP = 0.2
WALL_REACH = 0.1
COARSE_STEP = 0.25
SEARCH_MARGIN = 1.0
REFINE = ((0.3, 0.05), (0.06, 0.01))
SCALE_REFINE = ((0.5, 0.1), *REFINE)
TURNS = (0, 90, 180, 270)
TURN_MARGIN = 0.1
SCALES = tuple(round(0.92 + 0.02 * i, 2) for i in range(9))
SCALE_MARGIN = 0.03
WEIGHTS = {"outline": 0.55, "walls": 0.25, "stairs": 0.2}

Vec = tuple[float, float]


@dataclass(frozen=True)
class Alignment:
    """Turn the upper floor by `rotation` degrees and scale it by `scale` about `centre` (see
    `place`), then add `offset` to put it over the lower floor."""

    offset: Point
    rotation: int
    scale: float
    centre: Point
    score: float
    confident: bool


def align(lower: FloorSpec, upper: FloorSpec, fit_scale: bool = False) -> Alignment:
    target = _Target.of(lower)
    samples = _Samples.of(upper)
    centre = _point(samples.centre, 4)
    if target is None or samples.outline.size == 0:
        return Alignment(Point(x=0, y=0), 0, 1.0, centre, 0.0, False)

    fits = {turn: _search(target, samples.moved(turn, 1.0)) for turn in TURNS}
    turn = max(fits, key=lambda t: fits[t][1] - (0 if t == 0 else TURN_MARGIN))
    shift, score = fits[turn]
    scale = 1.0
    if fit_scale:
        for factor in SCALES:
            found, found_score = _refine(target, samples.moved(turn, factor), shift, SCALE_REFINE)
            if found_score > score + SCALE_MARGIN:
                shift, score, scale = found, found_score, factor

    if score < MIN_SCORE:
        centred = (target.centre[0] - samples.centre[0], target.centre[1] - samples.centre[1])
        return Alignment(_point(centred), 0, 1.0, centre, score, False)
    return Alignment(_point(shift), turn, scale, centre, score, True)


def place(floor: FloorSpec, fit: Alignment) -> FloorSpec:
    """The floor turned and scaled as the alignment says, about its centre. The shift is left to
    the level's offset."""
    if fit.rotation == 0 and fit.scale == 1.0:
        return floor
    cx, cy = fit.centre.x, fit.centre.y
    cos, sin = _turn(fit.rotation)

    def move(p: Point) -> Point:
        dx, dy = (p.x - cx) * fit.scale, (p.y - cy) * fit.scale
        return Point(x=round(cx + dx * cos - dy * sin, 4), y=round(cy + dx * sin + dy * cos, 4))

    return map_floor(floor, move, fit.scale)


@dataclass(frozen=True)
class _Target:
    """The lower floor, as areas that upper samples can land in."""

    outline: tuple
    walls: tuple
    stairs: tuple | None
    bounds: tuple[float, float, float, float]
    centre: Vec

    @staticmethod
    def of(floor: FloorSpec) -> "_Target | None":
        shape = _footprint(floor)
        if shape is None:
            return None
        lines = _wall_lines(floor)
        stair_shapes = _stair_shapes(floor)
        outline = _reaches(shape.exterior)
        walls = _reaches(unary_union(lines)) if lines else outline
        stairs = _reaches(unary_union(stair_shapes), (WALL_REACH,)) if stair_shapes else None
        centroid = shape.centroid
        return _Target(outline, walls, stairs, shape.bounds, (centroid.x, centroid.y))


@dataclass(frozen=True)
class _Samples:
    """The upper floor, as points along its outline and walls and inside its stairs."""

    outline: np.ndarray
    walls: np.ndarray
    stairs: np.ndarray
    centre: Vec

    @staticmethod
    def of(floor: FloorSpec) -> "_Samples":
        shape = _footprint(floor)
        if shape is None:
            empty = np.empty((0, 2))
            return _Samples(empty, empty, empty, (0.0, 0.0))
        centroid = shape.centroid
        return _Samples(
            outline=_along([shape.exterior], OUTLINE_STEP),
            walls=_along(_wall_lines(floor), WALL_STEP),
            stairs=_inside(_stair_shapes(floor), STAIR_STEP),
            centre=(centroid.x, centroid.y),
        )

    def moved(self, turn: int, scale: float) -> "_Samples":
        cos, sin = _turn(turn)
        matrix = np.array([[cos, sin], [-sin, cos]]) * scale
        centre = np.array(self.centre)

        def apply(points: np.ndarray) -> np.ndarray:
            return (points - centre) @ matrix + centre if points.size else points

        return _Samples(apply(self.outline), apply(self.walls), apply(self.stairs), self.centre)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        xs, ys = self.outline[:, 0], self.outline[:, 1]
        return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def _search(target: _Target, samples: _Samples) -> tuple[Vec, float]:
    """Every shift that keeps the outlines overlapping, coarsely, then refined around the best."""
    lx0, ly0, lx1, ly1 = target.bounds
    ux0, uy0, ux1, uy1 = samples.bounds
    coarse = [(x, y) for x in _span(lx0 - ux0, lx1 - ux1) for y in _span(ly0 - uy0, ly1 - uy1)]
    best = max(coarse, key=lambda s: _score(target, samples, s))
    return _refine(target, samples, best, REFINE)


def _refine(
    target: _Target, samples: _Samples, start: Vec, rounds: tuple[tuple[float, float], ...]
) -> tuple[Vec, float]:
    best = start
    for radius, step in rounds:
        steps = round(radius / step)
        origin = best
        grid = [
            (origin[0] + i * step, origin[1] + j * step)
            for i in range(-steps, steps + 1)
            for j in range(-steps, steps + 1)
        ]
        best = max(grid, key=lambda s: (_score(target, samples, s), -math.dist(s, origin)))
    return best, _score(target, samples, best)


def _score(target: _Target, samples: _Samples, shift: Vec) -> float:
    parts = [(WEIGHTS["outline"], _hits(target.outline, samples.outline, shift))]
    if samples.walls.size:
        parts.append((WEIGHTS["walls"], _hits(target.walls, samples.walls, shift)))
    if target.stairs is not None and samples.stairs.size:
        parts.append((WEIGHTS["stairs"], _hits(target.stairs, samples.stairs, shift)))
    return sum(w * h for w, h in parts) / sum(w for w, _ in parts)


def _hits(reaches: tuple, points: np.ndarray, shift: Vec) -> float:
    xs, ys = points[:, 0] + shift[0], points[:, 1] + shift[1]
    return float(np.mean([contains_xy(area, xs, ys).mean() for area in reaches]))


def _reaches(geometry, reaches: tuple[float, ...] = REACHES) -> tuple:
    """The areas within each reach of the geometry, prepared for fast point tests."""
    areas = tuple(geometry.buffer(reach) for reach in reaches)
    for area in areas:
        prepare(area)
    return areas


def _span(a: float, b: float) -> list[float]:
    low, high = min(a, b) - SEARCH_MARGIN, max(a, b) + SEARCH_MARGIN
    count = max(1, math.ceil((high - low) / COARSE_STEP))
    return [low + i * (high - low) / count for i in range(count + 1)]


def _footprint(floor: FloorSpec) -> Polygon | None:
    """Everything drawn on the floor with its holes filled: walls of every kind, indoor rooms."""
    parts = [line.buffer(WALL_REACH) for line in _wall_lines(floor)]
    parts += [
        Polygon([(p.x, p.y) for p in r.polygon]).buffer(0)
        for r in floor.rooms
        if not r.outdoor and len(r.polygon) >= 3
    ]
    shape = unary_union(parts)
    polygons = [g for g in getattr(shape, "geoms", [shape]) if isinstance(g, Polygon)]
    if not polygons:
        return None
    return Polygon(max(polygons, key=lambda g: g.area).exterior)


def _wall_lines(floor: FloorSpec) -> list[LineString]:
    return [
        LineString([(w.start.x, w.start.y), (w.end.x, w.end.y)])
        for w in floor.walls
        if (w.start.x, w.start.y) != (w.end.x, w.end.y)
    ]


def _stair_shapes(floor: FloorSpec) -> list[Polygon]:
    return [shape for shape in (footprint(s) for s in floor.stairs) if not shape.is_empty]


def _along(lines, step: float) -> np.ndarray:
    points = []
    for line in lines:
        count = max(1, round(line.length / step))
        for i in range(count):
            p = line.interpolate((i + 0.5) / count, normalized=True)
            points.append((p.x, p.y))
    return np.array(points) if points else np.empty((0, 2))


def _inside(shapes: list[Polygon], step: float) -> np.ndarray:
    found = []
    for shape in shapes:
        x0, y0, x1, y1 = shape.bounds
        xs, ys = np.meshgrid(np.arange(x0 + step / 2, x1, step), np.arange(y0 + step / 2, y1, step))
        grid = np.column_stack([xs.ravel(), ys.ravel()])
        if grid.size:
            found.append(grid[contains_xy(shape, grid[:, 0], grid[:, 1])])
    return np.concatenate(found) if found else np.empty((0, 2))


def _turn(degrees: int) -> tuple[float, float]:
    radians = math.radians(degrees)
    return round(math.cos(radians)), round(math.sin(radians))


def _point(v: Vec, digits: int = 3) -> Point:
    return Point(x=round(v[0], digits), y=round(v[1], digits))
