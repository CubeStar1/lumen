"""A drawing sheet with several drawings on it: what the model reads from it, and the crops.

The model looks at a downsized copy of the sheet and lists each drawing with its box (in that
copy's pixels) and how far it is turned. The floor plans are then cut from the full-resolution
upload, turned upright and padded, so each floor is read at the best resolution available.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from PIL import Image
from pydantic import BaseModel, Field

PADDING = 0.03
QUARTER_TURNS = (0, 90, 180, 270)


class DrawingKind(StrEnum):
    FLOOR_PLAN = "floor_plan"
    SECTION = "section"
    ELEVATION = "elevation"
    SITE = "site"
    SCHEDULE = "schedule"
    TITLE = "title"
    OTHER = "other"


class Box(BaseModel):
    left: float
    top: float
    right: float
    bottom: float


class SheetDrawing(BaseModel):
    kind: DrawingKind
    title: str = Field(description="The drawing's title as printed, e.g. 'FIRST FLOOR PLAN'.")
    level: int | None = Field(
        description="For floor plans: 0 for the ground floor, 1 for the first, and so on; "
        "-1 for a basement. Null for other drawings."
    )
    box: Box = Field(description="The drawing's extent in pixels, including its dimensions.")
    rotation: int = Field(
        description="Degrees clockwise (0, 90, 180 or 270) to turn the drawing so its text reads "
        "upright."
    )


class SheetReading(BaseModel):
    drawings: list[SheetDrawing]
    floor_to_floor: float | None = Field(
        description="Floor-to-floor height in metres if a section or note gives it, else null."
    )
    slab: float | None = Field(description="Floor slab thickness in metres if given, else null.")
    notes: str


@dataclass(frozen=True)
class FloorDrawing:
    level: int
    title: str
    image: Image.Image


def floor_drawings(
    sheet: Image.Image, reading: SheetReading, seen: tuple[int, int]
) -> list[FloorDrawing]:
    """The sheet's floor plans, lowest first, cut from `sheet` using boxes the model gave for a
    copy of it `seen` pixels in size."""
    plans = [d for d in reading.drawings if d.kind == DrawingKind.FLOOR_PLAN]
    ordered = sorted(enumerate(plans), key=lambda item: (_level(item[1], item[0]), item[0]))
    return [
        FloorDrawing(level=i, title=d.title, image=crop(sheet, d.box, seen, d.rotation))
        for i, (_, d) in enumerate(ordered)
    ]


def crop(sheet: Image.Image, box: Box, seen: tuple[int, int], rotation: int) -> Image.Image:
    sx, sy = sheet.width / seen[0], sheet.height / seen[1]
    pad_x = (box.right - box.left) * PADDING
    pad_y = (box.bottom - box.top) * PADDING
    area = (
        max(0, round((min(box.left, box.right) - pad_x) * sx)),
        max(0, round((min(box.top, box.bottom) - pad_y) * sy)),
        min(sheet.width, round((max(box.left, box.right) + pad_x) * sx)),
        min(sheet.height, round((max(box.top, box.bottom) + pad_y) * sy)),
    )
    if area[2] - area[0] < 16 or area[3] - area[1] < 16:
        area = (0, 0, sheet.width, sheet.height)
    turned = sheet.crop(area)
    degrees = quarter_turn(rotation)
    return turned.rotate(-degrees, expand=True) if degrees else turned


def quarter_turn(rotation: int) -> int:
    return min(
        QUARTER_TURNS, key=lambda q: min(abs(rotation % 360 - q), 360 - abs(rotation % 360 - q))
    )


ORDINALS = {
    "basement": -1,
    "cellar": -1,
    "ground": 0,
    "stilt": 0,
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}
ROOF_WORDS = ("terrace", "roof")


def level_from_title(title: str) -> int | None:
    """The level a drawing's title names (GROUND FLOOR PLAN, 2nd floor, Level 3), if any."""
    text = title.lower()
    if any(word in text for word in ROOF_WORDS):
        return 99
    for word, level in ORDINALS.items():
        if word in text:
            return level
    if re.search(r"\bg\.?\s*f\b", text):
        return 0
    match = re.search(
        r"(\d+)\s*(?:st|nd|rd|th)?\s*(?:floor|level|storey)|(?:level|floor)\s*(\d+)", text
    )
    if match:
        return int(match.group(1) or match.group(2))
    return None


def is_roof(title: str) -> bool:
    return any(word in title.lower() for word in ROOF_WORDS)


def _level(drawing: SheetDrawing, order: int) -> int:
    named = level_from_title(drawing.title)
    if named is not None:
        return named
    return drawing.level if drawing.level is not None else order
