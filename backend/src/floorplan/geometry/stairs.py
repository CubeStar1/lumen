"""Turns stair specs into step boxes, landings, railings and the wells they cut in the floors.

Each stair climbs the full rise to the next floor, its risers spread evenly over its flights,
which are listed from the bottom up. A straight flight's steps are quads along its centre line; a
flight with a `via` point follows the circular arc through start, via and end. Railings run along
the sides of a flight that no wall is beside.

Across a building, an `up` stair on one level is paired with the `down` stair above that overlaps
it most: the lower one is built, the upper one becomes a well in its floor. A `down` stair with
nothing below is drawn as a well too. Stairs of a few steps only have their treads marked.
"""

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import unary_union

from floorplan.geometry.vec import Vec, add, length, normalized, point, scale, sub, vec
from floorplan.models import (
    FlightSpec,
    Landing,
    Point,
    Point3,
    Stair,
    StairDirection,
    StairSpec,
    Step,
    Wall,
    WallKind,
)

TREAD = 0.28
RISER_RANGE = (0.14, 0.2)
STANDARD_RISER = 0.17
SHORT_STAIR = 5
MARKER = 0.02
WALL_CLEARANCE = 0.15
WALLED_SHARE = 0.6
SIDE_SAMPLES = 7
PAIR_OVERLAP = 0.2
ARRIVAL_REACH = 0.4
LOW = (WallKind.LOW, WallKind.PARAPET)


@dataclass(frozen=True)
class Storey:
    """One level as the stair pass sees it, in world coordinates."""

    stairs: list[StairSpec]
    walls: list[Wall]
    rise: float


@dataclass
class StoreyStairs:
    stairs: list[Stair] = field(default_factory=list)
    wells: list[Polygon] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def building_stairs(storeys: list[Storey]) -> list[StoreyStairs]:
    result = [StoreyStairs() for _ in storeys]
    arrived: set[tuple[int, str]] = set()
    for index, storey in enumerate(storeys):
        above = storeys[index + 1] if index + 1 < len(storeys) else None
        for spec in storey.stairs:
            if spec.direction == StairDirection.DOWN or not spec.flights or _short(spec):
                continue
            stair, warnings = build_stair(spec, storey.walls, storey.rise)
            result[index].stairs.append(stair)
            result[index].warnings += warnings
            if above is None:
                continue
            partner = _partner(spec, above.stairs)
            well = footprint(partner) if partner else footprint(spec)
            if partner:
                arrived.add((index + 1, partner.id))
            arrival = vec(spec.flights[-1].end)
            result[index + 1].wells.append(well)
            result[index + 1].stairs.append(
                _well(partner.id if partner else spec.id, well, above.walls, arrival)
            )

    for index, storey in enumerate(storeys):
        for spec in storey.stairs:
            if (index, spec.id) in arrived or not spec.flights:
                continue
            if _short(spec):
                result[index].stairs.append(_markers(spec))
            elif spec.direction == StairDirection.DOWN:
                shape = footprint(spec)
                arrival = vec(spec.flights[-1].end)
                result[index].wells.append(shape)
                result[index].stairs.append(_well(spec.id, shape, storey.walls, arrival))
    return result


def build_stair(spec: StairSpec, walls: list[Wall], rise: float) -> tuple[Stair, list[str]]:
    """The stair's steps climbing `rise`. A stair drawn with too few risers for that is the part
    below the plan's cut line; it is built with ordinary risers and stops where the drawing does."""
    counts = [_risers(f) for f in spec.flights]
    riser = rise / sum(counts)
    warnings = []
    if riser > RISER_RANGE[1]:
        riser = STANDARD_RISER
        warnings.append(
            f"Stair {spec.id} shows only {sum(counts)} risers for a {rise:.2f} m rise; "
            "it is drawn as the start of a stair that continues above the plan's cut."
        )
    elif riser < RISER_RANGE[0]:
        warnings.append(
            f"Stair {spec.id}: risers of {riser * 100:.0f} cm "
            f"({sum(counts)} for a {rise:.2f} m rise) are lower than the usual 14-20 cm."
        )

    steps: list[Step] = []
    railings: list[list[Point3]] = []
    tops: list[tuple[Vec, float]] = []
    base = 0.0
    for flight, count in zip(spec.flights, counts, strict=True):
        quads = _treads(flight, count)
        for i, quad in enumerate(quads):
            steps.append(Step(corners=[point(c) for c in quad], bottom=0.0, top=_h(base, i, riser)))
        railings += _flight_railings(quads, base, riser, walls)
        base += count * riser
        tops.append((vec(flight.end), base))

    landings = [
        Landing(polygon=landing.polygon, height=round(_landing_height(landing.polygon, tops), 4))
        for landing in spec.landings
        if len(landing.polygon) >= 3
    ]
    stair = Stair(
        id=spec.id,
        direction=spec.direction,
        riser=round(riser, 4),
        steps=steps,
        landings=landings,
        railings=railings,
        footprint=_outline(footprint(spec)),
    )
    return stair, warnings


