from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from PIL import Image

from floorplan.geometry.vec import add, normalized, scale, sub, vec
from floorplan.models import BuildingGeometry, LevelGeometry, OpeningType, Wall

OPENING_COLOURS = {
    OpeningType.DOOR: "tab:green",
    OpeningType.SLIDING_DOOR: "tab:olive",
    OpeningType.WINDOW: "tab:blue",
    OpeningType.OPENING: "tab:orange",
}


def render(geometry: BuildingGeometry, output: Path, source: Path | None = None) -> None:
    panels = len(geometry.levels) + (1 if source else 0)
    figure = Figure(figsize=(8 * panels, 8), layout="tight")
    axes = figure.subplots(1, panels, squeeze=False)[0]
    if source:
        axes[0].imshow(Image.open(source))
        axes[0].set_title("Input")
        axes[0].axis("off")
    for level_axes, level in zip(axes[-len(geometry.levels) :], geometry.levels, strict=True):
        _draw_level(level_axes, level)
    figure.savefig(output, dpi=120)


def _draw_level(axes: Axes, geometry: LevelGeometry) -> None:
    for room in geometry.rooms:
        xs, ys = [p.x for p in room.polygon], [p.y for p in room.polygon]
        axes.fill(xs, ys, alpha=0.1 if room.outdoor else 0.25, hatch="//" if room.outdoor else None)
        label = f"{room.name}\n{room.area} m²"
        axes.text(room.centroid.x, room.centroid.y, label, ha="center", va="center", fontsize=8)

    for wall in geometry.walls:
        _draw_wall(axes, wall)

    axes.set_aspect("equal")
    axes.set_title(f"{geometry.name} (m)")
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
