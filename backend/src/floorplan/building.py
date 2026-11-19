"""Reads a whole building: from one sheet holding every floor plan, or from a photo per floor.

A sheet is read once to find its drawings; each floor plan is then cut out and read on its own,
the floors in parallel. The floors are stacked lowest first, each one shifted to sit over the
floor below it (see `geometry.align`).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

from PIL import Image

from floorplan.errors import PlanRejectedError
from floorplan.geometry.align import align
from floorplan.imaging import prepare
from floorplan.models import BuildingKind, BuildingSpec, FloorSpec, LevelSpec, PlanResponse, Point
from floorplan.service import PlanService, assemble
from floorplan.sheet import floor_drawings, is_roof, level_from_title

DEFAULT_SLAB = 0.15
READING_SHEET = "Reading sheet"
STACKING = "Stacking floors"
FLOOR_WORKERS = 4


class Progress(Protocol):
    def plan(self, stages: list[str]) -> None: ...

    def start(self, stage: str) -> None: ...

    def finish(self, stage: str) -> None: ...


class BuildingReader:
    def __init__(self, service: PlanService, max_side: int):
        self._service = service
        self._max_side = max_side

    def from_sheet(self, sheet: Image.Image, progress: Progress) -> PlanResponse:
        progress.plan([READING_SHEET])
        progress.start(READING_SHEET)
        seen = prepare(sheet, self._max_side)
        reading = self._service.model.read_sheet(seen)
        drawings = floor_drawings(sheet, reading, (seen.width, seen.height))
        if not drawings:
            raise PlanRejectedError(["No floor plans were found on the sheet."])
        progress.finish(READING_SHEET)

        names = [level_name(d.title, i) for i, d in enumerate(drawings)]
        floors = self._read_floors([d.image for d in drawings], names, progress)
        floors = [
            (f.model_copy(update={"name": name}), w)
            for (f, w), name in zip(floors, names, strict=True)
        ]
        roofs = [is_roof(d.title) for d in drawings]
        return self._stack(floors, roofs, reading.floor_to_floor, reading.slab, progress)

    def from_photos(self, photos: list[Image.Image], progress: Progress) -> PlanResponse:
        names = [f"Photo {i + 1}" for i in range(len(photos))]
        floors = self._read_floors(photos, names, progress)
        order = sorted(
            range(len(floors)),
            key=lambda i: (_named_level(floors[i][0].name, i), i),
        )
        stacked = [floors[i] for i in order]
        roofs = [is_roof(floor.name) for floor, _ in stacked]
        return self._stack(stacked, roofs, None, None, progress)

    def _read_floors(
        self, images: list[Image.Image], names: list[str], progress: Progress
    ) -> list[tuple[FloorSpec, list[str]]]:
        progress.plan([*names, STACKING])

        def read(index: int) -> tuple[FloorSpec, list[str]]:
            progress.start(names[index])
            hint = f"It is one floor of a building: {names[index]}."
            result = self._service.read_floor(prepare(images[index], self._max_side), hint)
            progress.finish(names[index])
            return result

        with ThreadPoolExecutor(max_workers=FLOOR_WORKERS) as pool:
            return list(pool.map(read, range(len(images))))

    def _stack(
        self,
        floors: list[tuple[FloorSpec, list[str]]],
        roofs: list[bool],
        floor_to_floor: float | None,
        slab: float | None,
        progress: Progress,
    ) -> PlanResponse:
        progress.start(STACKING)
        response = stack(floors, roofs, floor_to_floor, slab)
        progress.finish(STACKING)
        return response


def stack(
    floors: list[tuple[FloorSpec, list[str]]],
    roofs: list[bool],
    floor_to_floor: float | None = None,
    slab: float | None = None,
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
            fit = align(levels[-1].floor, floor)
            offset = Point(x=round(offset.x + fit.offset.x, 3), y=round(offset.y + fit.offset.y, 3))
            if not fit.confident:
                warnings.append(
                    f"{floor.name}: only {fit.score:.0%} of its outer walls line up with the floor "
                    "below, so it is centred over it instead."
                )
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


def level_name(title: str, index: int) -> str:
    """A tidy level name from a drawing title: 'FIRST FLOOR PLAN' becomes 'First floor'."""
    words = [w for w in title.replace("-", " ").split() if w.lower() not in ("plan", "layout")]
    name = " ".join(words).strip(" :.").capitalize()
    return name or f"Level {index}"


def _named_level(name: str, fallback: int) -> int:
    level = level_from_title(name)
    return fallback if level is None else level