def _short(spec: StairSpec) -> bool:
    return sum(_risers(f) for f in spec.flights) <= SHORT_STAIR


def _markers(spec: StairSpec) -> Stair:
    """A few steps (to a porch, a sunken area) whose levels the plan doesn't give: their treads
    are marked on the floor rather than guessed."""
    steps = [
        Step(corners=[point(c) for c in quad], bottom=0.0, top=MARKER)
        for f in spec.flights
        for quad in _treads(f, _risers(f))
    ]
    return Stair(
        id=spec.id,
        direction=spec.direction,
        riser=0,
        steps=steps,
        landings=[],
        railings=[],
        footprint=_outline(footprint(spec)),
    )


def footprint(spec: StairSpec) -> Polygon:
    parts = [Polygon(q) for f in spec.flights for q in _treads(f, _risers(f))]
    parts += [Polygon([vec(p) for p in s.polygon]) for s in spec.landings if len(s.polygon) >= 3]
    shape = unary_union([p.buffer(0) for p in parts if p.area > 0]).buffer(0.02).buffer(-0.02)
    polygons = list(getattr(shape, "geoms", [shape]))
    polygons = [p for p in polygons if isinstance(p, Polygon) and not p.is_empty]
    if not polygons:
        return Polygon()
    return Polygon(max(polygons, key=lambda p: p.area).exterior).simplify(0.01)


def _risers(flight: FlightSpec) -> int:
    if flight.risers > 0:
        return flight.risers
    return max(2, round(_centre_length(flight) / TREAD) + 1)


def _h(base: float, i: int, riser: float) -> float:
    return round(base + (i + 1) * riser, 4)


def _treads(flight: FlightSpec, count: int) -> list[list[Vec]]:
    """One quad per riser, from the bottom step up: [left front, right front, right back,
    left back], left and right as seen walking up."""
    arc = _arc(flight)
    half = flight.width / 2
    if arc is None:
        start, end = vec(flight.start), vec(flight.end)
        along = sub(end, start)
        if length(along) < 1e-6:
            return []
        side = scale(_left(normalized(along)), half)
        cuts = [add(start, scale(along, i / count)) for i in range(count + 1)]
        return [
            [add(a, side), sub(a, side), sub(b, side), add(b, side)]
            for a, b in zip(cuts, cuts[1:], strict=False)
        ]

    centre, radius, a0, sweep = arc
    inner, outer = (radius - half, radius + half)
    left, right = (inner, outer) if sweep > 0 else (outer, inner)
    angles = [a0 + sweep * i / count for i in range(count + 1)]
    return [
        [
            _polar(centre, left, a),
            _polar(centre, right, a),
            _polar(centre, right, b),
            _polar(centre, left, b),
        ]
        for a, b in zip(angles, angles[1:], strict=False)
    ]


def _arc(flight: FlightSpec) -> tuple[Vec, float, float, float] | None:
    """Centre, radius, start angle and signed sweep of the arc through start, via and end."""
    if flight.via is None:
        return None
    (ax, ay), (bx, by), (cx, cy) = vec(flight.start), vec(flight.via), vec(flight.end)
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-6:
        return None
    ux = (
        (ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)
    ) / d
    uy = (
        (ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)
    ) / d
    centre = (ux, uy)
    radius = math.dist(centre, (ax, ay))
    a0, av, a1 = (math.atan2(y - uy, x - ux) for x, y in ((ax, ay), (bx, by), (cx, cy)))
    ccw = (a1 - a0) % math.tau
    sweep = ccw if (av - a0) % math.tau <= ccw else ccw - math.tau
    if radius <= flight.width / 2:
        return None
    return centre, radius, a0, sweep


