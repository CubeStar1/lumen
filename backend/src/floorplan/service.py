from collections.abc import Callable
from typing import Protocol

from floorplan.errors import PlanRejectedError
from floorplan.geometry import ValidationReport, build_geometry, normalize, validate
from floorplan.llm.client import Feedback
from floorplan.models import PlanResponse, PlanSpec


class PlanModel(Protocol):
    def extract(self, image_url: str, feedback: Feedback | None = None) -> PlanSpec: ...

    def edit(
        self, spec: PlanSpec, instruction: str, feedback: Feedback | None = None
    ) -> PlanSpec: ...


class PlanService:
    def __init__(self, model: PlanModel):
        self._model = model

    def parse(self, image_url: str) -> PlanResponse:
        return self._resolve(lambda feedback: self._model.extract(image_url, feedback))

    def edit(self, spec: PlanSpec, instruction: str) -> PlanResponse:
        return self._resolve(lambda feedback: self._model.edit(spec, instruction, feedback))

    def _resolve(self, request: Callable[[Feedback | None], PlanSpec]) -> PlanResponse:
        spec, report = _prepare(request(None))
        if report.errors:
            spec, report = _prepare(request(Feedback(spec, report.errors)))
        return _assemble(spec, report)


def from_spec(spec: PlanSpec) -> PlanResponse:
    return _assemble(*_prepare(spec))


def _prepare(spec: PlanSpec) -> tuple[PlanSpec, ValidationReport]:
    cleaned = normalize(spec)
    return cleaned, validate(cleaned)


def _assemble(spec: PlanSpec, report: ValidationReport) -> PlanResponse:
    if report.errors:
        raise PlanRejectedError(report.errors)
    geometry, warnings = build_geometry(spec)
    return PlanResponse(spec=spec, geometry=geometry, warnings=report.warnings + warnings)
