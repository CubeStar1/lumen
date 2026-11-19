from pathlib import Path
from statistics import mean

from matplotlib.figure import Figure

from floorplan.evaluation.metrics import Score
from floorplan.evaluation.snapshot import Snapshot

COLUMNS = [
    ("Wall P", "wall_precision"),
    ("Wall R", "wall_recall"),
    ("Wall F1", "wall_f1"),
    ("Room IoU", "room_iou"),
    ("Rooms", "rooms_matched"),
    ("Types", "room_type_accuracy"),
    ("Open P", "opening_precision"),
    ("Open R", "opening_recall"),
    ("Open err m", "opening_position_error"),
    ("Stairs R", "stair_recall"),
    ("Riser err", "stair_riser_error"),
    ("Scale", "scale_ratio"),
]


def markdown(title: str, scores: dict[str, Score], failures: dict[str, str]) -> str:
    header = "| Case | " + " | ".join(name for name, _ in COLUMNS) + " |"
    divider = "|" + "---|" * (len(COLUMNS) + 1)
    rows = [_row(case, s.model_dump()) for case, s in sorted(scores.items())]
    if len(scores) > 1:
        rows.append(_row("**mean**", _means(scores)))
    rows += [f"| {case} | failed: {reason} |" for case, reason in sorted(failures.items())]
    return "\n".join([f"# {title}", "", header, divider, *rows, ""])


def overlay(
    predicted: Snapshot, reference: Snapshot, offset: tuple[float, float], output: Path
) -> None:
    figure = Figure(figsize=(9, 9), layout="tight")
    axes = figure.subplots()
    for room in reference.rooms:
        x, y = room.shape.exterior.xy
        axes.fill(x, y, color="tab:gray", alpha=0.15)
    for a, b in reference.walls:
        axes.plot([a[0], b[0]], [a[1], b[1]], color="black", linewidth=5, alpha=0.35)
    for a, b in predicted.translated(offset).walls:
        axes.plot([a[0], b[0]], [a[1], b[1]], color="tab:red", linewidth=1.5)
    for o in reference.openings:
        axes.plot(*o.position, marker="o", color="tab:gray", markersize=7, alpha=0.5)
    for o in predicted.translated(offset).openings:
        axes.plot(*o.position, marker="x", color="tab:red", markersize=6)
    axes.set_aspect("equal")
    axes.set_title("Reference (grey) vs prediction (red), metres")
    axes.grid(alpha=0.3)
    figure.savefig(output, dpi=110)


def _row(case: str, values: dict) -> str:
    cells = [_cell(values.get(key)) for _, key in COLUMNS]
    return f"| {case} | " + " | ".join(cells) + " |"


def _means(scores: dict[str, Score]) -> dict:
    result = {}
    for _, key in COLUMNS:
        numbers = [v for s in scores.values() if isinstance(v := getattr(s, key), float | int)]
        result[key] = round(mean(numbers), 3) if numbers else None
    return result


def _cell(value) -> str:
    if value is None:
        return "–"
    return f"{value:.2f}" if isinstance(value, float) else str(value)
