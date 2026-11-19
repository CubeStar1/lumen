"""Runs the evaluation set through the pipeline and scores it against hand-labelled references.

Each case is a folder in eval/cases/ with reference.json and image.png (or .jpg). A run writes
the raw predictions, overlays, scores.json and report.md to eval/runs/<name>/. Model output varies
between calls, so --repeat N parses every case N times and reports the mean. Pass --rescore with an
earlier run's name to score its saved predictions again without calling the model, or --rebuild to
run the model's saved raw answers through the current geometry pipeline first.
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from floorplan.config import get_settings
from floorplan.errors import ModelError, PlanRejectedError
from floorplan.evaluation.metrics import Score, mean_score, score
from floorplan.evaluation.reference import load_reference
from floorplan.evaluation.report import markdown, overlay
from floorplan.evaluation.snapshot import from_geometry, from_reference
from floorplan.extraction import FloorExtraction, to_floor
from floorplan.imaging import PreparedImage, load_image, prepare
from floorplan.legacy import upgrade_plan, upgrade_spec
from floorplan.main import get_service, plan_model
from floorplan.models import FloorSpec, PlanResponse
from floorplan.service import PlanService, from_spec, single_floor

IMAGE_NAMES = ("image.png", "image.jpg", "image.jpeg")
PARALLEL_CALLS = 6

Prediction = PlanResponse | str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="case names (default: all)")
    parser.add_argument("--root", type=Path, default=Path("eval"))
    parser.add_argument("--name", help="run name (default: timestamp)")
    parser.add_argument("--rescore", metavar="RUN", help="reuse the predictions of an earlier run")
    parser.add_argument(
        "--rebuild", metavar="RUN", help="rebuild an earlier run's raw answers with this pipeline"
    )
    parser.add_argument("--repeat", type=int, default=1, help="parses per case (default: 1)")
    parser.add_argument("--model", help="override OPENAI_MODEL")
    parser.add_argument("--effort", help="override OPENAI_REASONING_EFFORT")
    args = parser.parse_args()
    _override_settings(model=args.model, effort=args.effort)

    cases = _cases(args.root / "cases", args.cases)
    run = (
        args.root / "runs" / (args.name or args.rescore or datetime.now().strftime("%Y%m%d-%H%M%S"))
    )
    predictions_dir = run / "predictions"
    (run / "overlays").mkdir(parents=True, exist_ok=True)
    predictions_dir.mkdir(exist_ok=True)

    if args.rescore:
        source = args.root / "runs" / args.rescore / "predictions"
        predictions = {name: _load_all(source, name) for name in cases}
    elif args.rebuild:
        source = args.root / "runs" / args.rebuild / "raw"
        predictions = {name: _rebuild_all(source, name) for name in cases}
        _save(predictions, predictions_dir)
    else:
        predictions = _predict(cases, predictions_dir, args.repeat)

    scores: dict[str, Score] = {}
    failures: dict[str, str] = {}
    for name, folder in cases.items():
        reference = from_reference(load_reference(folder / "reference.json"))
        parsed = [p for p in predictions[name] if isinstance(p, PlanResponse)]
        errors = [p for p in predictions[name] if isinstance(p, str)]
        if not parsed:
            failures[name] = errors[0] if errors else "no saved prediction"
            continue
        if errors:
            failures[name] = f"{len(errors)}/{len(predictions[name])} parses failed: {errors[0]}"
        snapshots = [from_geometry(p.geometry.levels[0]) for p in parsed]
        case_scores = [score(s, reference) for s in snapshots]
        scores[name] = mean_score(case_scores)
        overlay(snapshots[0], reference, case_scores[0].offset, run / "overlays" / f"{name}.png")

    settings = get_settings()
    effort = settings.openai_reasoning_effort or "default"
    runs = max(len(v) for v in predictions.values()) if predictions else 0
    title = f"Eval {run.name} - {settings.openai_model} - effort {effort} - {runs} run(s) per case"
    report = markdown(title, scores, failures)
    (run / "report.md").write_text(report, encoding="utf-8")
    (run / "scores.json").write_text(
        json.dumps({k: v.model_dump() for k, v in scores.items()}, indent=2), encoding="utf-8"
    )
    print(report)
    print(f"Wrote {run}")


def _cases(folder: Path, names: list[str]) -> dict[str, Path]:
    found = {p.name: p for p in sorted(folder.iterdir()) if (p / "reference.json").exists()}
    missing = set(names) - found.keys()
    if missing:
        raise SystemExit(f"Unknown cases: {', '.join(sorted(missing))}")
    return {n: found[n] for n in names} if names else found


def _override_settings(model: str | None, effort: str | None) -> None:
    if model:
        os.environ["OPENAI_MODEL"] = model
    if effort:
        os.environ["OPENAI_REASONING_EFFORT"] = effort
    get_settings.cache_clear()
    get_service.cache_clear()


class _Recorder:
    """Wraps the model and keeps its last raw answer, before any geometry clean-up."""

    def __init__(self, model):
        self._model = model
        self.answer: FloorExtraction | None = None

    def extract(self, image: PreparedImage, feedback=None, hint=None) -> FloorExtraction:
        self.answer = self._model.extract(image, feedback, hint)
        return self.answer

    def edit(self, floor: FloorSpec, instruction: str, feedback=None) -> FloorSpec:
        raise NotImplementedError


def _predict(cases: dict[str, Path], output: Path, repeat: int) -> dict[str, list[Prediction]]:
    raw = output.parent / "raw"
    raw.mkdir(exist_ok=True)

    def run(job: tuple[str, Path, int]) -> tuple[str, Prediction]:
        name, folder, index = job
        recorder = _Recorder(plan_model(get_settings()))
        try:
            response = PlanService(recorder).parse(_image(folder))
        except (ModelError, PlanRejectedError) as exc:
            return name, str(exc)
        finally:
            if recorder.answer is not None:
                (raw / f"{name}.{index}.json").write_text(
                    recorder.answer.model_dump_json(indent=2), encoding="utf-8"
                )
        path = output / f"{name}.{index}.json"
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        return name, response

    jobs = [(name, folder, i) for name, folder in cases.items() for i in range(repeat)]
    results: dict[str, list[Prediction]] = {name: [] for name in cases}
    with ThreadPoolExecutor(PARALLEL_CALLS) as pool:
        for name, prediction in pool.map(run, jobs):
            results[name].append(prediction)
    return results


def _image(folder: Path) -> PreparedImage:
    image = next(folder / n for n in IMAGE_NAMES if (folder / n).exists())
    return prepare(load_image(image.read_bytes()), get_settings().max_image_side)


def _rebuild_all(folder: Path, name: str) -> list[Prediction]:
    results: list[Prediction] = []
    for path in sorted(folder.glob(f"{name}.*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        floor = (
            to_floor(_extraction(data))
            if "dimensions" in data
            else FloorSpec.model_validate(
                upgrade_spec(_as_building(data)).levels[0].floor.model_dump()
            )
        )
        try:
            results.append(from_spec(single_floor(floor)))
        except PlanRejectedError as exc:
            results.append(str(exc))
    return results


def _save(predictions: dict[str, list[Prediction]], folder: Path) -> None:
    for name, results in predictions.items():
        for index, result in enumerate(results):
            if isinstance(result, PlanResponse):
                path = folder / f"{name}.{index}.json"
                path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def _as_building(floor: dict) -> dict:
    return {"kind": "floor", "levels": [{"index": 0, "elevation": 0.0, "floor": floor}]}


def _load_all(folder: Path, name: str) -> list[Prediction]:
    paths = sorted(folder.glob(f"{name}.*.json")) or sorted(folder.glob(f"{name}.json"))
    return [
        PlanResponse.model_validate(upgrade_plan(json.loads(p.read_text(encoding="utf-8"))))
        for p in paths
    ]


def _extraction(data: dict) -> FloorExtraction:
    """A saved raw answer, filling in fields added since it was saved."""
    for room in data.get("rooms", []):
        room.setdefault("size", None)
    return FloorExtraction.model_validate(data)


if __name__ == "__main__":
    main()
