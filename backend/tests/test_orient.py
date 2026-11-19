import math

from factories import plan, rect

from floorplan.geometry import normalize
from floorplan.geometry.orient import dominant_angles
from floorplan.geometry.walls import derive_walls
from floorplan.models import Point, RoomSpec, RoomType


def rotated_room(room_id: str, corners, angle_degrees: float, noise=()) -> RoomSpec:
    a = math.radians(angle_degrees)
    points = []
    for i, (x, y) in enumerate(corners):
        dx, dy = noise[i] if i < len(noise) else (0, 0)
        points.append(
            Point(
                x=x * math.cos(a) - y * math.sin(a) + dx, y=x * math.sin(a) + y * math.cos(a) + dy
            )
        )
    return RoomSpec(id=room_id, name=room_id, type=RoomType.OTHER, outdoor=False, polygon=points)


def edge_angles(room: RoomSpec) -> set[float]:
    pts = [(p.x, p.y) for p in room.polygon]
    return {
        round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180, 2)
        for a, b in zip(pts, pts[1:] + pts[:1], strict=True)
    }


def test_slightly_rotated_scan_is_squared_to_the_axes():
    segments = [((0, 0), (4, 0.05)), ((4, 0.05), (3.95, 3)), ((0, 0), (0.05, 3))]

    assert sorted(dominant_angles(segments)) == [0.0, math.pi / 2]


def test_angled_wing_keeps_its_angle():
    main = rect("r1", 0, 0, 6, 4)
    wing = rotated_room("r2", [(7, -2), (10, -2), (10, 1), (7, 1)], 30)

    _, snapped = normalize(plan([main, wing])).rooms

    assert edge_angles(snapped) == {30.0, 120.0}


def test_noisy_shared_angled_edge_becomes_one_interior_wall():
    corners_a = [(0, 0), (4, 0), (4, 3), (0, 3)]
    corners_b = [(4, 0), (7, 0), (7, 3), (4, 3)]
    a = rotated_room("a", corners_a, 35)
    b = rotated_room("b", corners_b, 35, noise=[(0.04, -0.03), (0, 0), (0, 0), (-0.03, 0.05)])

    walls = derive_walls(normalize(plan([a, b])).rooms)

    interior = [w for w in walls if not w.exterior]
    assert len(interior) == 1
    assert math.dist(interior[0].start, interior[0].end) > 2.9


def test_parallel_walls_far_apart_stay_separate():
    rooms = normalize(plan([rect("r1", 0, 0, 4, 3), rect("r2", 4.3, 0, 7, 3)])).rooms

    assert {p.x for p in rooms[0].polygon} == {0.0, 4.0}
    assert {p.x for p in rooms[1].polygon} == {4.3, 7.0}
