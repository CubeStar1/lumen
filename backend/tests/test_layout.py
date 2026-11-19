from factories import drawing, pixel_room, pixel_wall, px, two_room_drawing
from shapely.geometry import Polygon

from floorplan.extraction import PixelDimension, PixelOpening, to_floor
from floorplan.geometry.layout import complete
from floorplan.geometry.vec import vec
from floorplan.models import OpeningType, WallKind

SCALE = [PixelDimension(text="7 m", start=px(0, -40), end=px(700, -40))]
OUTER = [
    pixel_wall("e1", (0, 0), (700, 0), WallKind.EXTERIOR),
    pixel_wall("e2", (700, 0), (700, 300), WallKind.EXTERIOR),
    pixel_wall("e3", (700, 300), (0, 300), WallKind.EXTERIOR),
    pixel_wall("e4", (0, 300), (0, 0), WallKind.EXTERIOR),
]


def areas(floor) -> dict[str, float]:
    return {r.id: round(Polygon([vec(p) for p in r.polygon]).area, 1) for r in floor.rooms}


def test_rooms_are_found_from_the_walls():
    floor, warnings = complete(to_floor(two_room_drawing()))

    assert warnings == []
    assert areas(floor) == {"r1": 12.0, "r2": 9.0}


def test_open_plan_space_is_shared_between_its_labels():
    rooms = [pixel_room("living", 100, 150), pixel_room("dining", 500, 150)]

    floor, _ = complete(to_floor(drawing(walls=OUTER, rooms=rooms, dimensions=SCALE)))

    assert areas(floor) == {"living": 9.0, "dining": 12.0}


def test_wall_stopped_at_a_door_is_bridged_across_it():
    halves = [pixel_wall("a", (400, 0), (400, 100)), pixel_wall("b", (400, 190), (400, 300))]
    door = PixelOpening(id="o1", type=OpeningType.DOOR, wall="b", position=px(400, 145), width=90)
    rooms = [pixel_room("r1", 200, 150), pixel_room("r2", 550, 150)]
    extraction = drawing(walls=OUTER + halves, rooms=rooms, openings=[door], dimensions=SCALE)

    floor, _ = complete(to_floor(extraction))

    merged = next(w for w in floor.walls if w.id == "a")
    assert (merged.start.y, merged.end.y) == (0.0, 3.0)
    assert floor.openings[0].wall == "a"
    assert areas(floor) == {"r1": 12.0, "r2": 9.0}


def test_gap_without_an_opening_is_left_open():
    halves = [pixel_wall("a", (400, 0), (400, 100)), pixel_wall("b", (400, 190), (400, 300))]
    rooms = [pixel_room("r1", 200, 150), pixel_room("r2", 550, 150)]

    floor, _ = complete(to_floor(drawing(walls=OUTER + halves, rooms=rooms, dimensions=SCALE)))

    assert {w.id for w in floor.walls} >= {"a", "b"}
    assert sum(areas(floor).values()) == 21.0


def test_outdoor_rooms_keep_their_drawn_outline():
    porch = pixel_room(
        "p", 350, 350, polygon=[(0, 300), (700, 300), (700, 400), (0, 400)], outdoor=True
    )
    rooms = [pixel_room("r1", 350, 150), porch]

    floor, _ = complete(to_floor(drawing(walls=OUTER, rooms=rooms, dimensions=SCALE)))

    assert areas(floor) == {"r1": 21.0, "p": 7.0}


def test_low_walls_do_not_divide_rooms():
    planter = pixel_wall("low", (400, 0), (400, 300), WallKind.LOW)
    rooms = [pixel_room("r1", 200, 150)]

    floor, _ = complete(to_floor(drawing(walls=OUTER + [planter], rooms=rooms, dimensions=SCALE)))

    assert areas(floor) == {"r1": 21.0}


def test_large_unlabelled_space_is_kept_as_a_room():
    rooms = [pixel_room("r1", 200, 150)]
    split = pixel_wall("s", (400, 0), (400, 300))

    floor, _ = complete(to_floor(drawing(walls=OUTER + [split], rooms=rooms, dimensions=SCALE)))

    unnamed = [r for r in floor.rooms if r.id.startswith("u")]
    assert len(unnamed) == 1
    assert areas(floor)[unnamed[0].id] == 9.0


def test_open_plan_rooms_follow_their_traced_outlines():
    living = pixel_room("living", 100, 150, polygon=[(0, 0), (500, 0), (500, 300), (0, 300)])
    dining = pixel_room("dining", 600, 150, polygon=[(500, 0), (700, 0), (700, 300), (500, 300)])

    floor, _ = complete(to_floor(drawing(walls=OUTER, rooms=[living, dining], dimensions=SCALE)))

    assert areas(floor) == {"living": 15.0, "dining": 6.0}


def test_self_intersecting_outdoor_outline_is_repaired():
    bowtie = [(0, 300), (700, 400), (700, 300), (0, 400)]
    rooms = [pixel_room("r1", 350, 150), pixel_room("p", 100, 350, polygon=bowtie, outdoor=True)]

    floor, _ = complete(to_floor(drawing(walls=OUTER, rooms=rooms, dimensions=SCALE)))

    porch = next(r for r in floor.rooms if r.id == "p")
    assert Polygon([vec(q) for q in porch.polygon]).is_valid
