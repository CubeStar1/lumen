"""Runs the evaluation set through the pipeline and scores it against hand-labelled references.

Each case is a folder in eval/cases/ with reference.json and image.png (or .jpg). A run writes
the raw predictions, overlays, scores.json and report.md to eval/runs/<name>/. Model output varies
between calls, so --repeat N parses every case N times and reports the mean. Pass --rescore with an
earlier run's name to score its saved predictions again without calling the model.
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
from floorplan.imaging import load_image, to_data_url
from floorplan.main import get_service
from floorplan.models import PlanResponse

IMAGE_NAMES = ("image.png", "image.jpg", "image.jpeg")
PARALLEL_CALLS = 6

Prediction = PlanResponse | str


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="case names (default: all)")
    parser.add_argument("--root", type=Path, default=Path("eval"))
    parser.add_argument("--name", help="run name (default: timestamp)")
    parser.add_argument("--rescore", metavar="RUN", help="reuse the predictions of an earlier run")
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


def _predict(cases: dict[str, Path], output: Path, repeat: int) -> dict[str, list[Prediction]]:
    def run(job: tuple[str, Path, int]) -> tuple[str, Prediction]:
        name, folder, index = job
        try:
            response = get_service().parse(_image_url(folder))
        except (ModelError, PlanRejectedError) as exc:
            return name, str(exc)
        path = output / f"{name}.{index}.json"
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        return name, response

    jobs = [(name, folder, i) for name, folder in cases.items() for i in range(repeat)]
    results: dict[str, list[Prediction]] = {name: [] for name in cases}
    with ThreadPoolExecutor(PARALLEL_CALLS) as pool:
        for name, prediction in pool.map(run, jobs):
            results[name].append(prediction)
    return results


def _image_url(folder: Path) -> str:
    image = next(folder / n for n in IMAGE_NAMES if (folder / n).exists())
    return to_data_url(load_image(image.read_bytes()), get_settings().max_image_side)


def _load_all(folder: Path, name: str) -> list[Prediction]:
    paths = sorted(folder.glob(f"{name}.*.json")) or sorted(folder.glob(f"{name}.json"))
    return [PlanResponse.model_validate_json(p.read_text(encoding="utf-8")) for p in paths]


if __name__ == "__main__":
    main()
