import pytest
from factories import opening, plan, rect

from floorplan.models import FloorSpec, OpeningType


@pytest.fixture
def two_rooms() -> FloorSpec:
    """Two rooms side by side: r1 is 4 x 3 m, r2 is 3 x 3 m, sharing the wall at x = 4."""
    return plan(
        [rect("r1", 0, 0, 4, 3), rect("r2", 4, 0, 7, 3)],
        [
            opening("o1", OpeningType.DOOR, ["r1", "r2"], 4, 1.5),
            opening("o2", OpeningType.WINDOW, ["r1", "exterior"], 2, 0, width=1.2),
        ],
    )
