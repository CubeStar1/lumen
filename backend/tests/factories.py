from floorplan.models import OpeningSpec, OpeningType, PlanSpec, Point, RoomSpec, RoomType


def rect(room_id: str, x0: float, y0: float, x1: float, y1: float) -> RoomSpec:
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return RoomSpec(
        id=room_id,
        name=room_id.upper(),
        type=RoomType.OTHER,
        polygon=[Point(x=x, y=y) for x, y in corners],
    )


def opening(
    opening_id: str, kind: OpeningType, rooms: list[str], x: float, y: float, width: float = 0.9
) -> OpeningSpec:
    return OpeningSpec(id=opening_id, type=kind, rooms=rooms, position=Point(x=x, y=y), width=width)


def plan(rooms: list[RoomSpec], openings: list[OpeningSpec] | None = None) -> PlanSpec:
    return PlanSpec(wall_height=3.0, rooms=rooms, openings=openings or [], notes="")
