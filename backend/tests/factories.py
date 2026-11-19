from floorplan.models import (
    FloorSpec,
    OpeningSpec,
    OpeningType,
    Point,
    RoomSpec,
    RoomType,
    WallKind,
    WallSpec,
)


def rect(
    room_id: str, x0: float, y0: float, x1: float, y1: float, outdoor: bool = False
) -> RoomSpec:
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return RoomSpec(
        id=room_id,
        name=room_id.upper(),
        type=RoomType.PORCH if outdoor else RoomType.OTHER,
        outdoor=outdoor,
        polygon=[Point(x=x, y=y) for x, y in corners],
    )


def opening(
    opening_id: str, kind: OpeningType, rooms: list[str], x: float, y: float, width: float = 0.9
) -> OpeningSpec:
    return OpeningSpec(id=opening_id, type=kind, rooms=rooms, position=Point(x=x, y=y), width=width)


def wall(wall_id: str, a: tuple[float, float], b: tuple[float, float], kind: WallKind) -> WallSpec:
    return WallSpec(
        id=wall_id,
        start=Point(x=a[0], y=a[1]),
        end=Point(x=b[0], y=b[1]),
        kind=kind,
        thickness=None,
    )


def plan(
    rooms: list[RoomSpec],
    openings: list[OpeningSpec] | None = None,
    walls: list[WallSpec] | None = None,
) -> FloorSpec:
    return FloorSpec(
        name="Ground floor",
        height=3.0,
        rooms=rooms,
        walls=walls or [],
        openings=openings or [],
        stairs=[],
        columns=[],
        notes="",
    )
