import math

from factories import rect

from floorplan.geometry.walls import WallSegment, derive_walls
from floorplan.models import Point, RoomSpec, RoomType


def span(segment: WallSegment) -> float:
    return math.dist(segment.start, segment.end)


def test_single_room_has_four_exterior_walls():
    walls = derive_walls([rect("r1", 0, 0, 4, 3)])

    assert len(walls) == 4
    assert all(w.exterior for w in walls)
    assert sorted(round(span(w), 3) for w in walls) == [3, 3, 4, 4]


def test_shared_edge_becomes_one_interior_wall(two_rooms):
    walls = derive_walls(two_rooms.rooms)

    interior = [w for w in walls if not w.exterior]
    assert len(interior) == 1
    assert interior[0].rooms == {"r1", "r2"}
    assert span(interior[0]) == 3


def test_collinear_exterior_edges_merge_across_rooms(two_rooms):
    walls = derive_walls(two_rooms.rooms)

    exterior_lengths = sorted(round(span(w), 3) for w in walls if w.exterior)
    assert exterior_lengths == [3, 3, 7, 7]


def test_partial_overlap_splits_into_interior_and_exterior():
    walls = derive_walls([rect("r1", 0, 0, 4, 4), rect("r2", 4, 1, 6, 3)])

    on_shared_line = [w for w in walls if w.start[0] == w.end[0] == 4]
    kinds = sorted((round(span(w), 3), w.exterior) for w in on_shared_line)
    assert kinds == [(1, True), (1, True), (2, False)]


def test_l_shaped_room_has_six_walls():
    corners = [(0, 0), (6, 0), (6, 2), (3, 2), (3, 5), (0, 5)]
    room = RoomSpec(
        id="r1",
        name="L",
        type=RoomType.LIVING,
        outdoor=False,
        polygon=[Point(x=x, y=y) for x, y in corners],
    )

    walls = derive_walls([room])

    assert len(walls) == 6
    assert all(w.exterior for w in walls)
