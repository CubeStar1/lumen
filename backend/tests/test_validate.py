from factories import plan, rect

from floorplan.geometry import validate
from floorplan.models import Point


def test_valid_plan_has_no_errors(two_rooms):
    report = validate(two_rooms)

    assert report.errors == []
    assert report.warnings == []


def test_empty_plan_is_an_error():
    assert validate(plan([])).errors


def test_self_intersecting_room_is_an_error():
    room = rect("r1", 0, 0, 4, 3)
    room.polygon[1], room.polygon[2] = room.polygon[2], room.polygon[1]

    assert any("intersects" in e for e in validate(plan([room])).errors)


def test_duplicate_ids_are_an_error():
    report = validate(plan([rect("r1", 0, 0, 4, 3), rect("r1", 4, 0, 7, 3)]))

    assert any("Duplicate room" in e for e in report.errors)


def test_overlapping_rooms_are_a_warning():
    report = validate(plan([rect("r1", 0, 0, 4, 3), rect("r2", 2, 0, 6, 3)]))

    assert report.errors == []
    assert any("overlap" in w for w in report.warnings)


def test_degenerate_room_is_an_error():
    room = rect("r1", 0, 0, 4, 3)
    room.polygon = [Point(x=0, y=0), Point(x=4, y=0)]

    assert validate(plan([room])).errors
