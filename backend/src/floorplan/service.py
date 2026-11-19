from collections.abc import Callable
from typing import Protocol

from floorplan.errors import LevelNotFoundError, PlanRejectedError
from floorplan.geometry import ValidationReport, build_building, normalize, validate
from floorplan.llm.client import Feedback
from floorplan.models import BuildingKind, BuildingSpec, FloorSpec, LevelSpec, PlanResponse


class PlanModel(Protocol):
    def extract(self, image_url: str, feedback: Feedback | None = None) -> FloorSpec: ...

    def edit(
        self, floor: FloorSpec, instruction: str, feedback: Feedback | None = None
    ) -> FloorSpec: ...


class PlanService:
    def __init__(self, model: PlanModel):
        self._model = model

    def parse(self, image_url: str) -> PlanResponse:
        floor, report = self._resolve(lambda feedback: self._model.extract(image_url, feedback))
        return _assemble(single_floor(floor), report.warnings)

    def edit(self, spec: BuildingSpec, instruction: str, level: int = 0) -> PlanResponse:
        target = _level(spec, level)
        floor, report = self._resolve(
            lambda feedback: self._model.edit(target.floor, instruction, feedback)
        )
        levels = [
            lv.model_copy(update={"floor": floor}) if lv is target else lv for lv in spec.levels
        ]
        return _assemble(spec.model_copy(update={"levels": levels}), report.warnings)

    def _resolve(
        self, request: Callable[[Feedback | None], FloorSpec]
    ) -> tuple[FloorSpec, ValidationReport]:
        floor, report = _prepare(request(None))
        if report.errors:
            floor, report = _prepare(request(Feedback(floor, report.errors)))
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
    return _assemble(spec.model_copy(update={"levels": levels}), warnings)


def _level(spec: BuildingSpec, index: int) -> LevelSpec:
    match = next((level for level in spec.levels if level.index == index), None)
    if match is None:
        raise LevelNotFoundError(index)
    return match


def _prepare(floor: FloorSpec) -> tuple[FloorSpec, ValidationReport]:
    cleaned = normalize(floor)
    return cleaned, validate(cleaned)


def _assemble(spec: BuildingSpec, warnings: list[str]) -> PlanResponse:
    geometry, build_warnings = build_building(spec)
    return PlanResponse(spec=spec, geometry=geometry, warnings=warnings + build_warnings)
