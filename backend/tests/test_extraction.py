import pytest
from factories import drawing, pixel_wall, px, two_room_drawing

from floorplan.extraction import PixelDimension, PixelOpening, drawing_scale, to_floor
from floorplan.models import OpeningType


def test_scale_comes_from_printed_dimensions():
    scale, note = drawing_scale(two_room_drawing())

    assert scale == pytest.approx(0.01)
    assert "1 printed dimension" in note


def test_feet_and_inches_dimensions_set_the_scale():
    dims = [PixelDimension(text="15'-3\"", start=px(0, 0), end=px(465, 0))]

    scale, _ = drawing_scale(drawing(dimensions=dims))

    assert scale == pytest.approx(4.6482 / 465)


def test_printed_room_sizes_set_the_scale_without_dimension_lines():
    plan = two_room_drawing().model_copy(update={"dimensions": []})
    plan.rooms[0] = plan.rooms[0].model_copy(update={"size": "3.85 x 2.85"})

    scale, note = drawing_scale(plan)

    assert scale == pytest.approx(0.01)
    assert "printed room size" in note


def test_without_any_sizes_the_models_guess_is_used():
    scale, note = drawing_scale(drawing())

    assert scale == 0.02
    assert "estimated by the model" in note


def test_doors_are_the_last_resort():
    door = PixelOpening(id="o1", type=OpeningType.DOOR, wall="w1", position=px(0, 0), width=45)
    plan = drawing(openings=[door]).model_copy(update={"metres_per_pixel": 0})

    scale, note = drawing_scale(plan)

    assert scale == pytest.approx(0.02)
    assert "door widths" in note


def test_pixels_become_metres():
    floor = to_floor(two_room_drawing())

    w5 = next(w for w in floor.walls if w.id == "w5")
    assert (w5.start.x, w5.end.y) == (4.0, 3.0)
    assert floor.openings[0].width == pytest.approx(0.9)
    assert floor.openings[0].wall == "w5"
    assert floor.rooms[0].label.x == 2.0
    assert floor.rooms[0].polygon == []


def test_thickness_converts_when_given():
    wall = pixel_wall("w1", (0, 0), (100, 0)).model_copy(update={"thickness": 23})

    (converted,) = to_floor(drawing(walls=[wall], dimensions=[])).walls

    assert converted.thickness == pytest.approx(0.46)
