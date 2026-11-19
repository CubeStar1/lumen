from shapely.geometry import Polygon

from floorplan.geometry.frame import bounds_of, to_world_frame
from floorplan.geometry.openings import attach_openings
from floorplan.geometry.vec import point
from floorplan.geometry.walls import derive_walls
from floorplan.models import PlanGeometry, PlanSpec, Room, RoomSpec, Wall

EXTERIOR_THICKNESS = 0.2
INTERIOR_THICKNESS = 0.12


def build_geometry(spec: PlanSpec) -> tuple[PlanGeometry, list[str]]:
    world = to_world_frame(spec)
    walls: list[Wall] = []
    wall_rooms: dict[str, frozenset[str]] = {}

    for index, segment in enumerate(derive_walls(world.rooms), start=1):
        wall = Wall(
            id=f"w{index}",
            start=point(segment.start),
            end=point(segment.end),
            thickness=EXTERIOR_THICKNESS if segment.exterior else INTERIOR_THICKNESS,
            height=spec.wall_height,
            exterior=segment.exterior,
        )
        walls.append(wall)
        wall_rooms[wall.id] = segment.rooms

    warnings = attach_openings(walls, wall_rooms, world.openings)
    geometry = PlanGeometry(
        bounds=bounds_of(world),
        rooms=[_room(r) for r in world.rooms],
        walls=walls,
    )
    return geometry, warnings


def _room(spec: RoomSpec) -> Room:
    shape = Polygon([(p.x, p.y) for p in spec.polygon])
    label = shape.centroid if shape.contains(shape.centroid) else shape.representative_point()
    return Room(
        id=spec.id,
        name=spec.name,
        type=spec.type,
        polygon=spec.polygon,
        centroid=point((label.x, label.y)),
        area=round(shape.area, 2),
    )