def _centre_length(flight: FlightSpec) -> float:
    arc = _arc(flight)
    if arc is None:
        return math.dist(vec(flight.start), vec(flight.end))
    return abs(arc[1] * arc[3])


def _polar(centre: Vec, radius: float, angle: float) -> Vec:
    return (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))


def _left(direction: Vec) -> Vec:
    return (-direction[1], direction[0])


def _flight_railings(
    quads: list[list[Vec]], base: float, riser: float, walls: list[Wall]
) -> list[list[Point3]]:
    railings = []
    for front, back in ((0, 3), (1, 2)):
        side = [quads[0][front]] + [q[back] for q in quads] if quads else []
        if len(side) < 2 or _walled(side, walls):
            continue
        heights = [base + riser] + [_h(base, i, riser) for i in range(len(quads))]
        railings.append(
            [
                Point3(x=round(x, 4), y=round(y, 4), z=round(z, 4))
                for (x, y), z in zip(side, heights, strict=True)
            ]
        )
    return railings


def _well(stair_id: str, shape: Polygon, walls: list[Wall], arrival: Vec | None) -> Stair:
    """A stair arriving from below: the railing round its well's open edges, except the edge the
    stair arrives at."""
    corners = list(shape.exterior.coords)[:-1]
    railings, run = [], []
    for a, b in zip(corners, corners[1:] + corners[:1], strict=True):
        open_edge = not _walled([a, b], walls) and not _arrives(a, b, arrival)
        if open_edge:
            run = run or [a]
            run.append(b)
        elif run:
            railings.append(run)
            run = []
    if run:
        if railings and railings[0][0] == run[-1]:
            railings[0] = run[:-1] + railings[0]
        else:
            railings.append(run)
    return Stair(
        id=stair_id,
        direction=StairDirection.DOWN,
        riser=0,
        steps=[],
        landings=[],
        railings=[[Point3(x=round(x, 4), y=round(y, 4), z=0) for x, y in r] for r in railings],
        footprint=_outline(shape),
    )


def _arrives(a: Vec, b: Vec, arrival: Vec | None) -> bool:
    return arrival is not None and LineString([a, b]).distance(_pt(arrival)) <= ARRIVAL_REACH


def _walled(line: list[Vec], walls: list[Wall]) -> bool:
    path = LineString(line)
    if path.length < 1e-6:
        return True
    near = [
        (LineString([vec(w.start), vec(w.end)]), w.thickness / 2 + WALL_CLEARANCE)
        for w in walls
        if w.kind not in LOW
    ]
    samples = [
        path.interpolate((i + 0.5) / SIDE_SAMPLES, normalized=True) for i in range(SIDE_SAMPLES)
    ]
    walled = sum(any(seg.distance(s) <= reach for seg, reach in near) for s in samples)
    return walled >= WALLED_SHARE * SIDE_SAMPLES


def _partner(spec: StairSpec, candidates: list[StairSpec]) -> StairSpec | None:
    shape = footprint(spec)
    best, best_overlap = None, PAIR_OVERLAP
    for other in candidates:
        if other.direction != StairDirection.DOWN:
            continue
        theirs = footprint(other)
        smaller = min(shape.area, theirs.area)
        if smaller <= 0:
            continue
        overlap = shape.intersection(theirs).area / smaller
        if overlap > best_overlap:
            best, best_overlap = other, overlap
    return best


def _landing_height(polygon: list[Point], tops: list[tuple[Vec, float]]) -> float:
    shape = Polygon([vec(p) for p in polygon])
    return min(tops, key=lambda top: shape.distance(_pt(top[0])))[1]


def _pt(v: Vec) -> ShapelyPoint:
    return ShapelyPoint(v)


def _outline(shape: Polygon) -> list[Point]:
    if shape.is_empty:
        return []
    return [point(c) for c in shape.exterior.coords[:-1]]
