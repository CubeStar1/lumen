"""What the model reads off a drawing, in pixels of the image it was shown, and its conversion to
a metric FloorSpec.

The model points at walls, openings and printed dimensions; the scale is then computed here from
the dimension texts rather than estimated by the model. Without dimension lines, printed room
sizes (14'0"X10'0") are compared with the rooms the walls enclose; failing that the model's own
estimate is used, and door widths (assumed 0.9 m) only as a last resort.
"""

import math
import re
from statistics import median

from pydantic import BaseModel, Field
from shapely.geometry import Point as ShapelyPoint

from floorplan.geometry.regions import faces
from floorplan.geometry.scale import Dimension, bare_unit, estimate_scale, parse_length
from floorplan.geometry.vec import length, sub, vec
from floorplan.models import (
    ColumnSpec,
    FlightSpec,
    FloorSpec,
    LandingSpec,
    OpeningSpec,
    OpeningType,
    Point,
    RoomSpec,
    RoomType,
    StairDirection,
    StairSpec,
    WallKind,
    WallSpec,
)

DOOR_WIDTH = 0.9
WALL_ALLOWANCE = 0.15
UNENCLOSING = (WallKind.LOW, WallKind.PARAPET)


class PixelWall(BaseModel):
    id: str
    start: Point
    end: Point
    kind: WallKind
    thickness: float | None = Field(description="Drawn thickness in pixels, or null if unclear.")


class PixelOpening(BaseModel):
    id: str
    type: OpeningType
    wall: str = Field(description="Id of the wall the opening is in.")
    position: Point = Field(description="Centre of the opening, on its wall.")
    width: float = Field(description="Clear width in pixels.")


class PixelRoom(BaseModel):
    id: str
    name: str = Field(description="Label as printed, or the room's use if unlabelled.")
    type: RoomType
    outdoor: bool = Field(description="True for porches, sit-outs, terraces and open balconies.")
    label: Point = Field(description="A point well inside the room.")
    size: str | None = Field(description="The room's printed size, e.g. 14'0\"X10'0\", else null.")
    polygon: list[Point] | None = Field(
        description="Outline for outdoor areas and open-plan rooms; null for walled-in rooms."
    )


class PixelFlight(BaseModel):
    start: Point = Field(description="Centre of the bottom step's front edge.")
    end: Point = Field(description="Centre of the top step's back edge.")
    width: float = Field(description="Flight width in pixels.")
    risers: int
    via: Point | None = Field(
        description="A point on the centre line of a curved flight, else null."
    )


class PixelStair(BaseModel):
    id: str
    direction: StairDirection = Field(
        description="up if it climbs from this floor, down if it arrives from the floor below."
    )
    flights: list[PixelFlight] = Field(description="In climbing order, the lowest flight first.")
    landings: list[list[Point]] = Field(description="Landing outlines between the flights.")


class PixelColumn(BaseModel):
    position: Point
    size: float = Field(description="Width in pixels.")


class PixelDimension(BaseModel):
    text: str = Field(description="The dimension exactly as printed, e.g. 15'-3\" or 350.")
    start: Point = Field(description="Where the dimension line starts (its tick or arrow).")
    end: Point = Field(description="Where the dimension line ends.")


class FloorExtraction(BaseModel):
    name: str = Field(description="Level name, e.g. 'Ground floor'.")
    height: float = Field(description="Floor-to-ceiling height in metres, usually 3.0.")
    metres_per_pixel: float = Field(description="Your own estimate of the drawing's scale.")
    walls: list[PixelWall]
    openings: list[PixelOpening]
    rooms: list[PixelRoom]
    stairs: list[PixelStair]
    columns: list[PixelColumn]
    dimensions: list[PixelDimension]
    notes: str = Field(description="Anything uncertain about the drawing.")


Scale = tuple[float, str]


