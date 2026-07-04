"""Data structures shared by CAM generation and toolpath workflows."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CamParameters:
    """CAM parameters required for basic contour G-code generation."""

    tool_diameter: float
    spindle_speed: int
    feed_rate: int
    cutting_depth: float
    safe_height: float
    machining_mode: str = "车削模式"
    contour_direction: str = "自动"
    zero_origin: bool = True
    arc_output: str = "折线近似"
    layer_filter: str = "全部图层"
    cutter_compensation: str = "none"


@dataclass(frozen=True)
class ToolpathPoint:
    """One XY point in a generated two-dimensional contour path."""

    x: float
    y: float


@dataclass(frozen=True)
class ToolpathArc:
    """One circular interpolation move in DXF XY coordinates."""

    start: ToolpathPoint
    end: ToolpathPoint
    center: ToolpathPoint
    clockwise: bool


@dataclass(frozen=True)
class Toolpath:
    """One continuous contour path made of XY points."""

    points: list[ToolpathPoint] = field(default_factory=list)
    arcs: list[ToolpathArc] = field(default_factory=list)

    @property
    def is_machinable(self) -> bool:
        """Return whether the path has enough points for line cutting."""
        return len(self.points) >= 2 or bool(self.arcs)


@dataclass(frozen=True)
class GeneratedGCode:
    """Generated Fanuc-style G-code and source path statistics."""

    text: str
    line_count: int
    entity_count: int
    path_count: int
    machining_mode: str = "车削模式"
    zero_origin: bool = True
