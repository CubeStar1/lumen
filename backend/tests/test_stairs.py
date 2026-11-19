import math

import pytest
from factories import plan, rect

from floorplan.geometry.build import build_building
from floorplan.geometry.stairs import Storey, build_stair, building_stairs, footprint
from floorplan.models import (
    BuildingKind,
    BuildingSpec,
    FlightSpec,
    LandingSpec,
    LevelSpec,
    Point,
    StairDirection,
    StairSpec,
    Wall,
    WallKind,
)


def flight(a, b, risers=10, width=1.0, via=None) -> FlightSpec:
    return FlightSpec(
        start=Point(x=a[0], y=a[1]),
        end=Point(x=b[0], y=b[1]),
        width=width,
        risers=risers,
        via=Point(x=via[0], y=via[1]) if via else None,
    )


def stair(*flights, landings=(), direction=StairDirection.UP, stair_id="s1") -> StairSpec:
    return StairSpec(
        id=stair_id,
        direction=direction,
        flights=list(flights),
        landings=[LandingSpec(polygon=[Point(x=x, y=y) for x, y in poly]) for poly in landings],
    )


def solid_wall(a, b) -> Wall:
    return Wall(
        id="w",
        start=Point(x=a[0], y=a[1]),
        end=Point(x=b[0], y=b[1]),
        kind=WallKind.INTERIOR,
        thickness=0.12,
        height=3.0,
        exterior=False,
    )


def test_straight_flight_spreads_the_rise_over_its_risers():
    built, warnings = build_stair(stair(flight((0, 0), (0, 4.5), risers=18)), [], 3.0)

    assert len(built.steps) == 18
    assert built.riser == pytest.approx(3.0 / 18, abs=1e-4)
    assert built.steps[-1].top == pytest.approx(3.0)
    assert built.steps[0].corners[0].y == pytest.approx(0)
    assert built.steps[-1].corners[2].y == pytest.approx(4.5)
    assert warnings == []


def test_stair_cut_by_the_drawing_keeps_ordinary_risers():
    built, warnings = build_stair(stair(flight((0, 0), (0, 1.7), risers=6)), [], 3.0)

    assert built.riser == pytest.approx(0.17)
    assert built.steps[-1].top == pytest.approx(1.02)
    assert "continues above" in warnings[0]


def test_a_few_steps_are_only_marked():
    (level,) = building_stairs([Storey([stair(flight((0, 0), (0, 0.6), risers=2))], [], 3.0)])

    assert [s.top for s in level.stairs[0].steps] == [0.02, 0.02]
    assert level.wells == []


def test_dog_leg_stair_climbs_through_its_landing():
    spec = stair(
        flight((0, 0), (0, 2.5), risers=9, width=1.0),
        flight((1.1, 2.5), (1.1, 0), risers=9, width=1.0),
        landings=[[(-0.5, 2.5), (1.6, 2.5), (1.6, 3.5), (-0.5, 3.5)]],
    )

    built, _ = build_stair(spec, [], 3.0)

    assert built.landings[0].height == pytest.approx(1.5)
    assert built.steps[9].top == pytest.approx(1.5 + 3.0 / 18, abs=1e-4)
    assert footprint(spec).area == pytest.approx(2.5 * 2 + 2.1 * 1.0 + 0.1 * 2.5, rel=0.05)


def test_curved_flight_follows_its_arc():
    spec = stair(flight((2, 0), (-2, 0), risers=16, width=1.0, via=(0, 2)))

    built, _ = build_stair(spec, [], 3.0)

    radii = {round(math.hypot(c.x, c.y), 2) for s in built.steps for c in s.corners}
    assert radii == {1.5, 2.5}
    assert all(c.y >= -1e-6 for s in built.steps for c in s.corners)


def test_railings_go_on_the_sides_without_a_wall():
    spec = stair(flight((0, 0), (0, 4), risers=18, width=1.0))

    open_both, _ = build_stair(spec, [], 3.0)
    beside_wall, _ = build_stair(spec, [solid_wall((-0.56, -1), (-0.56, 5))], 3.0)

    assert len(open_both.railings) == 2
    assert len(beside_wall.railings) == 1
    rail = beside_wall.railings[0]
    assert rail[0].x == pytest.approx(0.5) and rail[-1].z == pytest.approx(3.0)


def test_up_stair_pairs_with_the_down_stair_above():
    lower = stair(flight((0, 0), (0, 4), risers=18))
    upper = stair(flight((0, 0), (0, 4), risers=18), direction=StairDirection.DOWN, stair_id="d")

    below, above = building_stairs([Storey([lower], [], 3.15), Storey([upper], [], 3.0)])

    assert len(below.stairs[0].steps) == 18
    assert len(above.wells) == 1
    assert above.stairs[0].id == "d" and above.stairs[0].steps == []
    assert len(above.stairs[0].railings) == 1


def test_down_stair_on_its_own_is_a_well():
    (level,) = building_stairs(
        [Storey([stair(flight((0, 0), (0, 4)), direction=StairDirection.DOWN)], [], 3.0)]
    )

    assert level.stairs[0].steps == []
    assert level.wells[0].area == pytest.approx(4.0, rel=0.02)


def test_building_cuts_the_well_out_of_the_upper_floor():
    ground = plan([rect("r1", 0, 0, 6, 6)])
    ground.stairs.append(stair(flight((1, 5), (1, 1), risers=18)))
    first = plan([rect("r2", 0, 0, 6, 6)]).model_copy(update={"name": "First floor"})
    spec = BuildingSpec(
        kind=BuildingKind.BUILDING,
        levels=[
            LevelSpec(index=0, elevation=0, floor=ground),
            LevelSpec(index=1, elevation=3.15, floor=first),
        ],
    )

    geometry, _ = build_building(spec)

    upper = geometry.levels[1]
    assert geometry.levels[0].stairs[0].steps[-1].top == pytest.approx(3.15)
    assert len(upper.rooms[0].holes) == 1
    assert len(upper.slabs) == 1 and len(upper.slabs[0].holes) == 1
    assert geometry.levels[0].slabs == []
