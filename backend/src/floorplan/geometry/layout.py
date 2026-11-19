"""Completes a wall-first floor: joins its walls into a graph and finds its rooms from it.

Walls are connected (see `wallgraph`), and where the model stopped a wall at a door's jambs
the two collinear pieces are merged across the door. Rooms are the faces the walls enclose,
named by the model's label points; an open-plan face with several labels is shared out between
them along the outlines the model traced for those rooms, the rest by nearest label. Outdoor
areas keep the outline the model drew.
"""

import math

from shapely import make_valid, voronoi_polygons
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import unary_union

from floorplan.geometry.orient import angle_between, angle_of
from floorplan.geometry.regions import Label, Region, assign
from floorplan.geometry.vec import Vec, add, dot, length, normalized, scale, sub, vec
from floorplan.geometry.wallgraph import connect
from floorplan.models import FloorSpec, OpeningSpec, Point, RoomSpec, RoomType, WallKind, WallSpec

BRIDGE_REACH = 2.5
BRIDGE_ALIGNMENT = 0.1
OPENING_ON_GAP = 0.25
PARALLEL = math.radians(3)
UNENCLOSING = (WallKind.LOW, WallKind.PARAPET)


def complete(floor: FloorSpec) -> tuple[FloorSpec, list[str]]:
    if floor.derive_walls:
        return floor, []
    walls, openings = _bridge_doorways(connect([], floor.walls), floor.openings)
    rooms, warnings = _rooms(floor.rooms, walls)
    return floor.model_copy(update={"walls": walls, "openings": openings, "rooms": rooms}), warnings


def _rooms(rooms: list[RoomSpec], walls: list[WallSpec]) -> tuple[list[RoomSpec], list[str]]:
    indoor = [r for r in rooms if not r.outdoor]
    labels, warnings = [], []
    for room in indoor:
        point = _label_point(room)
        if point is None:
            warnings.append(f"Room {room.id} has no position; dropped.")
            continue
        labels.append(Label(room.id, point, repaired(room.polygon)))

    segments = [(vec(w.start), vec(w.end)) for w in walls if w.kind not in UNENCLOSING]
    regions, region_warnings = assign(labels, segments)
    shapes = _share_out(regions, {label.id: label for label in labels})

    result = [
        r.model_copy(update={"polygon": _outline(shapes[r.id])}) for r in indoor if r.id in shapes
    ]
    result += [_repair_outline(r) for r in rooms if r.outdoor]
    result += [
        _unlabelled(i, region) for i, region in enumerate(r for r in regions if not r.labels)
    ]
    return result, warnings + region_warnings


def _share_out(regions: list[Region], labels: dict[str, Label]) -> dict[str, Polygon]:
    """Each label's floor. An open-plan face is split along the outlines the model traced for its
    rooms; whatever those leave uncovered goes to the nearest label."""
    shapes: dict[str, Polygon] = {}
    for region in regions:
        if len(region.labels) == 1:
            shapes[region.labels[0]] = region.shape
            continue
        members = [labels[label_id] for label_id in region.labels]
        traced = {
            m.id: m.fallback.intersection(region.shape)
            for m in members
            if m.fallback is not None and m.fallback.is_valid
        }
        remainder = region.shape.difference(unary_union(list(traced.values())))
        sites = MultiPoint([m.point for m in members])
        for cell in voronoi_polygons(sites, extend_to=region.shape).geoms:
            member = next(m for m in members if cell.covers(ShapelyPoint(m.point)))
            share = cell.intersection(remainder)
            if member.id in traced:
                share = traced[member.id].union(share)
            shapes[member.id] = _part_containing(share, member.point)
    return shapes


def _bridge_doorways(
    walls: list[WallSpec], openings: list[OpeningSpec]
) -> tuple[list[WallSpec], list[OpeningSpec]]:
    """Merges collinear walls that stop either side of an opening into one wall."""
    walls = list(walls)
    renamed: dict[str, str] = {}
    merged = True
    while merged:
        merged = False
        for i, a in enumerate(walls):
            for j, b in enumerate(walls):
                if i == j or not _collinear(a, b):
                    continue
                gap = _gap(a, b)
                if gap is not None and any(_on_segment(vec(o.position), gap) for o in openings):
                    walls[i] = a.model_copy(update=_span(a, b))
                    renamed[b.id] = a.id
                    del walls[j]
                    merged = True
                    break
            if merged:
                break

    def target(wall_id: str | None) -> str | None:
        while wall_id in renamed:
            wall_id = renamed[wall_id]
        return wall_id

    return walls, [o.model_copy(update={"wall": target(o.wall)}) for o in openings]


