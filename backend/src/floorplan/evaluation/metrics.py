"""Scores a predicted plan against its reference after aligning the two.

Walls are compared as sampled points (length-weighted), rooms by IoU, openings and stairs
by one-to-one greedy matching.
"""

import math
from collections.abc import Callable, Sequence
from itertools import product

import numpy as np
from pydantic import BaseModel

from floorplan.evaluation.snapshot import Segment, Snapshot
from floorplan.geometry.vec import Vec

WALL_DISTANCE = 0.15
WALL_ANGLE = math.radians(5)
SAMPLE_SPACING = 0.05
ALIGN_SPACING = 0.1
ROOM_MIN_IOU = 0.1
OPENING_DISTANCE = 0.3
STAIR_MIN_IOU = 0.3


class Score(BaseModel):
    wall_precision: float
    wall_recall: float
    wall_f1: float
    room_iou: float
    room_type_accuracy: float | None
    rooms_matched: str
    opening_precision: float | None
    opening_recall: float | None
    opening_position_error: float | None
    stair_recall: float | None
    stair_riser_error: float | None
    scale_ratio: float
    offset: tuple[float, float]


def score(predicted: Snapshot, reference: Snapshot) -> Score:
    offset = align(predicted, reference)
    aligned = predicted.translated(offset)
    precision, recall = wall_coverage(aligned.walls, reference.walls)

    room_pairs = _greedy(
        aligned.rooms, reference.rooms, lambda p, r: _iou(p.shape, r.shape), ROOM_MIN_IOU
    )
    opening_pairs = _greedy(
        aligned.openings,
        reference.openings,
        lambda p, r: -_distance(p.position, r.position) if p.type == r.type else -math.inf,
        -OPENING_DISTANCE,
    )
    stair_pairs = _greedy(
        aligned.stairs, reference.stairs, lambda p, r: _iou(p.shape, r.shape), STAIR_MIN_IOU
    )

    return Score(
        wall_precision=round(precision, 3),
        wall_recall=round(recall, 3),
        wall_f1=round(_f1(precision, recall), 3),
        room_iou=round(sum(v for _, _, v in room_pairs) / max(len(reference.rooms), 1), 3),
        room_type_accuracy=_ratio(sum(p.type == r.type for p, r, _ in room_pairs), len(room_pairs)),
        rooms_matched=f"{len(room_pairs)}/{len(reference.rooms)}",
        opening_precision=_ratio(len(opening_pairs), len(aligned.openings)),
        opening_recall=_ratio(len(opening_pairs), len(reference.openings)),
        opening_position_error=_mean([-v for _, _, v in opening_pairs]),
        stair_recall=_ratio(len(stair_pairs), len(reference.stairs)),
        stair_riser_error=_mean(
            [abs(p.risers - r.risers) for p, r, _ in stair_pairs if p.risers and r.risers]
        ),
        scale_ratio=round(_extent(predicted.walls) / max(_extent(reference.walls), 1e-9), 3),
        offset=(round(offset[0], 3), round(offset[1], 3)),
    )


def mean_score(scores: list[Score]) -> Score:
    """Field-wise mean over repeated runs of one case; None values are skipped."""
    first = scores[0]
    if len(scores) == 1:
        return first
    values = {}
    for field in Score.model_fields:
        items = [getattr(s, field) for s in scores]
        numbers = [v for v in items if isinstance(v, float | int)]
        values[field] = round(sum(numbers) / len(numbers), 3) if numbers else None
    matched = [int(s.rooms_matched.split("/")[0]) for s in scores]
    total = first.rooms_matched.split("/")[1]
    values["rooms_matched"] = f"{sum(matched) / len(matched):.1f}/{total}"
    values["offset"] = first.offset
    return Score(**values)


def align(predicted: Snapshot, reference: Snapshot) -> Vec:
    """Translation that best lays the predicted walls over the reference walls."""
    centre = _sub(_centre(reference.walls), _centre(predicted.walls))
    best = centre
    for radius, step in ((3.0, 0.25), (0.3, 0.05), (0.06, 0.01)):
        steps = np.arange(-radius, radius + 1e-9, step)
        origin = best
        candidates = [(origin[0] + dx, origin[1] + dy) for dx, dy in product(steps, steps)]
        best = max(candidates, key=lambda o: _alignment_fit(predicted.walls, reference.walls, o))
    return best


