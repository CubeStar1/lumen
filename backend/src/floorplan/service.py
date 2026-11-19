from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel

from floorplan.errors import LevelNotFoundError, PlanRejectedError
from floorplan.extraction import FloorExtraction, to_floor
from floorplan.geometry import ValidationReport, build_building, normalize, validate
from floorplan.geometry.layout import complete
from floorplan.imaging import PreparedImage
from floorplan.llm.client import Feedback
from floorplan.models import BuildingKind, BuildingSpec, FloorSpec, LevelSpec, PlanResponse
from floorplan.sheet import SheetReading


class PlanModel(Protocol):
    def extract(
        self, image: PreparedImage, feedback: Feedback | None = None, hint: str | None = None
    ) -> FloorExtraction: ...

    def read_sheet(self, image: PreparedImage) -> SheetReading: ...

    def edit(
        self, floor: FloorSpec, instruction: str, feedback: Feedback | None = None
    ) -> FloorSpec: ...


class PlanService:
    def __init__(self, model: PlanModel):
        self._model = model

    @property
    def model(self) -> PlanModel:
        return self._model

    def parse(self, image: PreparedImage) -> PlanResponse:
        floor, warnings = self.read_floor(image)
        return assemble(single_floor(floor), warnings)

    def read_floor(
        self, image: PreparedImage, hint: str | None = None
    ) -> tuple[FloorSpec, list[str]]:
        floor, report = self._resolve(
            lambda feedback: self._model.extract(image, feedback, hint), to_floor
        )
        return floor, report.warnings

    def edit(self, spec: BuildingSpec, instruction: str, level: int = 0) -> PlanResponse:
        target = _level(spec, level)
        floor, report = self._resolve(
            lambda feedback: self._model.edit(target.floor, instruction, feedback),
            lambda floor: floor,
        )
        levels = [
            lv.model_copy(update={"floor": floor}) if lv is target else lv for lv in spec.levels
        ]
        return assemble(spec.model_copy(update={"levels": levels}), report.warnings)

    def _resolve[A: BaseModel](
        self, ask: Callable[[Feedback | None], A], convert: Callable[[A], FloorSpec]
    ) -> tuple[FloorSpec, ValidationReport]:
        """Asks the model, retrying once with the problems found in its first answer."""
        answer = ask(None)
        floor, report = _prepare(convert(answer))
        if report.errors:
            answer = ask(Feedback(answer, report.errors))
            floor, report = _prepare(convert(answer))
        if report.errors:
            raise PlanRejectedError(report.errors)
        return floor, report


def single_floor(floor: FloorSpec) -> BuildingSpec:
    return BuildingSpec(
        kind=BuildingKind.FLOOR, levels=[LevelSpec(index=0, elevation=0.0, floor=floor)]
    )


def from_spec(spec: BuildingSpec) -> PlanResponse:
    levels, warnings = [], []
    for level in spec.levels:
        floor, report = _prepare(level.floor)
        if report.errors:
            raise PlanRejectedError(report.errors)
        levels.append(level.model_copy(update={"floor": floor}))
        warnings += report.warnings
    return assemble(spec.model_copy(update={"levels": levels}), warnings)


def _level(spec: BuildingSpec, index: int) -> LevelSpec:
    match = next((level for level in spec.levels if level.index == index), None)
    if match is None:
        raise LevelNotFoundError(index)
    return match


def _prepare(floor: FloorSpec) -> tuple[FloorSpec, ValidationReport]:
    cleaned, warnings = complete(normalize(floor))
    report = validate(cleaned)
    report.warnings[:0] = warnings
    return cleaned, report


def assemble(spec: BuildingSpec, warnings: list[str]) -> PlanResponse:
    geometry, build_warnings = build_building(spec)
    return PlanResponse(spec=spec, geometry=geometry, warnings=warnings + build_warnings)
