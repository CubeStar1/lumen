import time

import pytest
from factories import plan, rect, two_room_drawing, wall
from PIL import Image
from test_service import ScriptedModel

from floorplan.building import (
    BuildingAnswers,
    BuildingReader,
    BuildingSource,
    FloorAnswer,
    level_name,
    rebuild,
    shared_scale,
    stack,
)
from floorplan.geometry.align import align, place
from floorplan.jobs import JobBoard, JobState, StageState
from floorplan.models import (
    BuildingKind,
    FlightSpec,
    FloorSpec,
    Point,
    StairDirection,
    StairSpec,
    WallKind,
)
from floorplan.service import PlanService
from floorplan.sheet import (
    Box,
    DrawingKind,
    SheetDrawing,
    SheetReading,
    crop,
    floor_drawings,
    level_from_title,
)


class Stages:
    def __init__(self):
        self.events: list[tuple[str, str]] = []

    def plan(self, stages):
        self.events += [("plan", s) for s in stages]

    def start(self, stage):
        self.events.append(("start", stage))

    def finish(self, stage):
        self.events.append(("finish", stage))


def outlined(x0, y0, x1, y1, kind=WallKind.EXTERIOR):
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [
        wall(f"w{i + 1}", a, b, kind)
        for i, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1], strict=True))
    ]


def walled_floor(x0, y0, x1, y1):
    floor = plan([rect("r1", x0, y0, x1, y1)], walls=outlined(x0, y0, x1, y1))
    return floor.model_copy(update={"derive_walls": False})


def drawing_on_sheet(title, level, box, rotation=0):
    return SheetDrawing(
        kind=DrawingKind.FLOOR_PLAN, title=title, level=level, box=Box(**box), rotation=rotation
    )


@pytest.mark.parametrize(
    ("title", "level"),
    [
        ("GROUND FLOOR PLAN", 0),
        ("First Floor Plan", 1),
        ("2nd floor", 2),
        ("LEVEL 3", 3),
        ("TERRACE FLOOR PLAN", 99),
        ("Basement", -1),
        ("Kitchen detail", None),
    ],
)
def test_level_from_title(title, level):
    assert level_from_title(title) == level


def test_level_name_drops_the_word_plan():
    assert level_name("FIRST FLOOR PLAN", 1) == "First floor"


def test_crop_scales_the_box_and_turns_the_drawing_upright():
    sheet = Image.new("RGB", (2000, 1000), "white")

    part = crop(sheet, Box(left=100, top=50, right=300, bottom=150), (1000, 500), 90)

    assert part.size == (212, 424)


def test_sheet_floors_come_out_lowest_first():
    reading = SheetReading(
        drawings=[
            drawing_on_sheet(
                "FIRST FLOOR PLAN", 1, {"left": 500, "top": 0, "right": 900, "bottom": 400}
            ),
            SheetDrawing(
                kind=DrawingKind.SECTION,
                title="SECTION A-A",
                level=None,
                box=Box(left=0, top=500, right=400, bottom=700),
                rotation=0,
            ),
            drawing_on_sheet(
                "GROUND FLOOR PLAN", 0, {"left": 0, "top": 0, "right": 400, "bottom": 400}
            ),
        ],
        floor_to_floor=None,
        slab=None,
        notes="",
    )

    floors = floor_drawings(Image.new("RGB", (1000, 800)), reading, (1000, 800))

    assert [f.title for f in floors] == ["GROUND FLOOR PLAN", "FIRST FLOOR PLAN"]


def test_align_recovers_a_known_shift():
    lower = walled_floor(0, 0, 8, 6)
    lower.walls.append(wall("w9", (4, 0), (4, 6), WallKind.INTERIOR))
    upper = walled_floor(10.4, -2.3, 18.4, 3.7)

    fit = align(lower, upper)

    assert fit.confident
    assert (fit.offset.x, fit.offset.y) == pytest.approx((-10.4, 2.3), abs=0.03)


