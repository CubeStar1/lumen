from factories import opening, plan, rect

from floorplan.geometry import build_building
from floorplan.geometry.vec import edges
from floorplan.models import OpeningType
from floorplan.service import single_floor


def build_geometry(floor):
    geometry, warnings = build_building(single_floor(floor))
    return geometry.levels[0], warnings


def walls_with_openings(geometry):
    return {o.id: wall for wall in geometry.walls for o in wall.openings}


def test_plan_is_centred_with_y_up(two_rooms):
    building, _ = build_building(single_floor(two_rooms))
    geometry = building.levels[0]

    assert building.bounds.min.model_dump() == {"x": -3.5, "y": -1.5}
    assert building.bounds.max.model_dump() == {"x": 3.5, "y": 1.5}
    r1 = next(r for r in geometry.rooms if r.id == "r1")
    assert r1.centroid.model_dump() == {"x": -1.5, "y": 0.0}
    assert r1.area == 12


def test_room_polygons_are_counter_clockwise(two_rooms):
    geometry, _ = build_geometry(two_rooms)

    for room in geometry.rooms:
        signed_area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in edges(room.polygon))
        assert signed_area > 0


def test_openings_attach_to_the_right_walls(two_rooms):
    geometry, warnings = build_geometry(two_rooms)

    attached = walls_with_openings(geometry)
    assert warnings == []
    assert not attached["o1"].exterior
    assert attached["o2"].exterior

    door = attached["o1"].openings[0]
    assert (door.offset, door.width, door.sill, door.head) == (1.5, 0.9, 0.0, 2.1)
    window = attached["o2"].openings[0]
    assert (window.sill, window.head) == (0.9, 2.1)


def test_opening_far_from_walls_is_dropped():
    spec = plan([rect("r1", 0, 0, 4, 3)], [opening("o1", OpeningType.DOOR, ["r1", "r2"], 2, 1.5)])

    geometry, warnings = build_geometry(spec)

    assert walls_with_openings(geometry) == {}
    assert any("o1" in w for w in warnings)


def test_opening_near_corner_is_pulled_inside_the_wall():
    window = opening("o1", OpeningType.WINDOW, ["r1", "exterior"], 3.9, 0)
    spec = plan([rect("r1", 0, 0, 4, 3)], [window])

    geometry, _ = build_geometry(spec)

    window = walls_with_openings(geometry)["o1"].openings[0]
    assert window.offset + window.width / 2 <= 4 - 0.05


def test_overlapping_openings_keep_only_the_first():
    spec = plan(
        [rect("r1", 0, 0, 4, 3)],
        [
            opening("o1", OpeningType.WINDOW, ["r1", "exterior"], 2.0, 0),
            opening("o2", OpeningType.WINDOW, ["r1", "exterior"], 2.4, 0),
        ],
    )

    geometry, warnings = build_geometry(spec)

    assert set(walls_with_openings(geometry)) == {"o1"}
    assert any("o2" in w for w in warnings)


def test_listed_walls_take_their_kind_from_the_rooms_beside_them():
    from factories import two_room_drawing

    from floorplan.extraction import to_floor
    from floorplan.service import from_spec

    level = from_spec(single_floor(to_floor(two_room_drawing()))).geometry.levels[0]

    kinds = {w.id: w.exterior for w in level.walls}
    assert kinds == {"w1": True, "w2": True, "w3": True, "w4": True, "w5": False}
    assert walls_with_openings(level)["o1"].id == "w5"
    assert walls_with_openings(level)["o2"].id == "w1"
