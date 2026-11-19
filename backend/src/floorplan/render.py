from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PIL import Image

from floorplan.geometry.vec import add, normalized, scale, sub, vec
from floorplan.models import BuildingGeometry, LevelGeometry, OpeningType, Stair, Wall

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
    for stair in geometry.stairs:
        _draw_stair(axes, stair)
    for column in geometry.columns:
        half = column.size / 2
        axes.add_patch(
            Rectangle(
                (column.position.x - half, column.position.y - half),
                column.size,
                column.size,
                color="black",
            )
        )

    axes.set_aspect("equal")
    axes.set_title(f"{geometry.name} (m)")
    axes.grid(alpha=0.3)


def _draw_stair(axes: Axes, stair: Stair) -> None:
    if not stair.steps:
        xs, ys = [p.x for p in stair.footprint], [p.y for p in stair.footprint]
        axes.fill(xs, ys, fill=False, hatch="xx", edgecolor="grey", linewidth=0)
    for step in stair.steps:
        xs, ys = [p.x for p in step.corners], [p.y for p in step.corners]
        axes.fill(xs, ys, facecolor="white", edgecolor="grey", linewidth=0.6)
    for landing in stair.landings:
        xs, ys = [p.x for p in landing.polygon], [p.y for p in landing.polygon]
        axes.fill(xs, ys, facecolor="white", edgecolor="grey", linewidth=0.6)
    for railing in stair.railings:
        axes.plot([p.x for p in railing], [p.y for p in railing], color="tab:red", linewidth=1)
    if stair.steps:
        first, last = stair.steps[0].corners, stair.steps[-1].corners
        a = ((first[0].x + first[1].x) / 2, (first[0].y + first[1].y) / 2)
        b = ((last[2].x + last[3].x) / 2, (last[2].y + last[3].y) / 2)
        axes.annotate("", b, a, arrowprops={"arrowstyle": "->", "color": "tab:red"})


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
