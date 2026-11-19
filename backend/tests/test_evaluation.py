from factories import opening, plan, rect

from floorplan.evaluation.metrics import score
from floorplan.evaluation.reference import Reference
from floorplan.evaluation.snapshot import from_geometry, from_reference
from floorplan.models import OpeningType
from floorplan.service import from_spec, single_floor


def _reference(metres_per_unit: float = 1.0) -> Reference:
    unit = 1 / metres_per_unit
    return Reference.model_validate(
        {
            "metres_per_unit": metres_per_unit,
            "walls": [
                {"start": {"x": a * unit, "y": b * unit}, "end": {"x": c * unit, "y": d * unit}}
                for a, b, c, d in [
                    (0, 0, 7, 0),
                    (7, 0, 7, 3),
                    (7, 3, 0, 3),
                    (0, 3, 0, 0),
                    (4, 0, 4, 3),
                ]
            ],
            "rooms": [
                {"name": "A", "type": "other", "polygon": _square(0, 4, unit)},
                {"name": "B", "type": "other", "polygon": _square(4, 7, unit)},
            ],
            "openings": [
                {"type": "door", "position": {"x": 4 * unit, "y": 1.5 * unit}, "width": 0.9 * unit},
                {"type": "window", "position": {"x": 2 * unit, "y": 0}, "width": 1.2 * unit},
            ],
        }
    )


def _square(x0: float, x1: float, unit: float) -> list[dict]:
    return [{"x": x * unit, "y": y * unit} for x, y in [(x0, 0), (x1, 0), (x1, 3), (x0, 3)]]


def _prediction(width: float = 7.0):
    spec = plan(
        [rect("r1", 0, 0, 4, 3), rect("r2", 4, 0, width, 3)],
        [
            opening("o1", OpeningType.DOOR, ["r1", "r2"], 4, 1.5),
            opening("o2", OpeningType.WINDOW, ["r1", "exterior"], 2, 0, width=1.2),
        ],
    )
    return from_geometry(from_spec(single_floor(spec)).geometry.levels[0])


def test_identical_plan_scores_perfectly_despite_recentring():
    result = score(_prediction(), from_reference(_reference()))

    assert result.wall_f1 == 1.0
    assert result.room_iou == 1.0
    assert result.opening_recall == 1.0
    assert result.scale_ratio == 1.0


def test_pixel_references_are_scaled_to_metres():
    result = score(_prediction(), from_reference(_reference(metres_per_unit=0.02)))

    assert result.wall_f1 == 1.0
    assert result.rooms_matched == "2/2"


def test_wrong_room_size_lowers_wall_and_room_scores():
    result = score(_prediction(width=8.0), from_reference(_reference()))

    assert result.wall_f1 < 0.9
    assert result.room_iou < 1.0
    assert result.scale_ratio > 1.0
