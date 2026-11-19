"""Runs a floor plan through the pipeline and writes the response JSON and a preview PNG.

Pass an image to go through the language model, or a *.spec.json file to skip it.
"""

import argparse
from pathlib import Path

from floorplan.config import get_settings
from floorplan.imaging import to_data_url
from floorplan.main import get_service
from floorplan.models import PlanResponse, PlanSpec
from floorplan.render import render
from floorplan.service import from_spec


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="floor plan image or *.spec.json")
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args()

    is_spec = args.input.suffix == ".json"
    response = _from_spec(args.input) if is_spec else _from_image(args.input)
    name = args.input.name.split(".")[0]

    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / f"{name}.json"
    png_path = args.out / f"{name}.png"
    json_path.write_text(response.model_dump_json(indent=2))
    render(response.geometry, png_path, source=None if is_spec else args.input)

    print(f"{len(response.geometry.rooms)} rooms, {len(response.geometry.walls)} walls")
    print(f"Notes: {response.spec.notes}")
    for warning in response.warnings:
        print(f"Warning: {warning}")
    print(f"Wrote {json_path} and {png_path}")


def _from_image(path: Path) -> PlanResponse:
    image_url = to_data_url(path.read_bytes(), get_settings().max_image_side)
    return get_service().parse(image_url)


def _from_spec(path: Path) -> PlanResponse:
    return from_spec(PlanSpec.model_validate_json(path.read_text()))


if __name__ == "__main__":
    main()
