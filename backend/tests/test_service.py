import pytest
from factories import plan

from floorplan.errors import PlanRejectedError
from floorplan.llm.client import Feedback
from floorplan.models import FloorSpec
from floorplan.service import PlanService, single_floor


class ScriptedModel:
    def __init__(self, *answers: FloorSpec):
        self.answers = list(answers)
        self.feedback: list[Feedback | None] = []

    def extract(self, image_url: str, feedback: Feedback | None = None) -> FloorSpec:
        self.feedback.append(feedback)
        return self.answers.pop(0)

    def edit(
        self, floor: FloorSpec, instruction: str, feedback: Feedback | None = None
    ) -> FloorSpec:
        return self.extract("", feedback)


def test_valid_answer_is_used_directly(two_rooms):
    model = ScriptedModel(two_rooms)

    response = PlanService(model).parse("data:")

    assert model.feedback == [None]
    assert len(response.geometry.rooms) == 2


def test_invalid_answer_is_retried_with_feedback(two_rooms):
    model = ScriptedModel(plan([]), two_rooms)

    response = PlanService(model).parse("data:")

    assert model.feedback[1] is not None
    assert model.feedback[1].problems == ["No rooms were found."]
    assert len(response.geometry.rooms) == 2


def test_repeated_invalid_answer_is_rejected():
    model = ScriptedModel(plan([]), plan([]))

    with pytest.raises(PlanRejectedError):
        PlanService(model).parse("data:")


def test_edit_goes_through_the_same_pipeline(two_rooms):
    response = PlanService(ScriptedModel(two_rooms)).edit(single_floor(two_rooms), "bigger")

    assert response.spec.levels[0].floor.rooms[0].id == "r1"
