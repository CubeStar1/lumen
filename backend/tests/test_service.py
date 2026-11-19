import pytest
from factories import drawing, two_room_drawing

from floorplan.errors import PlanRejectedError
from floorplan.imaging import PreparedImage
from floorplan.llm.client import Feedback
from floorplan.models import FloorSpec
from floorplan.service import PlanService, single_floor

IMAGE = PreparedImage("data:", 800, 400)


class ScriptedModel:
    """Answers extractions from a script; edits return the plan unchanged."""

    def __init__(self, *answers, sheet=None):
        self.answers = list(answers)
        self.sheet = sheet
        self.feedback: list[Feedback | None] = []
        self.hints: list[str | None] = []

    def extract(self, image: PreparedImage, feedback: Feedback | None = None, hint=None):
        self.feedback.append(feedback)
        self.hints.append(hint)
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]

    def read_sheet(self, image: PreparedImage):
        return self.sheet

    def edit(
        self, floor: FloorSpec, instruction: str, feedback: Feedback | None = None
    ) -> FloorSpec:
        return floor


def test_drawing_becomes_a_wall_first_plan_in_metres():
    response = PlanService(ScriptedModel(two_room_drawing())).parse(IMAGE)

    floor = response.spec.levels[0].floor
    assert not floor.derive_walls
    assert "Scale from 1 printed dimension" in floor.notes
    assert sorted(round(r.area) for r in response.geometry.rooms) == [9, 12]


def test_invalid_answer_is_retried_with_feedback_in_the_models_own_format():
    model = ScriptedModel(drawing(), two_room_drawing())

    response = PlanService(model).parse(IMAGE)

    assert model.feedback[1].problems == ["No rooms were found."]
    assert model.feedback[1].previous == drawing()
    assert len(response.geometry.rooms) == 2


def test_repeated_invalid_answer_is_rejected():
    with pytest.raises(PlanRejectedError):
        PlanService(ScriptedModel(drawing())).parse(IMAGE)


def test_edit_goes_through_the_same_pipeline(two_rooms):
    response = PlanService(ScriptedModel(drawing())).edit(single_floor(two_rooms), "bigger")

    assert response.spec.levels[0].floor.rooms[0].id == "r1"
