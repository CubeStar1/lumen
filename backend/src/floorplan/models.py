from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

EXTERIOR = "exterior"


class RoomType(StrEnum):
    LIVING = "living"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    TOILET = "toilet"
    DINING = "dining"
    HALLWAY = "hallway"
    STAIRCASE = "staircase"
    BALCONY = "balcony"
    PORCH = "porch"
    TERRACE = "terrace"
    UTILITY = "utility"
    STORE = "store"
    GARAGE = "garage"
    OTHER = "other"


class OpeningType(StrEnum):
    DOOR = "door"
    SLIDING_DOOR = "sliding_door"
    WINDOW = "window"
    OPENING = "opening"


class WallKind(StrEnum):
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    PARTITION = "partition"
    LOW = "low"
    PARAPET = "parapet"


class StairDirection(StrEnum):
    UP = "up"
    DOWN = "down"


class BuildingKind(StrEnum):
    FLOOR = "floor"
    BUILDING = "building"


class Point(BaseModel):
    x: float
    y: float


class RoomSpec(BaseModel):
    id: str
    name: str = Field(description="Label as printed on the plan, e.g. 'Bedroom 2'.")
    type: RoomType
    outdoor: bool = Field(description="True for porches, sit-outs, terraces and open balconies.")
    label: Point | None = Field(description="A point inside the room, or null.")
    polygon: list[Point] = Field(description="Room outline in metres, vertices in order.")


class WallSpec(BaseModel):
    id: str
    start: Point
    end: Point
    kind: WallKind
    thickness: float | None = Field(description="Drawn thickness in metres, or null if unclear.")


class OpeningSpec(BaseModel):
    id: str
    type: OpeningType
    wall: str | None = Field(description="Id of the wall the opening is in, or null.")
    rooms: list[str] = Field(
        description=f"The two room ids this opening connects; use '{EXTERIOR}' for the outside."
    )
    position: Point = Field(description="Centre of the opening, on the shared room edge.")
    width: float = Field(description="Clear width in metres.")


class FlightSpec(BaseModel):
    start: Point = Field(description="Centre of the bottom step's front edge.")
    end: Point = Field(description="Centre of the top step's back edge.")
    width: float
    risers: int
    via: Point | None = Field(
        description="A point on the centre line of a curved flight, else null."
    )


class LandingSpec(BaseModel):
    polygon: list[Point]


class StairSpec(BaseModel):
    id: str
    direction: StairDirection = Field(description="Whether the stair is drawn going up or down.")
    flights: list[FlightSpec]
    landings: list[LandingSpec]


class ColumnSpec(BaseModel):
    position: Point
    size: float


class FloorSpec(BaseModel):
    name: str = Field(description="Level name, e.g. 'Ground floor'.")
    height: float = Field(description="Floor-to-ceiling height in metres, usually 3.0.")
    derive_walls: bool = Field(
        description=(
            "Keep as given. True: walls follow the room outlines and `walls` lists only stubs and "
            "low walls. False: `walls` lists every wall and rooms are found from them."
        )
    )
    rooms: list[RoomSpec]
    walls: list[WallSpec]
    openings: list[OpeningSpec]
    stairs: list[StairSpec]
    columns: list[ColumnSpec]
    notes: str = Field(description="How the scale was determined and anything uncertain.")


class LevelSpec(BaseModel):
    index: int
    elevation: float
    slab: float = 0.15
    offset: Point = Point(x=0, y=0)
    roof: bool = False
    floor: FloorSpec


class BuildingSpec(BaseModel):
    kind: BuildingKind
    levels: list[LevelSpec]
    notes: str = ""


class Bounds(BaseModel):
    min: Point
    max: Point


class Point3(BaseModel):
    x: float
    y: float
    z: float


class Room(BaseModel):
    id: str
    name: str
    type: RoomType
    outdoor: bool
    polygon: list[Point]
    holes: list[list[Point]] = []
    centroid: Point
    area: float


class Opening(BaseModel):
    id: str
    type: OpeningType
    offset: float
    width: float
    sill: float
    head: float


class Wall(BaseModel):
    id: str
    start: Point
    end: Point
    kind: WallKind
    thickness: float
    height: float
    exterior: bool
    openings: list[Opening] = []


class Step(BaseModel):
    corners: list[Point]
    bottom: float
    top: float


class Landing(BaseModel):
    polygon: list[Point]
    height: float


class Stair(BaseModel):
    """A staircase, heights relative to its level's floor. A stair that arrives from the level
    below has no steps: only the railing around its well."""

    id: str
    direction: StairDirection
    riser: float
    steps: list[Step]
    landings: list[Landing]
    railings: list[list[Point3]]
    footprint: list[Point]


class Column(BaseModel):
    position: Point
    size: float
    height: float


class Slab(BaseModel):
    outline: list[Point]
    holes: list[list[Point]]
    thickness: float


class LevelGeometry(BaseModel):
    index: int
    name: str
    elevation: float
    height: float
    rooms: list[Room]
    walls: list[Wall]
    stairs: list[Stair] = []
    columns: list[Column] = []
    slabs: list[Slab] = []


class BuildingGeometry(BaseModel):
    bounds: Bounds
    levels: list[LevelGeometry]

    @property
    def rooms(self) -> list[Room]:
        return [room for level in self.levels for room in level.rooms]


class PlanResponse(BaseModel):
    spec: BuildingSpec
    geometry: BuildingGeometry
    warnings: list[str]


class EditRequest(BaseModel):
    spec: BuildingSpec
    instruction: str = Field(min_length=1, max_length=500)
    level: int = 0


class InstructionRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=500)
    level: int = 0


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PlanSummary(BaseModel):
    id: str
    name: str
    kind: BuildingKind = BuildingKind.FLOOR
    level_count: int = 1
    created_at: datetime
    updated_at: datetime
    has_image: bool
    room_count: int
    area: float
    width: float
    depth: float


class PlanRecord(PlanSummary):
    plan: PlanResponse
