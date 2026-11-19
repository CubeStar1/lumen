from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from PIL import Image

from floorplan.geometry.vec import add, normalized, scale, sub, vec
from floorplan.models import OpeningType, PlanGeometry, Wall

OPENING_COLOURS = {OpeningType.DOOR: "tab:green", OpeningType.WINDOW: "tab:blue"}


def render(geometry: PlanGeometry, output: Path, source: Path | None = None) -> None:
    figure = Figure(figsize=(16 if source else 8, 8), layout="tight")
    if source:
        image_axes, plan_axes = figure.subplots(1, 2)
        image_axes.imshow(Image.open(source))
        image_axes.set_title("Input")
        image_axes.axis("off")
    else:
        plan_axes = figure.subplots()

    _draw_plan(plan_axes, geometry)
    figure.savefig(output, dpi=120)


def _draw_plan(axes: Axes, geometry: PlanGeometry) -> None:
    for room in geometry.rooms:
        axes.fill([p.x for p in room.polygon], [p.y for p in room.polygon], alpha=0.25)
        label = f"{room.name}\n{room.area} m²"
        axes.text(room.centroid.x, room.centroid.y, label, ha="center", va="center", fontsize=8)

    for wall in geometry.walls:
        _draw_wall(axes, wall)

    axes.set_aspect("equal")
    axes.set_title("Reconstructed (m)")
    axes.grid(alpha=0.3)


def _draw_wall(axes: Axes, wall: Wall) -> None:
    start, end = vec(wall.start), vec(wall.end)
    width = 4 if wall.exterior else 2
    axes.plot([start[0], end[0]], [start[1], end[1]], color="black", linewidth=width)

    direction = normalized(sub(end, start))
    for opening in wall.openings:
        a = add(start, scale(direction, opening.offset - opening.width / 2))
        b = add(start, scale(direction, opening.offset + opening.width / 2))
        colour = OPENING_COLOURS[opening.type]
        axes.plot([a[0], b[0]], [a[1], b[1]], color=colour, linewidth=width + 2)
