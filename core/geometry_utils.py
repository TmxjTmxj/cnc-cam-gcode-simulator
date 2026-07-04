"""Shared geometry helpers for future CAM and simulation modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Point2D:
    """Two-dimensional point in millimeters."""

    x: float
    y: float
