from dataclasses import dataclass

from floorplan.geometry.vec import Vec, add, dot, length, normalized, scale, sub, vec
from floorplan.models import EXTERIOR, Opening, OpeningSpec, OpeningType, Wall

MAX_DISTANCE = 0.4
MISMATCH_PENALTY = 0.25
END_CLEARANCE = 0.05
MIN_WIDTH = 0.5
MAX_WIDTH = 3.0
DOOR_HEAD = 2.1
WINDOW_SILL = 0.9
WINDOW_HEAD = 2.1


@dataclass(frozen=True)
class _Candidate:
    wall: Wall
    offset: float
    score: float


def attach_openings(
    walls: list[Wall], wall_rooms: dict[str, frozenset[str]], openings: list[OpeningSpec]
) -> list[str]:
    warnings: list[str] = []
    for spec in openings:
        candidate = _best_wall(spec, walls, wall_rooms)
        if candidate is None:
            warnings.append(f"Opening {spec.id} is not near any wall; dropped.")
            continue
        opening = _fit(spec, candidate)
        if opening is None:
            warnings.append(f"Opening {spec.id} does not fit on its wall; dropped.")
        elif any(_overlaps(opening, other) for other in candidate.wall.openings):
            warnings.append(f"Opening {spec.id} overlaps another opening; dropped.")
        else:
            candidate.wall.openings.append(opening)

    for wall in walls:
        wall.openings.sort(key=lambda o: o.offset)
    return warnings


def _best_wall(
    spec: OpeningSpec, walls: list[Wall], wall_rooms: dict[str, frozenset[str]]
) -> _Candidate | None:
    position = vec(spec.position)
    named = next((w for w in walls if w.id == spec.wall), None) if spec.wall else None
    if named is not None:
        offset, distance = _project(position, named)
        if distance <= MAX_DISTANCE:
            return _Candidate(named, offset, distance)

    best: _Candidate | None = None
    for wall in walls:
        offset, distance = _project(position, wall)
        if distance > MAX_DISTANCE:
            continue
        score = distance + (0 if _matches(spec, wall, wall_rooms[wall.id]) else MISMATCH_PENALTY)
        if best is None or score < best.score:
            best = _Candidate(wall, offset, score)
    return best


def _project(position: Vec, wall: Wall) -> tuple[float, float]:
    """Offset along the wall of the point nearest `position`, and the distance to it."""
    start = vec(wall.start)
    axis = sub(vec(wall.end), start)
    direction = normalized(axis)
    offset = min(max(dot(sub(position, start), direction), 0.0), length(axis))
    return offset, length(sub(position, add(start, scale(direction, offset))))


def _matches(spec: OpeningSpec, wall: Wall, rooms: frozenset[str]) -> bool:
    if not spec.rooms:
        return True
    if EXTERIOR in spec.rooms:
        return wall.exterior and bool(rooms & set(spec.rooms))
    return not wall.exterior and set(spec.rooms) <= rooms


def _fit(spec: OpeningSpec, candidate: _Candidate) -> Opening | None:
    wall = candidate.wall
    span = length(sub(vec(wall.end), vec(wall.start)))
    width = min(max(spec.width, MIN_WIDTH), MAX_WIDTH, span - 2 * END_CLEARANCE)
    if width < MIN_WIDTH:
        return None
    half = width / 2 + END_CLEARANCE
    offset = min(max(candidate.offset, half), span - half)
    sill, head = (WINDOW_SILL, WINDOW_HEAD) if spec.type == OpeningType.WINDOW else (0.0, DOOR_HEAD)
    return Opening(
        id=spec.id,
        type=spec.type,
        offset=round(offset, 4),
        width=round(width, 4),
        sill=sill,
        head=min(head, wall.height - 0.1),
    )


def _overlaps(a: Opening, b: Opening) -> bool:
    return abs(a.offset - b.offset) < (a.width + b.width) / 2