def _collinear(a: WallSpec, b: WallSpec) -> bool:
    if a.kind != b.kind:
        return False
    sa, sb = (vec(a.start), vec(a.end)), (vec(b.start), vec(b.end))
    if angle_between(angle_of(sa), angle_of(sb)) > PARALLEL:
        return False
    direction = normalized(sub(sa[1], sa[0]))
    normal = (-direction[1], direction[0])
    return all(abs(dot(sub(p, sa[0]), normal)) <= BRIDGE_ALIGNMENT for p in sb)


def _gap(a: WallSpec, b: WallSpec) -> tuple[Vec, Vec] | None:
    """The gap between the nearest ends of two collinear, non-overlapping walls."""
    ends = [
        (math.dist(p, q), p, q)
        for p in (vec(a.start), vec(a.end))
        for q in (vec(b.start), vec(b.end))
    ]
    distance, p, q = min(ends)
    if not 1e-6 < distance <= BRIDGE_REACH or _overlap(a, b):
        return None
    return p, q


def _overlap(a: WallSpec, b: WallSpec) -> bool:
    origin = vec(a.start)
    direction = normalized(sub(vec(a.end), origin))
    ta = sorted(dot(sub(vec(p), origin), direction) for p in (a.start, a.end))
    tb = sorted(dot(sub(vec(p), origin), direction) for p in (b.start, b.end))
    return min(ta[1], tb[1]) - max(ta[0], tb[0]) > 1e-6


def _span(a: WallSpec, b: WallSpec) -> dict[str, Point]:
    points = [vec(a.start), vec(a.end), vec(b.start), vec(b.end)]
    origin = points[0]
    direction = normalized(sub(points[1], origin))
    ordered = sorted(points, key=lambda p: dot(sub(p, origin), direction))
    return {
        "start": Point(x=ordered[0][0], y=ordered[0][1]),
        "end": Point(x=ordered[-1][0], y=ordered[-1][1]),
    }


def _on_segment(p: Vec, segment: tuple[Vec, Vec]) -> bool:
    start, end = segment
    axis = sub(end, start)
    span = length(axis)
    t = min(max(dot(sub(p, start), axis) / (span * span), 0.0), 1.0)
    return math.dist(p, add(start, scale(axis, t))) <= OPENING_ON_GAP


def repaired(outline: list[Point]) -> Polygon | None:
    """A valid polygon for a traced outline, fixing self-intersections; None if there is none."""
    if len(outline) < 3:
        return None
    shape = make_valid(Polygon([vec(p) for p in outline]))
    parts = [g for g in getattr(shape, "geoms", [shape]) if isinstance(g, Polygon) and g.area > 0]
    return max(parts, key=lambda g: g.area) if parts else None


def _repair_outline(room: RoomSpec) -> RoomSpec:
    shape = repaired(room.polygon)
    return room.model_copy(update={"polygon": _outline(shape)}) if shape else room


def _label_point(room: RoomSpec) -> Vec | None:
    if room.label is not None:
        return vec(room.label)
    if len(room.polygon) >= 3:
        inside = Polygon([vec(p) for p in room.polygon]).representative_point()
        return (inside.x, inside.y)
    return None


def _part_containing(shape, point: Vec) -> Polygon:
    parts = list(getattr(shape, "geoms", [shape]))
    polygons = [p for p in parts if isinstance(p, Polygon)]
    return next(
        (p for p in polygons if p.covers(ShapelyPoint(point))), max(polygons, key=lambda p: p.area)
    )


def _unlabelled(index: int, region: Region) -> RoomSpec:
    inside = region.shape.representative_point()
    return RoomSpec(
        id=f"u{index + 1}",
        name="Room",
        type=RoomType.OTHER,
        outdoor=False,
        label=Point(x=round(inside.x, 4), y=round(inside.y, 4)),
        polygon=_outline(region.shape),
    )


def _outline(shape: Polygon) -> list[Point]:
    """The shape's outer boundary, rounded, and repaired if rounding made it touch itself."""
    points = [Point(x=round(x, 4), y=round(y, 4)) for x, y in shape.exterior.coords[:-1]]
    fixed = repaired(points)
    if fixed is None or fixed.equals(Polygon([vec(p) for p in points])):
        return points
    return [Point(x=round(x, 4), y=round(y, 4)) for x, y in fixed.exterior.coords[:-1]]
