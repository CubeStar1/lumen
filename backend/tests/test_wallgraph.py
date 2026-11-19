from floorplan.geometry.wallgraph import connect
from floorplan.models import Point, Wall, WallKind


def wall(a, b, wall_id="w") -> Wall:
    return Wall(
        id=wall_id,
        start=Point(x=a[0], y=a[1]),
        end=Point(x=b[0], y=b[1]),
        kind=WallKind.INTERIOR,
        thickness=0.12,
        height=3.0,
        exterior=False,
    )


def ends(w: Wall):
    return (w.start.x, w.start.y), (w.end.x, w.end.y)


BOX = [wall((0, 0), (6, 0)), wall((6, 0), (6, 4)), wall((6, 4), (0, 4)), wall((0, 4), (0, 0))]


def test_short_stub_is_extended_onto_the_wall_it_almost_touches():
    (stub,) = connect(BOX, [wall((3, 0.2), (3, 2))])

    assert ends(stub) == ((3, 0), (3, 2))


def test_overshooting_end_is_trimmed_back_to_the_wall():
    (stub,) = connect(BOX, [wall((3, -0.2), (3, 2))])

    assert ends(stub) == ((3, 0), (3, 2))


def test_free_end_far_from_any_wall_stays_a_stub():
    (stub,) = connect(BOX, [wall((3, 0), (3, 2))])

    assert ends(stub)[1] == (3, 2)


def test_nearby_loose_endpoints_meet_at_one_corner():
    a, b = connect([], [wall((0, 0), (3, 0.1)), wall((3.1, -0.05), (3, 3))])

    assert ends(a)[1] == ends(b)[0]


def test_wall_on_top_of_an_existing_wall_is_dropped():
    assert connect(BOX, [wall((1, 0.02), (5, 0.02))]) == []