def wall_coverage(predicted: list[Segment], reference: list[Segment]) -> tuple[float, float]:
    return _covered(predicted, reference)[0], _covered(reference, predicted)[0]


def _alignment_fit(
    predicted: list[Segment], reference: list[Segment], offset: Vec
) -> tuple[float, float]:
    moved = [
        ((a[0] + offset[0], a[1] + offset[1]), (b[0] + offset[0], b[1] + offset[1]))
        for a, b in predicted
    ]
    p, p_error = _covered(moved, reference, ALIGN_SPACING)
    r, r_error = _covered(reference, moved, ALIGN_SPACING)
    return round(_f1(p, r), 3), -(p_error + r_error)


def _covered(
    source: list[Segment], target: list[Segment], spacing: float = SAMPLE_SPACING
) -> tuple[float, float]:
    """Length fraction of `source` within tolerance of a parallel `target` wall, and the
    mean distance of the matched part."""
    points, directions, weights = _samples(source, spacing)
    if not len(points) or not target:
        return 0.0, 0.0
    starts = np.array([a for a, _ in target])
    ends = np.array([b for _, b in target])
    axes = ends - starts
    lengths = np.maximum(np.linalg.norm(axes, axis=1), 1e-9)
    units = axes / lengths[:, None]

    relative = points[:, None, :] - starts[None, :, :]
    along = np.clip(np.einsum("nmk,mk->nm", relative, units), 0, lengths[None, :])
    nearest = starts[None, :, :] + along[..., None] * units[None, :, :]
    distance = np.linalg.norm(points[:, None, :] - nearest, axis=2)
    cross = np.abs(
        directions[:, None, 0] * units[None, :, 1] - directions[:, None, 1] * units[None, :, 0]
    )

    parallel_distance = np.where(cross < math.sin(WALL_ANGLE), distance, np.inf).min(axis=1)
    matched = parallel_distance < WALL_DISTANCE
    if not matched.any():
        return 0.0, 0.0
    fraction = float(weights[matched].sum() / weights.sum())
    return fraction, float(np.average(parallel_distance[matched], weights=weights[matched]))


def _samples(segments: list[Segment], spacing: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points, directions, weights = [], [], []
    for a, b in segments:
        start, end = np.array(a), np.array(b)
        span = float(np.linalg.norm(end - start))
        if span < 1e-6:
            continue
        count = max(int(math.ceil(span / spacing)), 1)
        t = (np.arange(count) + 0.5) / count
        points.append(start + t[:, None] * (end - start))
        directions.append(np.repeat(((end - start) / span)[None, :], count, axis=0))
        weights.append(np.full(count, span / count))
    if not points:
        return np.empty((0, 2)), np.empty((0, 2)), np.empty(0)
    return np.concatenate(points), np.concatenate(directions), np.concatenate(weights)


def _greedy[P, R](
    predicted: Sequence[P],
    reference: Sequence[R],
    similarity: Callable[[P, R], float],
    floor: float,
) -> list[tuple[P, R, float]]:
    candidates = sorted(
        (
            (similarity(p, r), i, j)
            for (i, p), (j, r) in product(enumerate(predicted), enumerate(reference))
        ),
        reverse=True,
    )
    used_p: set[int] = set()
    used_r: set[int] = set()
    pairs = []
    for value, i, j in candidates:
        if value < floor:
            break
        if i in used_p or j in used_r:
            continue
        used_p.add(i)
        used_r.add(j)
        pairs.append((predicted[i], reference[j], value))
    return pairs


def _iou(a, b) -> float:
    if not (a.is_valid and b.is_valid):
        return 0.0
    union = a.union(b).area
    return a.intersection(b).area / union if union else 0.0


def _centre(segments: list[Segment]) -> Vec:
    xs = [p[0] for s in segments for p in s]
    ys = [p[1] for s in segments for p in s]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2) if xs else (0.0, 0.0)


def _extent(segments: list[Segment]) -> float:
    xs = [p[0] for s in segments for p in s]
    ys = [p[1] for s in segments for p in s]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) if xs else 0.0


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1])


def _distance(a: Vec, b: Vec) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 3) if whole else None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None
