from shapely.geometry import Polygon

from floorplan.geometry.frame import Frame, building_frame, to_world
from floorplan.geometry.openings import attach_openings
from floorplan.geometry.regions import wall_sides
from floorplan.geometry.vec import point, vec
from floorplan.geometry.wallgraph import connect
from floorplan.geometry.walls import derive_walls
from floorplan.models import (
    Bounds,
    BuildingGeometry,
    BuildingSpec,
    FloorSpec,
    LevelGeometry,
    LevelSpec,
    Point,
    Room,
    RoomSpec,
    Wall,
    WallKind,
    WallSpec,
)

THICKNESS = {
    WallKind.EXTERIOR: 0.2,
    WallKind.INTERIOR: 0.12,
    WallKind.PARTITION: 0.075,
    WallKind.LOW: 0.115,
    WallKind.PARAPET: 0.115,
}
LOW_WALL_HEIGHT = 1.0
MIN_THICKNESS = 0.05
MAX_THICKNESS = 0.4


def build_building(spec: BuildingSpec) -> tuple[BuildingGeometry, list[str]]:
    frame = building_frame(spec)
    levels: list[LevelGeometry] = []
    warnings: list[str] = []
    for level in spec.levels:
        geometry, level_warnings = build_level(level, frame)
        levels.append(geometry)
        prefix = f"{level.floor.name}: " if len(spec.levels) > 1 else ""
        warnings += [prefix + w for w in level_warnings]
    return BuildingGeometry(bounds=_bounds(levels), levels=levels), warnings


def build_level(level: LevelSpec, frame: Frame) -> tuple[LevelGeometry, list[str]]:
    floor = to_world(level.floor, frame, level.offset)
    walls, wall_rooms = _outline_walls(floor) if floor.derive_walls else _listed_walls(floor)
    warnings = attach_openings(walls, wall_rooms, floor.openings)
    geometry = LevelGeometry(
        index=level.index,
        name=floor.name,
        elevation=level.elevation,
        height=floor.height,
        rooms=[_room(r) for r in floor.rooms],
        walls=walls,
    )
    return geometry, warnings


WallsWithRooms = tuple[list[Wall], dict[str, frozenset[str]]]


def _outline_walls(floor: FloorSpec) -> WallsWithRooms:
    """Walls along the indoor room outlines, plus the floor's extra walls joined onto them."""
    walls: list[Wall] = []
    wall_rooms: dict[str, frozenset[str]] = {}
    for segment in derive_walls([r for r in floor.rooms if not r.outdoor]):
        kind = WallKind.EXTERIOR if segment.exterior else WallKind.INTERIOR
        wall = Wall(
            id=f"w{len(walls) + 1}",
            start=point(segment.start),
            end=point(segment.end),
            kind=kind,
            thickness=THICKNESS[kind],
            height=floor.height,
            exterior=segment.exterior,
        )
        walls.append(wall)
        wall_rooms[wall.id] = segment.rooms

    extras = [_extra_wall(spec, spec.id, floor.height) for spec in floor.walls]
    for wall in connect(walls, extras):
        wall = wall.model_copy(update={"id": f"w{len(walls) + 1}"})
        walls.append(wall)
        wall_rooms[wall.id] = frozenset()
    return walls, wall_rooms


def _listed_walls(floor: FloorSpec) -> WallsWithRooms:
    """Every wall as listed, with exterior or interior decided by the rooms on either side."""
    rooms = {
        r.id: Polygon([(p.x, p.y) for p in r.polygon])
        for r in floor.rooms
        if not r.outdoor and len(r.polygon) >= 3
    }
    segments = [(vec(w.start), vec(w.end)) for w in floor.walls]
    walls: list[Wall] = []
    wall_rooms: dict[str, frozenset[str]] = {}
    for spec, (left, right) in zip(floor.walls, wall_sides(segments, rooms), strict=True):
        kind = spec.kind
        if kind in (WallKind.EXTERIOR, WallKind.INTERIOR):
            kind = WallKind.EXTERIOR if not left or not right else WallKind.INTERIOR
        wall = _extra_wall(spec.model_copy(update={"kind": kind}), spec.id, floor.height)
        walls.append(wall)
        wall_rooms[wall.id] = left | right
    return walls, wall_rooms


def _extra_wall(spec: WallSpec, wall_id: str, floor_height: float) -> Wall:
    thickness = spec.thickness or THICKNESS[spec.kind]
    low = spec.kind in (WallKind.LOW, WallKind.PARAPET)
    return Wall(
        id=wall_id,
        start=spec.start,
        end=spec.end,
        kind=spec.kind,
        thickness=round(min(max(thickness, MIN_THICKNESS), MAX_THICKNESS), 3),
        height=min(LOW_WALL_HEIGHT, floor_height) if low else floor_height,
        exterior=spec.kind in (WallKind.EXTERIOR, WallKind.PARAPET),
    )


def _room(spec: RoomSpec) -> Room:
    shape = Polygon([(p.x, p.y) for p in spec.polygon])
    label = shape.centroid if shape.contains(shape.centroid) else shape.representative_point()
    return Room(
        id=spec.id,
        name=spec.name,
        type=spec.type,
        outdoor=spec.outdoor,
        polygon=spec.polygon,
        centroid=point((label.x, label.y)),
        area=round(shape.area, 2),
    )


def _bounds(levels: list[LevelGeometry]) -> Bounds:
    points = [p for level in levels for room in level.rooms for p in room.polygon]
    xs, ys = [p.x for p in points], [p.y for p in points]
    return Bounds(min=Point(x=min(xs), y=min(ys)), max=Point(x=max(xs), y=max(ys)))
