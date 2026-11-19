from factories import plan, rect

from floorplan.geometry import normalize
from floorplan.models import Point


def test_nearly_shared_edges_snap_to_the_same_coordinate():
    spec = plan([rect("r1", 0, 0, 4.0, 3.0), rect("r2", 4.08, 0.02, 7.0, 2.97)])

    r1, r2 = normalize(spec).rooms

    assert {p.x for p in r1.polygon} & {p.x for p in r2.polygon} == {4.05}
    assert {p.y for p in r1.polygon} == {p.y for p in r2.polygon} == {0.0, 3.0}


def test_skewed_edge_becomes_axis_aligned():
    room = rect("r1", 0, 0, 4, 3)
    room.polygon[1] = Point(x=4.06, y=0.04)

    (snapped,) = normalize(plan([room])).rooms

    assert snapped.polygon[0].y == snapped.polygon[1].y
    assert snapped.polygon[1].x == snapped.polygon[2].x


def test_collapsed_vertices_are_removed():
    room = rect("r1", 0, 0, 4, 3)
    room.polygon.insert(1, Point(x=0.03, y=0.02))

    (snapped,) = normalize(plan([room])).rooms

    assert len(snapped.polygon) == 4