def test_floors_stack_with_elevations_offsets_and_a_roof():
    ground = walled_floor(0, 0, 8, 6)
    first = walled_floor(2, 1, 10, 7).model_copy(update={"name": "First floor"})
    terrace = walled_floor(0, 0, 8, 6).model_copy(update={"name": "Terrace"})
    terrace.rooms[0] = terrace.rooms[0].model_copy(update={"outdoor": True})

    response = stack([(ground, []), (first, []), (terrace, [])], [False, False, True], 3.15)

    levels = response.spec.levels
    assert response.spec.kind == BuildingKind.BUILDING
    assert [lv.elevation for lv in levels] == [0, 3.15, 6.3]
    assert levels[1].floor.height == 3.0
    assert (levels[1].offset.x, levels[1].offset.y) == pytest.approx((-2, -1), abs=0.03)
    roof_walls = response.geometry.levels[2].walls
    assert {w.kind for w in roof_walls} == {WallKind.PARAPET}
    assert all(w.height == 1.0 for w in roof_walls)


def sheet_reading():
    return SheetReading(
        drawings=[
            drawing_on_sheet(
                "GROUND FLOOR PLAN", 0, {"left": 0, "top": 0, "right": 400, "bottom": 300}
            ),
            drawing_on_sheet(
                "FIRST FLOOR PLAN", 1, {"left": 400, "top": 0, "right": 800, "bottom": 300}
            ),
        ],
        floor_to_floor=3.2,
        slab=0.2,
        notes="",
    )


def test_sheet_is_read_floor_by_floor_with_hints_and_stages():
    model = ScriptedModel(two_room_drawing(), sheet=sheet_reading())
    stages = Stages()

    read = BuildingReader(PlanService(model), 2048).from_sheet(
        Image.new("RGB", (1600, 600)), stages
    )
    response = read.response

    assert [lv.floor.name for lv in response.spec.levels] == ["Ground floor", "First floor"]
    assert [lv.elevation for lv in response.spec.levels] == [0, 3.2]
    assert sorted(model.hints) == [
        "It is one floor of a building: First floor.",
        "It is one floor of a building: Ground floor.",
    ]
    assert ("finish", "Stacking floors") in stages.events


def test_photos_are_ordered_by_the_floor_names_the_model_reads():
    upper = two_room_drawing().model_copy(update={"name": "First floor"})
    model = ScriptedModel(upper, two_room_drawing())

    response = (
        BuildingReader(PlanService(model), 2048)
        .from_photos([Image.new("RGB", (100, 100))] * 2, Stages())
        .response
    )

    assert [lv.floor.name for lv in response.spec.levels] == ["Ground floor", "First floor"]


def test_job_board_reports_stages_and_the_saved_plan():
    board = JobBoard(workers=1)

    def work(progress):
        progress.plan(["One", "Two"])
        progress.start("One")
        progress.finish("One")
        return "abc"

    job = board.submit(work)
    for _ in range(100):
        job = board.get(job.id)
        if job.state != JobState.RUNNING:
            break
        time.sleep(0.01)

    assert job.state == JobState.DONE
    assert job.plan_id == "abc"
    assert job.progress == 1.0
    assert all(s.state == StageState.DONE for s in job.stages)


def test_failed_job_keeps_the_error():
    board = JobBoard(workers=1)

    def work(progress):
        raise ValueError("boom")

    job = board.submit(work)
    for _ in range(100):
        job = board.get(job.id)
        if job.state != JobState.RUNNING:
            break
        time.sleep(0.01)

    assert job.state == JobState.FAILED
    assert "boom" in job.error


def ring_floor(corners, kind=WallKind.EXTERIOR, name="Floor"):
    walls = [
        wall(f"w{i + 1}", a, b, kind)
        for i, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1], strict=True))
    ]
    room = rect("r1", 0, 0, 1, 1).model_copy(
        update={"polygon": [Point(x=x, y=y) for x, y in corners]}
    )
    return FloorSpec(
        name=name,
        height=3.0,
        derive_walls=False,
        rooms=[room],
        walls=walls,
        openings=[],
        stairs=[],
        columns=[],
        notes="",
    )


