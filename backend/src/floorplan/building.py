"""Reads a whole building: from one sheet holding every floor plan, or from a photo per floor.

A sheet is read once to find its drawings; each floor plan is then cut out and read on its own,
the floors in parallel. What the model answered is kept (`BuildingAnswers`), and the building is
built from those answers, so a saved building can be rebuilt with a newer pipeline for free.

Floors cut from one sheet are drawn at one scale, so their printed sizes are pooled into a single
scale. The floors are then stacked lowest first, each placed over the floor below it (see
`geometry.align`); between photos, which may be taken from different distances, the placement may
also correct the scale.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from PIL import Image
from pydantic import BaseModel

from floorplan.errors import PlanRejectedError
from floorplan.extraction import (
    FloorExtraction,
    Scale,
    drawing_scale,
    scale_from_sizes,
    size_samples,
    to_floor,
)
from floorplan.geometry.align import Alignment, align, place
from floorplan.geometry.scale import Dimension, estimate_scale
from floorplan.imaging import prepare
from floorplan.models import BuildingKind, BuildingSpec, FloorSpec, LevelSpec, PlanResponse, Point
from floorplan.service import FloorRead, PlanService, assemble, prepare_floor
from floorplan.sheet import SheetReading, floor_drawings, is_roof, level_from_title

DEFAULT_SLAB = 0.15
READING_SHEET = "Reading sheet"
STACKING = "Stacking floors"
FLOOR_WORKERS = 4
OWN_SCALE_LINES = 3
OWN_SCALE_GAP = 0.15


class Progress(Protocol):
    def plan(self, stages: list[str]) -> None: ...

    def start(self, stage: str) -> None: ...

    def finish(self, stage: str) -> None: ...


class BuildingSource(StrEnum):
    SHEET = "sheet"
    PHOTOS = "photos"


class FloorAnswer(BaseModel):
    name: str
    roof: bool
    image_scale: float
    """Pixels of the image the model saw per pixel of the upload (or of the sheet)."""
    extraction: FloorExtraction


class BuildingAnswers(BaseModel):
    """Everything the model said about a building, lowest floor first."""

    source: BuildingSource
    sheet: SheetReading | None
    floors: list[FloorAnswer]


@dataclass(frozen=True)
class BuildingRead:
    response: PlanResponse
    answers: BuildingAnswers


class BuildingReader:
    def __init__(self, service: PlanService, max_side: int):
        self._service = service
        self._max_side = max_side

    def from_sheet(self, sheet: Image.Image, progress: Progress) -> BuildingRead:
        progress.plan([READING_SHEET])
        progress.start(READING_SHEET)
        seen = prepare(sheet, self._max_side)
        reading = self._service.model.read_sheet(seen)
        drawings = floor_drawings(sheet, reading, (seen.width, seen.height))
        if not drawings:
            raise PlanRejectedError(["No floor plans were found on the sheet."])
        progress.finish(READING_SHEET)

        names = [level_name(d.title, i) for i, d in enumerate(drawings)]
        reads = self._read_floors([d.image for d in drawings], names, progress)
        floors = [
            FloorAnswer(name=name, roof=is_roof(d.title), image_scale=scale, extraction=r.answer)
            for name, d, (r, scale) in zip(names, drawings, reads, strict=True)
        ]
        answers = BuildingAnswers(source=BuildingSource.SHEET, sheet=reading, floors=floors)
        return self._build(answers, progress)

    def from_photos(self, photos: list[Image.Image], progress: Progress) -> BuildingRead:
        names = [f"Photo {i + 1}" for i in range(len(photos))]
        reads = self._read_floors(photos, names, progress)
        order = sorted(
            range(len(reads)), key=lambda i: (_named_level(reads[i][0].floor.name, i), i)
        )
        floors = [
            FloorAnswer(
                name=reads[i][0].floor.name,
                roof=is_roof(reads[i][0].floor.name),
                image_scale=reads[i][1],
                extraction=reads[i][0].answer,
            )
            for i in order
        ]
        answers = BuildingAnswers(source=BuildingSource.PHOTOS, sheet=None, floors=floors)
        return self._build(answers, progress)

    def _read_floors(
        self, images: list[Image.Image], names: list[str], progress: Progress
    ) -> list[tuple[FloorRead, float]]:
        progress.plan([*names, STACKING])

        def read(index: int) -> tuple[FloorRead, float]:
            progress.start(names[index])
            seen = prepare(images[index], self._max_side)
            hint = f"It is one floor of a building: {names[index]}."
            result = self._service.read_floor(seen, hint)
            progress.finish(names[index])
            return result, seen.width / images[index].width

        with ThreadPoolExecutor(max_workers=FLOOR_WORKERS) as pool:
            return list(pool.map(read, range(len(images))))

    def _build(self, answers: BuildingAnswers, progress: Progress) -> BuildingRead:
        progress.start(STACKING)
        response = rebuild(answers)
        progress.finish(STACKING)
        return BuildingRead(response, answers)


def rebuild(answers: BuildingAnswers) -> PlanResponse:
    """The building from the model's answers, with the current pipeline."""
    shared = shared_scale(answers.floors) if answers.source == BuildingSource.SHEET else None
    floors = [_floor(answer, shared) for answer in answers.floors]
    sheet = answers.sheet
    return stack(
        floors,
        [answer.roof for answer in answers.floors],
        sheet.floor_to_floor if sheet else None,
        sheet.slab if sheet else None,
        fit_scale=answers.source == BuildingSource.PHOTOS,
    )


