"""Shared geometry helpers for future CAM and simulation modules.

本模块定义通用几何工具，便于后续在 DxfLine / ToolpathPoint / CAM 偏置 /
canvas 绘制中复用。当前已实现内容以不破坏既有接口为前提，仅做增量补充。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point2D:
    """Two-dimensional point in millimeters."""

    x: float
    y: float


@dataclass(frozen=True)
class Vector2D:
    """Two-dimensional vector with basic arithmetic helpers."""

    x: float
    y: float

    def __add__(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        return Vector2D(self.x * scalar, self.y * scalar)

    @property
    def length(self) -> float:
        """Return the Euclidean length of the vector."""
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vector2D":
        """Return a unit vector with the same direction, or zero if length is 0."""
        length = self.length
        if length <= 0.0:
            return Vector2D(0.0, 0.0)
        return Vector2D(self.x / length, self.y / length)


def distance(a: Point2D, b: Point2D) -> float:
    """Return the Euclidean distance between two points."""
    return math.hypot(a.x - b.x, a.y - b.y)


def lerp(a: Point2D, b: Point2D, t: float) -> Point2D:
    """Linearly interpolate between two points with parameter t in [0, 1]."""
    t = max(0.0, min(1.0, float(t)))
    return Point2D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)


def is_close(a: Point2D, b: Point2D, tol: float = 1e-6) -> bool:
    """Return True when two points are within ``tol`` of each other."""
    return distance(a, b) <= abs(tol)


def signed_area(points: list[Point2D]) -> float:
    """Return the signed area of a polygon using the shoelace formula.

    Positive values indicate counter-clockwise winding,
    negative values indicate clockwise winding.
    """
    if len(points) < 3:
        return 0.0
    total = 0.0
    for i in range(len(points)):
        current = points[i]
        nxt = points[(i + 1) % len(points)]
        total += current.x * nxt.y - nxt.x * current.y
    return total * 0.5


def line_intersection(
    p1: Point2D,
    p2: Point2D,
    p3: Point2D,
    p4: Point2D,
) -> Point2D | None:
    """Return the intersection point of two infinite lines, or None if parallel."""
    denom = (p1.x - p2.x) * (p3.y - p4.y) - (p1.y - p2.y) * (p3.x - p4.x)
    if abs(denom) < 1e-9:
        return None
    t = ((p1.x - p3.x) * (p3.y - p4.y) - (p1.y - p3.y) * (p3.x - p4.x)) / denom
    return Point2D(p1.x + (p2.x - p1.x) * t, p1.y + (p2.y - p1.y) * t)


__all__ = [
    "Point2D",
    "Vector2D",
    "distance",
    "lerp",
    "is_close",
    "signed_area",
    "line_intersection",
]