L_SHAPE = [(0, 0), (10, 0), (10, 4), (4, 4), (4, 12), (0, 12)]


def moved(corners, dx, dy):
    return [(x + dx, y + dy) for x, y in corners]


def straight_stair(x, y):
    return StairSpec(
        id="s1",
        direction=StairDirection.UP,
        flights=[
            FlightSpec(
                start=Point(x=x, y=y), end=Point(x=x, y=y + 3), width=1.0, risers=18, via=None
            )
        ],
        landings=[],
    )


def test_terrace_lines_up_by_its_parapets_and_stair_not_its_headroom():
    lower = ring_floor(L_SHAPE)
    lower.stairs.append(straight_stair(2, 6))
    terrace = ring_floor(moved(L_SHAPE, 3.7, -1.2), WallKind.PARAPET, "Terrace")
    terrace.rooms[0] = terrace.rooms[0].model_copy(update={"outdoor": True})
    headroom = [(4.7, 3.8), (6.7, 3.8), (6.7, 8.8), (4.7, 8.8)]
    terrace.walls += ring_floor(headroom).walls
    terrace.stairs.append(straight_stair(5.7, 4.8))

    fit = align(lower, terrace)

    assert fit.confident and fit.rotation == 0
    assert (fit.offset.x, fit.offset.y) == pytest.approx((-3.7, 1.2), abs=0.03)


def test_quarter_turned_floor_is_turned_back():
    lower = ring_floor(L_SHAPE)
    turned = [(-y, x) for x, y in L_SHAPE]
    upper = ring_floor(moved(turned, 20, 5))

    fit = align(lower, upper)
    placed = place(upper, fit)

    assert fit.rotation in (90, 270)
    corners = {
        (round(w.start.x + fit.offset.x, 1), round(w.start.y + fit.offset.y, 1))
        for w in placed.walls
    }
    assert corners == {(float(x), float(y)) for x, y in L_SHAPE}


def test_photo_drawn_at_another_scale_is_rescaled():
    lower = ring_floor(L_SHAPE)
    upper = ring_floor([(x * 1.06 + 2, y * 1.06 + 1) for x, y in L_SHAPE])

    fixed = align(lower, upper, fit_scale=True)
    kept = align(lower, upper, fit_scale=False)

    assert fixed.scale == pytest.approx(0.94, abs=0.011)
    assert fixed.score > kept.score


def answer(scale, dimensions, name):
    extraction = two_room_drawing().model_copy(update={"name": name, "dimensions": dimensions})
    return FloorAnswer(name=name, roof=False, image_scale=scale, extraction=extraction)


def test_sheet_floors_share_one_scale_even_without_dimensions_of_their_own():
    ground = answer(1.0, two_room_drawing().dimensions, "Ground floor")
    first = answer(1.0, [], "First floor")
    first.extraction.metres_per_pixel = 0.05
    answers = BuildingAnswers(source=BuildingSource.SHEET, sheet=None, floors=[ground, first])

    levels = rebuild(answers).spec.levels

    widths = [
        max(w.end.x for w in lv.floor.walls) - min(w.start.x for w in lv.floor.walls)
        for lv in levels
    ]
    assert widths == pytest.approx([7.0, 7.0], abs=0.05)
    assert "across every floor" in levels[1].floor.notes


def test_shared_scale_allows_for_crops_shown_at_different_sizes():
    floors = [answer(1.0, two_room_drawing().dimensions, "Ground floor"), answer(0.5, [], "First")]

    metres_per_sheet_pixel, _ = shared_scale(floors)

    assert metres_per_sheet_pixel == pytest.approx(0.01)


def test_saved_answers_rebuild_the_same_building():
    answers = BuildingAnswers(
        source=BuildingSource.PHOTOS,
        sheet=None,
        floors=[answer(1.0, two_room_drawing().dimensions, "Ground floor")],
    )

    again = BuildingAnswers.model_validate_json(answers.model_dump_json())

    assert rebuild(again).spec == rebuild(answers).spec