def shared_scale(floors: list[FloorAnswer]) -> Scale | None:
    """Metres per sheet pixel from the printed sizes on every floor of the sheet."""
    pooled = tuple(
        [
            Dimension(d.text, d.length / floor.image_scale)
            for floor in floors
            for d in size_samples(floor.extraction)[source]
        ]
        for source in (0, 1)
    )
    return scale_from_sizes(pooled, " across every floor on the sheet")


def _floor(answer: FloorAnswer, shared: Scale | None) -> tuple[FloorSpec, list[str]]:
    """One floor in metres, at the sheet's shared scale unless its own dimensions clearly show it
    was drawn at another."""
    given, warnings = None, []
    if shared is not None:
        metres = shared[0] / answer.image_scale
        own = estimate_scale(size_samples(answer.extraction)[0])
        if (
            own
            and own.used >= OWN_SCALE_LINES
            and abs(own.metres_per_unit / metres - 1) > OWN_SCALE_GAP
        ):
            warnings.append("its dimensions show a different scale from the rest of the sheet.")
        else:
            given = (metres, shared[1])

    floor, report = prepare_floor(to_floor(answer.extraction, given))
    if report.errors and given is not None:
        floor, report = prepare_floor(to_floor(answer.extraction, drawing_scale(answer.extraction)))
    if report.errors:
        raise PlanRejectedError(report.errors)
    return floor.model_copy(update={"name": answer.name}), warnings + report.warnings


def stack(
    floors: list[tuple[FloorSpec, list[str]]],
    roofs: list[bool],
    floor_to_floor: float | None = None,
    slab: float | None = None,
    fit_scale: bool = False,
) -> PlanResponse:
    """Puts the floors, lowest first, one above the other."""
    slab = slab or DEFAULT_SLAB
    levels: list[LevelSpec] = []
    warnings: list[str] = []
    elevation, offset = 0.0, Point(x=0, y=0)
    for index, ((floor, floor_warnings), roof) in enumerate(zip(floors, roofs, strict=True)):
        if floor_to_floor and not roof:
            floor = floor.model_copy(update={"height": round(floor_to_floor - slab, 3)})
        if levels:
            fit = align(levels[-1].floor, floor, fit_scale)
            floor = place(floor, fit)
            offset = Point(x=round(offset.x + fit.offset.x, 3), y=round(offset.y + fit.offset.y, 3))
            warnings += _placement_notes(floor.name, fit)
        warnings += [f"{floor.name}: {w}" for w in floor_warnings]
        levels.append(
            LevelSpec(
                index=index,
                elevation=round(elevation, 3),
                slab=slab,
                offset=offset,
                roof=roof,
                floor=floor,
            )
        )
        elevation += floor_to_floor or floor.height + slab
    return assemble(BuildingSpec(kind=BuildingKind.BUILDING, levels=levels), warnings)


def _placement_notes(name: str, fit: Alignment) -> list[str]:
    if not fit.confident:
        return [
            f"{name}: only {fit.score:.0%} of it lines up with the floor below, so it is centred "
            "over it instead."
        ]
    notes = []
    if fit.rotation:
        notes.append(f"{name}: turned {fit.rotation}° to line up with the floor below.")
    if fit.scale != 1.0:
        notes.append(f"{name}: rescaled by {fit.scale:.0%} to match the floor below.")
    return notes


def level_name(title: str, index: int) -> str:
    """A tidy level name from a drawing title: 'FIRST FLOOR PLAN' becomes 'First floor'."""
    words = [w for w in title.replace("-", " ").split() if w.lower() not in ("plan", "layout")]
    name = " ".join(words).strip(" :.").capitalize()
    return name or f"Level {index}"


def _named_level(name: str, fallback: int) -> int:
    level = level_from_title(name)
    return fallback if level is None else level
