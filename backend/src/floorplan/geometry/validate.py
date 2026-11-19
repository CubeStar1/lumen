from dataclasses import dataclass, field
from itertools import combinations

from shapely.geometry import Polygon

from floorplan.models import EXTERIOR, PlanSpec

MIN_ROOM_AREA = 1.0
MAX_OVERLAP_RATIO = 0.05


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate(spec: PlanSpec) -> ValidationReport:
    report = ValidationReport()
    if not spec.rooms:
        report.errors.append("No rooms were found.")
        return report

    _check_unique("room", [r.id for r in spec.rooms], report)
    _check_unique("opening", [o.id for o in spec.openings], report)

    shapes: dict[str, Polygon] = {}
    for room in spec.rooms:
        if len(room.polygon) < 3:
            report.errors.append(f"Room {room.id} has fewer than 3 distinct vertices.")
            continue
        shape = Polygon([(p.x, p.y) for p in room.polygon])
        if not shape.is_valid:
            report.errors.append(f"Room {room.id} outline intersects itself.")
        elif shape.area < MIN_ROOM_AREA:
            report.warnings.append(f"Room {room.id} is smaller than {MIN_ROOM_AREA} m².")
        shapes[room.id] = shape

    _check_overlaps(shapes, report)
    _check_opening_rooms(spec, report)
    return report


def _check_unique(kind: str, ids: list[str], report: ValidationReport) -> None:
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        report.errors.append(f"Duplicate {kind} ids: {', '.join(duplicates)}.")


def _check_overlaps(shapes: dict[str, Polygon], report: ValidationReport) -> None:
    valid = {room_id: s for room_id, s in shapes.items() if s.is_valid}
    for (id_a, a), (id_b, b) in combinations(valid.items(), 2):
        overlap = a.intersection(b).area
        if overlap > MAX_OVERLAP_RATIO * min(a.area, b.area):
            report.warnings.append(f"Rooms {id_a} and {id_b} overlap by {overlap:.1f} m².")


def _check_opening_rooms(spec: PlanSpec, report: ValidationReport) -> None:
    known = {r.id for r in spec.rooms} | {EXTERIOR}
    for opening in spec.openings:
        unknown = [r for r in opening.rooms if r not in known]
        if unknown:
            report.warnings.append(
                f"Opening {opening.id} references unknown rooms: {', '.join(unknown)}."
            )
