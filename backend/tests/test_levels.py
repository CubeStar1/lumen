import json

from factories import opening, plan, rect, wall

from floorplan.legacy import upgrade_record, upgrade_spec
from floorplan.models import BuildingKind, OpeningType, WallKind
from floorplan.service import from_spec, single_floor
from floorplan.store import PlanStore

LEGACY_SPEC = {
    "wall_height": 2.8,
    "notes": "old",
    "rooms": [
        {
            "id": "r1",
            "name": "A",
            "type": "living",
            "polygon": [{"x": 0, "y": 0}, {"x": 4, "y": 0}, {"x": 4, "y": 3}, {"x": 0, "y": 3}],
        },
    ],
    "openings": [
        {
            "id": "o1",
            "type": "door",
            "rooms": ["r1", "exterior"],
            "position": {"x": 2, "y": 0},
            "width": 0.9,
        },
    ],
}


def level_of(floor):
    return from_spec(single_floor(floor)).geometry.levels[0]


def test_outdoor_rooms_get_no_walls_and_leave_the_shared_wall_exterior():
    level = level_of(plan([rect("r1", 0, 0, 4, 3), rect("p1", 0, 3, 4, 5, outdoor=True)]))

    assert len(level.walls) == 4
    assert all(w.exterior for w in level.walls)
    assert next(r for r in level.rooms if r.id == "p1").outdoor


def test_extra_walls_keep_their_kind_and_low_walls_are_short():
    stub = wall("x1", (2, 0), (2, 1.5), WallKind.INTERIOR)
    parapet = wall("x2", (0, 3), (0, 5), WallKind.PARAPET)
    level = level_of(plan([rect("r1", 0, 0, 4, 3)], walls=[stub, parapet]))

    by_kind = {w.kind: w for w in level.walls[4:]}
    assert by_kind[WallKind.INTERIOR].height == 3.0
    assert by_kind[WallKind.PARAPET].height == 1.0
    assert by_kind[WallKind.PARAPET].thickness == 0.115


def test_plain_openings_and_sliding_doors_reach_the_floor():
    gap = opening("o1", OpeningType.OPENING, ["r1", "r2"], 4, 1.5, width=1.2)
    slider = opening("o2", OpeningType.SLIDING_DOOR, ["r1", "exterior"], 2, 0, width=1.6)
    level = level_of(plan([rect("r1", 0, 0, 4, 3), rect("r2", 4, 0, 7, 3)], [gap, slider]))

    openings = {o.id: o for w in level.walls for o in w.openings}
    assert openings["o1"].sill == 0.0
    assert openings["o2"].sill == 0.0


def test_legacy_spec_becomes_a_one_level_building():
    spec = upgrade_spec(LEGACY_SPEC)

    assert spec.kind == BuildingKind.FLOOR
    (level,) = spec.levels
    assert level.floor.height == 2.8
    assert level.floor.notes == "old"
    assert not level.floor.rooms[0].outdoor


def test_legacy_record_is_upgraded_when_read(tmp_path):
    record = {
        "id": "0123456789ab",
        "name": "Old plan",
        "created_at": "2026-11-18T10:00:00Z",
        "updated_at": "2026-11-18T10:00:00Z",
        "has_image": False,
        "room_count": 1,
        "area": 12.0,
        "width": 4.0,
        "depth": 3.0,
        "plan": {"spec": LEGACY_SPEC, "geometry": {}, "warnings": []},
    }
    folder = tmp_path / record["id"]
    folder.mkdir()
    (folder / "record.json").write_text(json.dumps(record))

    loaded = PlanStore(tmp_path).get(record["id"])

    assert loaded.kind == BuildingKind.FLOOR
    assert loaded.plan.geometry.levels[0].rooms[0].id == "r1"
    assert (
        upgrade_record(loaded.model_dump(mode="json"))["plan"]
        == loaded.model_dump(mode="json")["plan"]
    )
