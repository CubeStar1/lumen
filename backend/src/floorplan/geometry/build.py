from shapely.geometry import Polygon
from shapely.ops import unary_union

from floorplan.geometry.frame import building_frame, counter_clockwise, to_world
from floorplan.geometry.openings import attach_openings
from floorplan.geometry.regions import wall_sides
from floorplan.geometry.stairs import Storey, StoreyStairs, building_stairs
from floorplan.geometry.vec import point, vec
from floorplan.geometry.wallgraph import connect
from floorplan.geometry.walls import derive_walls
from floorplan.models import (
    Bounds,
    BuildingGeometry,
    BuildingSpec,
    Column,
    FloorSpec,
    LevelGeometry,
    LevelSpec,
    Point,
    Room,
    RoomSpec,
    Slab,
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
    floors = [to_world(level.floor, frame, level.offset) for level in spec.levels]
    walled = [_walls(floor, level.roof) for floor, level in zip(floors, spec.levels, strict=True)]
    storeys = [
        Storey(floor.stairs, walls, _rise(spec.levels, i))
        for i, (floor, (walls, _)) in enumerate(zip(floors, walled, strict=True))
    ]
    levels: list[LevelGeometry] = []
    warnings: list[str] = []
    for level, floor, (walls, wall_warnings), stairs in zip(
        spec.levels, floors, walled, building_stairs(storeys), strict=True
    ):
        levels.append(_level(level, floor, walls, stairs))
        prefix = f"{floor.name}: " if len(spec.levels) > 1 else ""
        warnings += [prefix + w for w in wall_warnings + stairs.warnings]
    return BuildingGeometry(bounds=_bounds(levels), levels=levels), warnings


def _walls(floor: FloorSpec, roof: bool) -> tuple[list[Wall], list[str]]:
    walls, wall_rooms = _outline_walls(floor) if floor.derive_walls else _listed_walls(floor, roof)
    return walls, attach_openings(walls, wall_rooms, floor.openings)


def _rise(levels: list[LevelSpec], index: int) -> float:
    """Height a stair on this level climbs: to the next level's floor, or to the ceiling."""
    if index + 1 < len(levels):
        return levels[index + 1].elevation - levels[index].elevation
    return levels[index].floor.height


def _level(
    level: LevelSpec, floor: FloorSpec, walls: list[Wall], stairs: StoreyStairs
) -> LevelGeometry:
    rooms = [_room(r, stairs.wells) for r in floor.rooms]
    return LevelGeometry(
        index=level.index,
        name=floor.name,
        elevation=level.elevation,
        height=floor.height,
        rooms=rooms,
        walls=walls,
        stairs=stairs.stairs,
        columns=[
            Column(position=c.position, size=c.size, height=floor.height) for c in floor.columns
        ],
        slabs=_slabs(floor, stairs.wells, level.slab) if level.elevation > 0 else [],
    )


def _slabs(floor: FloorSpec, wells: list[Polygon], thickness: float) -> list[Slab]:
    """The floor slab under the level's indoor rooms, with its stair wells cut out."""
    indoor = [_shape(r.polygon) for r in floor.rooms if not r.outdoor and len(r.polygon) >= 3]
    shape = unary_union(indoor).buffer(0.01, join_style="mitre").difference(unary_union(wells))
    return [
        Slab(
            outline=_ring(part.exterior.coords),
            holes=[_ring(hole.coords) for hole in part.interiors],
            thickness=thickness,
        )
        for part in _polygons(shape)
    ]


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


def _listed_walls(floor: FloorSpec, roof: bool = False) -> WallsWithRooms:
    """Every wall as listed, with exterior or interior decided by the rooms on either side. On a
    roof level, walls with no indoor room beside them are parapets."""
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
        if roof and not left and not right:
            kind = WallKind.PARAPET
        elif kind in (WallKind.EXTERIOR, WallKind.INTERIOR):
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


def _room(spec: RoomSpec, wells: list[Polygon]) -> Room:
    shape = _shape(spec.polygon)
    label = shape.centroid if shape.contains(shape.centroid) else shape.representative_point()
    polygon, holes = spec.polygon, []
    cut = [w for w in wells if w.intersects(shape)]
    if cut:
        parts = _polygons(shape.difference(unary_union(cut)))
        if parts:
            floor = max(parts, key=lambda p: p.area)
            polygon = counter_clockwise(_ring(floor.exterior.coords))
            holes = [_ring(hole.coords) for hole in floor.interiors]
    return Room(
        id=spec.id,
        name=spec.name,
        type=spec.type,
        outdoor=spec.outdoor,
        polygon=polygon,
        holes=holes,
        centroid=point((label.x, label.y)),
        area=round(shape.area, 2),
    )


def _shape(polygon: list[Point]) -> Polygon:
    return Polygon([(p.x, p.y) for p in polygon])


def _polygons(shape) -> list[Polygon]:
    parts = getattr(shape, "geoms", [shape])
    return [p for p in parts if isinstance(p, Polygon) and p.area > 1e-4]


def _ring(coords) -> list[Point]:
    return [point(c) for c in list(coords)[:-1]]


def _bounds(levels: list[LevelGeometry]) -> Bounds:
    points = [p for level in levels for room in level.rooms for p in room.polygon]
    xs, ys = [p.x for p in points], [p.y for p in points]
    return Bounds(min=Point(x=min(xs), y=min(ys)), max=Point(x=max(xs), y=max(ys)))
