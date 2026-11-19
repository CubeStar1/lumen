from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

EXTERIOR = "exterior"


class RoomType(StrEnum):
    LIVING = "living"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    DINING = "dining"
    HALLWAY = "hallway"
    BALCONY = "balcony"
    UTILITY = "utility"
    OTHER = "other"


class OpeningType(StrEnum):
    DOOR = "door"
    WINDOW = "window"


class Point(BaseModel):
    x: float
    y: float


class RoomSpec(BaseModel):
    id: str
    name: str = Field(description="Label as printed on the plan, e.g. 'Bedroom 2'.")
    type: RoomType
    polygon: list[Point] = Field(description="Room outline in metres, vertices in order.")


class OpeningSpec(BaseModel):
    id: str
    type: OpeningType
    rooms: list[str] = Field(
        description=f"The two room ids this opening connects; use '{EXTERIOR}' for the outside."
    )
    position: Point = Field(description="Centre of the opening, on the shared room edge.")
    width: float = Field(description="Clear width in metres.")


class PlanSpec(BaseModel):
    wall_height: float = Field(description="Floor-to-ceiling height in metres, usually 3.0.")
    rooms: list[RoomSpec]
    openings: list[OpeningSpec]
    notes: str = Field(description="How the scale was determined and anything uncertain.")


class Bounds(BaseModel):
    min: Point
    max: Point


class Room(BaseModel):
    id: str
    name: str
    type: RoomType
    polygon: list[Point]
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
    thickness: float
    height: float
    exterior: bool
    openings: list[Opening] = []


class PlanGeometry(BaseModel):
    bounds: Bounds
    rooms: list[Room]
    walls: list[Wall]


class PlanResponse(BaseModel):
    spec: PlanSpec
    geometry: PlanGeometry
    warnings: list[str]


class EditRequest(BaseModel):
    spec: PlanSpec
    instruction: str = Field(min_length=1, max_length=500)


class InstructionRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=500)


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PlanSummary(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    has_image: bool
    room_count: int
    area: float
    width: float
    depth: float


class PlanRecord(PlanSummary):
    plan: PlanResponse
