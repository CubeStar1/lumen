from floorplan.extraction import (
    FloorExtraction,
    PixelDimension,
    PixelOpening,
    PixelRoom,
    PixelWall,
)
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
        label=None,
        polygon=[Point(x=x, y=y) for x, y in corners],
    )


def opening(
    opening_id: str, kind: OpeningType, rooms: list[str], x: float, y: float, width: float = 0.9
) -> OpeningSpec:
    return OpeningSpec(
        id=opening_id, type=kind, wall=None, rooms=rooms, position=Point(x=x, y=y), width=width
    )


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
        derive_walls=True,
        rooms=rooms,
        walls=walls or [],
        openings=openings or [],
        stairs=[],
        columns=[],
        notes="",
    )


def px(x: float, y: float) -> Point:
    return Point(x=x, y=y)


def drawing(
    walls: list[PixelWall] | None = None,
    rooms: list[PixelRoom] | None = None,
    openings: list[PixelOpening] | None = None,
    dimensions: list[PixelDimension] | None = None,
) -> FloorExtraction:
    return FloorExtraction(
        name="Ground floor",
        height=3.0,
        metres_per_pixel=0.02,
        walls=walls or [],
        openings=openings or [],
        rooms=rooms or [],
        stairs=[],
        columns=[],
        dimensions=dimensions or [],
        notes="",
    )


def pixel_wall(wall_id: str, a, b, kind: WallKind = WallKind.INTERIOR) -> PixelWall:
    return PixelWall(id=wall_id, start=px(*a), end=px(*b), kind=kind, thickness=None)


def pixel_room(
    room_id: str, x: float, y: float, polygon=None, outdoor: bool = False, size: str | None = None
) -> PixelRoom:
    return PixelRoom(
        id=room_id,
        name=room_id.upper(),
        type=RoomType.PORCH if outdoor else RoomType.OTHER,
        outdoor=outdoor,
        label=px(x, y),
        size=size,
        polygon=[px(*p) for p in polygon] if polygon else None,
    )


def two_room_drawing() -> FloorExtraction:
    """A 7 x 3 m house drawn at 100 px per metre, split by a wall at x = 4 m with a door in it."""
    outer = [((0, 0), (700, 0)), ((700, 0), (700, 300)), ((700, 300), (0, 300)), ((0, 300), (0, 0))]
    walls = [pixel_wall(f"w{i + 1}", a, b, WallKind.EXTERIOR) for i, (a, b) in enumerate(outer)]
    walls.append(pixel_wall("w5", (400, 0), (400, 300)))
    return drawing(
        walls=walls,
        rooms=[pixel_room("r1", 200, 150), pixel_room("r2", 550, 150)],
        openings=[
            PixelOpening(
                id="o1", type=OpeningType.DOOR, wall="w5", position=px(400, 150), width=90
            ),
            PixelOpening(
                id="o2", type=OpeningType.WINDOW, wall="w1", position=px(200, 0), width=120
            ),
        ],
        dimensions=[PixelDimension(text="7.0 m", start=px(0, -40), end=px(700, -40))],
    )