def to_floor(extraction: FloorExtraction, given: Scale | None = None) -> FloorSpec:
    """The extraction in metres, at `given` metres per pixel or else its own drawing scale."""
    scale, note = given or drawing_scale(extraction)

    def p(point: Point) -> Point:
        return Point(x=round(point.x * scale, 4), y=round(point.y * scale, 4))

    def metres(value: float) -> float:
        return round(value * scale, 4)

    return FloorSpec(
        name=extraction.name,
        height=extraction.height,
        derive_walls=False,
        rooms=[
            RoomSpec(
                id=r.id,
                name=r.name,
                type=r.type,
                outdoor=r.outdoor,
                label=p(r.label),
                polygon=[p(q) for q in r.polygon or []],
            )
            for r in extraction.rooms
        ],
        walls=[
            WallSpec(
                id=w.id,
                start=p(w.start),
                end=p(w.end),
                kind=w.kind,
                thickness=metres(w.thickness) if w.thickness else None,
            )
            for w in extraction.walls
        ],
        openings=[
            OpeningSpec(
                id=o.id,
                type=o.type,
                wall=o.wall,
                rooms=[],
                position=p(o.position),
                width=metres(o.width),
            )
            for o in extraction.openings
        ],
        stairs=[
            StairSpec(
                id=s.id,
                direction=s.direction,
                flights=[
                    FlightSpec(
                        start=p(f.start),
                        end=p(f.end),
                        width=metres(f.width),
                        risers=f.risers,
                        via=p(f.via) if f.via else None,
                    )
                    for f in s.flights
                ],
                landings=[LandingSpec(polygon=[p(q) for q in landing]) for landing in s.landings],
            )
            for s in extraction.stairs
        ],
        columns=[
            ColumnSpec(position=p(c.position), size=metres(c.size)) for c in extraction.columns
        ],
        notes=f"{extraction.notes} {note}".strip(),
    )


def drawing_scale(extraction: FloorExtraction) -> Scale:
    """Metres per pixel and a note saying how it was found."""
    found = scale_from_sizes(size_samples(extraction))
    if found is not None:
        return found

    if extraction.metres_per_pixel > 0:
        return extraction.metres_per_pixel, "Scale estimated by the model; no sizes were readable."
    doors = [o.width for o in extraction.openings if o.type == OpeningType.DOOR and o.width > 0]
    scale = DOOR_WIDTH / median(doors) if doors else 0.01
    return scale, f"Scale from door widths (assumed {DOOR_WIDTH} m)."


SIZE_SOURCES = ("printed dimension", "printed room size")


def size_samples(extraction: FloorExtraction) -> tuple[list[Dimension], list[Dimension]]:
    """The drawing's dimension lines and its printed room sizes, measured in its pixels."""
    lines = [
        Dimension(d.text, length(sub(vec(d.end), vec(d.start)))) for d in extraction.dimensions
    ]
    return lines, room_size_dimensions(extraction)


def scale_from_sizes(
    samples: tuple[list[Dimension], list[Dimension]], what: str = ""
) -> Scale | None:
    """Metres per pixel from dimension lines, or failing those from room sizes."""
    for source, found in zip(SIZE_SOURCES, samples, strict=True):
        estimate = estimate_scale(found)
        if estimate is not None:
            note = f"Scale from {estimate.used} {source}(s){what}"
            if estimate.outliers:
                note += f"; ignored {', '.join(estimate.outliers)} as inconsistent"
            return estimate.metres_per_unit, note + "."
    return None


def room_size_dimensions(extraction: FloorExtraction) -> list[Dimension]:
    """Printed room sizes paired with the sides of the room the walls enclose, in pixels. Sizes
    are measured inside the walls, so half a wall is added on each side to match centre lines."""
    sized = [r for r in extraction.rooms if r.size and not r.outdoor]
    if not sized:
        return []
    segments = [(vec(w.start), vec(w.end)) for w in extraction.walls if w.kind not in UNENCLOSING]
    found = faces(segments)
    unit = bare_unit([part for r in sized for part in _size_parts(r.size or "")])
    dimensions: list[Dimension] = []
    for room in sized:
        face = next((f for f in found if f.covers(ShapelyPoint(vec(room.label)))), None)
        lengths = [parse_length(part, unit) for part in _size_parts(room.size or "")]
        if face is None or len(lengths) != 2 or None in lengths:
            continue
        for metres, pixels in zip(sorted(lengths), _rectangle_sides(face), strict=True):
            dimensions.append(Dimension(f"{metres + WALL_ALLOWANCE:.4f} m", pixels))
    return dimensions


def _size_parts(size: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*[xX×*]\s*", size) if part.strip()]


def _rectangle_sides(face) -> list[float]:
    corners = list(face.minimum_rotated_rectangle.exterior.coords)[:3]
    return sorted([math.dist(corners[0], corners[1]), math.dist(corners[1], corners[2])])
