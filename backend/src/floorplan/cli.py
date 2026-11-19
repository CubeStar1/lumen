"""Runs a floor plan through the pipeline and writes the response JSON and a preview PNG.

Pass an image to go through the language model, or a *.spec.json file (a building spec, or a
legacy single-floor spec) to skip it. `--sheet` reads one image as a sheet of a whole building's
plans; several images are read as one photo per floor. A building's saved answers (a plan folder
in data/, or an *.answers.json file) are rebuilt with the current pipeline without the model.
"""

import argparse
import json
import sys
from pathlib import Path

from floorplan.building import BuildingAnswers, BuildingReader, rebuild
from floorplan.config import get_settings
from floorplan.imaging import load_image, prepare
from floorplan.legacy import upgrade_spec
from floorplan.main import get_service
from floorplan.models import PlanResponse
from floorplan.render import render
from floorplan.service import from_spec
from floorplan.store import ANSWERS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+", help="plan image(s) or *.spec.json")
    parser.add_argument("--sheet", action="store_true", help="the image holds every floor's plan")
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")

    first = args.inputs[0]
    name = first.name.split(".")[0]
    answers_file = first / ANSWERS if first.is_dir() else first
    is_spec = first.suffix == ".json" or first.is_dir()
    if answers_file.name.endswith(ANSWERS):
        response = rebuild(BuildingAnswers.model_validate_json(answers_file.read_text("utf-8")))
    elif is_spec:
        response = _from_spec(first)
    elif args.sheet or len(args.inputs) > 1:
        response, answers = _building(args.inputs, args.sheet)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"{name}.{ANSWERS}").write_text(answers.model_dump_json(), encoding="utf-8")
    else:
        response = _from_image(first)

    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / f"{name}.json"
    png_path = args.out / f"{name}.png"
    json_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    render(response.geometry, png_path, source=None if is_spec else first)

    for level in response.geometry.levels:
        print(f"{level.name}: {len(level.rooms)} rooms, {len(level.walls)} walls")
    for level in response.spec.levels:
        print(f"Notes ({level.floor.name}): {level.floor.notes}")
    for warning in response.warnings:
        print(f"Warning: {warning}")
    print(f"Wrote {json_path} and {png_path}")


def _from_image(path: Path) -> PlanResponse:
    image = prepare(load_image(path.read_bytes()), get_settings().max_image_side)
    return get_service().parse(image)


def _building(paths: list[Path], sheet: bool) -> tuple[PlanResponse, BuildingAnswers]:
    reader = BuildingReader(get_service(), get_settings().max_image_side)
    images = [load_image(path.read_bytes()) for path in paths]
    progress = _Printer()
    read = reader.from_sheet(images[0], progress) if sheet else reader.from_photos(images, progress)
    return read.response, read.answers


class _Printer:
    def plan(self, stages: list[str]) -> None:
        pass

    def start(self, stage: str) -> None:
        print(f"... {stage}")

    def finish(self, stage: str) -> None:
        print(f"done {stage}")


def _from_spec(path: Path) -> PlanResponse:
    return from_spec(upgrade_spec(json.loads(path.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
