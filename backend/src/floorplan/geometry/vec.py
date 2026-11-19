import math

from floorplan.models import Point

Vec = tuple[float, float]


def vec(p: Point) -> Vec:
    return (p.x, p.y)


def point(v: Vec) -> Point:
    return Point(x=round(v[0], 4), y=round(v[1], 4))


def sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1])


def add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])


def scale(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s)


def dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1]


def length(a: Vec) -> float:
    return math.hypot(a[0], a[1])


def normalized(a: Vec) -> Vec:
    n = length(a)
    return (a[0] / n, a[1] / n)


def edges(polygon: list[Point]) -> list[tuple[Vec, Vec]]:
    points = [vec(p) for p in polygon]
    return list(zip(points, points[1:] + points[:1], strict=True))
