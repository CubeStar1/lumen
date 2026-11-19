from shapely.geometry import Polygon

from floorplan.geometry.regions import Label, assign, faces, wall_sides

OUTER = [((0, 0), (8, 0)), ((8, 0), (8, 5)), ((8, 5), (0, 5)), ((0, 5), (0, 0))]
SPLIT = [((5, 0), (5, 5))]


def test_walls_enclose_faces():
    assert sorted(round(f.area) for f in faces(OUTER + SPLIT)) == [15, 25]


def test_stub_walls_do_not_split_a_room():
    stub = [((5, 0), (5, 2))]

    assert [round(f.area) for f in faces(OUTER + stub)] == [40]


def test_each_label_takes_the_face_it_sits_in():
    regions, warnings = assign([Label("a", (2, 2)), Label("b", (6, 2))], OUTER + SPLIT)

    assert warnings == []
    assert {r.primary: round(r.shape.area) for r in regions} == {"a": 25, "b": 15}


def test_open_plan_face_keeps_both_labels():
    (region,), _ = assign([Label("living", (2, 2)), Label("dining", (6, 2))], OUTER)

    assert region.labels == ("living", "dining")


def test_unenclosed_label_falls_back_to_its_outline():
    porch = Polygon([(0, 5), (8, 5), (8, 7), (0, 7)])

    regions, warnings = assign([Label("p", (4, 6), fallback=porch)], OUTER)

    assert next(r for r in regions if r.primary == "p").shape.equals(porch)
    assert "not enclosed" in warnings[0]


def test_unlabelled_small_faces_are_dropped_and_large_ones_kept():
    duct = [((7, 0), (7, 1)), ((7, 1), (8, 1))]
    regions, _ = assign([Label("a", (2, 2))], OUTER + SPLIT + duct)

    assert sorted(round(r.shape.area) for r in regions) == [14, 25]


def test_wall_sides_name_the_rooms_either_side():
    rooms = {
        "a": Polygon([(0, 0), (5, 0), (5, 5), (0, 5)]),
        "b": Polygon([(5, 0), (8, 0), (8, 5), (5, 5)]),
    }

    sides = wall_sides(OUTER + SPLIT, rooms)

    faces_outside = [not left or not right for left, right in sides]
    assert faces_outside == [True, True, True, True, False]
    assert set(sides[4][0] | sides[4][1]) == {"a", "b"}
