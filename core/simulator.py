"""G0/G1/G2/G3 two-dimensional path simulation engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from math import atan2, cos, hypot, pi, sin, sqrt

from core.constants import ARC_RADIUS_TOLERANCE
from core.gcode_parser import GCodeCommand, GCodeParseResult

# 保留模块级名称以便向后兼容
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MachinePosition:
    """Current machine position in millimeters."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class ToolpathSegment:
    """A drawable two-dimensional linear or circular path segment."""

    start_x: float
    start_y: float
    end_x: float
    end_y: float
    move_type: str
    line_number: int
    raw_line: str
    points: list[tuple[float, float]] = field(default_factory=list)
    arc_length: float | None = None
    command: GCodeCommand | None = None
    machine_start: MachinePosition | None = None
    machine_end: MachinePosition | None = None
    warning: str | None = None

    @property
    def length(self) -> float:
        """Return the display-plane length of this segment in millimeters."""
        if self.arc_length is not None:
            return self.arc_length
        return hypot(self.end_x - self.start_x, self.end_y - self.start_y)


@dataclass(frozen=True)
class SimulationResult:
    """Computed G-code simulation data used by the GUI and canvas."""

    segments: list[ToolpathSegment] = field(default_factory=list)
    final_position: MachinePosition = field(default_factory=MachinePosition)
    total_path_length: float = 0.0
    plane: str = "XY"
    warnings: list[str] = field(default_factory=list)


class GCodeSimulator:
    """Convert parsed motion commands into drawable two-dimensional path segments."""

    def simulate(
        self,
        parse_result: GCodeParseResult,
        plane: str = "XY",
        *,
        honor_program_plane: bool = True,
    ) -> SimulationResult:
        """Generate drawable line segments from a parsed G-code result."""
        position = MachinePosition()
        segments: list[ToolpathSegment] = []
        warnings: list[str] = []
        normalized_plane = "XZ" if plane == "XZ" else "XY"

        for command in parse_result.commands:
            if command.command == "G17":
                if honor_program_plane:
                    normalized_plane = "XY"
                continue
            if command.command == "G18":
                if honor_program_plane:
                    normalized_plane = "XZ"
                continue
            if command.command not in {"G0", "G1", "G2", "G3"}:
                continue

            next_position = self._next_position(position, command)
            if command.command in {"G2", "G3"}:
                arc_segment = self._arc_segment(position, next_position, command, normalized_plane)
                if arc_segment is not None:
                    if arc_segment.warning:
                        warnings.append(arc_segment.warning)
                        logger.warning("仿真告警: %s", arc_segment.warning)
                    segments.append(arc_segment)
                elif self._has_plane_motion(position, next_position, normalized_plane):
                    warning = f"Line {command.line_number}: invalid arc, rendered as linear move"
                    warnings.append(warning)
                    logger.warning("仿真告警: %s", warning)
                    segments.append(self._linear_segment(position, next_position, command, normalized_plane, warning))
            elif self._has_plane_motion(position, next_position, normalized_plane):
                segments.append(self._linear_segment(position, next_position, command, normalized_plane))
            position = next_position

        return SimulationResult(
            segments=segments,
            final_position=position,
            total_path_length=sum(segment.length for segment in segments),
            plane=normalized_plane,
            warnings=warnings,
        )

    def reset(self) -> SimulationResult:
        """Return an empty simulation result at the machine origin."""
        return SimulationResult()

    def _next_position(self, position: MachinePosition, command: GCodeCommand) -> MachinePosition:
        """Apply absolute G90 or incremental G91 coordinates, inheriting omitted axes."""
        if command.distance_mode == "incremental":
            return MachinePosition(
                x=position.x + (command.x or 0.0),
                y=position.y + (command.y or 0.0),
                z=position.z + (command.z or 0.0),
            )
        return MachinePosition(
            x=command.x if command.x is not None else position.x,
            y=command.y if command.y is not None else position.y,
            z=command.z if command.z is not None else position.z,
        )

    def _linear_segment(
        self,
        start: MachinePosition,
        end: MachinePosition,
        command: GCodeCommand,
        plane: str,
        warning: str | None = None,
    ) -> ToolpathSegment:
        start_x, start_y = self._display_point(start, plane)
        end_x, end_y = self._display_point(end, plane)
        return ToolpathSegment(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            move_type=command.move_type,
            line_number=command.line_number,
            raw_line=command.raw_line,
            command=command,
            machine_start=start,
            machine_end=end,
            warning=warning,
        )

    def _has_plane_motion(self, start: MachinePosition, end: MachinePosition, plane: str) -> bool:
        """Return whether the command creates a visible segment in the selected plane."""
        if plane == "XZ":
            return start.x != end.x or start.z != end.z
        return start.x != end.x or start.y != end.y

    def _display_point(self, position: MachinePosition, plane: str) -> tuple[float, float]:
        """Map machine coordinates into the current drawing plane."""
        if plane == "XZ":
            return position.z, position.x
        return position.x, position.y

    def _arc_segment(
        self,
        start: MachinePosition,
        end: MachinePosition,
        command: GCodeCommand,
        plane: str,
    ) -> ToolpathSegment | None:
        """Convert one G2/G3 command into sampled display points and arc length."""
        arc_geometry = self._arc_geometry(start, end, command, plane)
        if arc_geometry is None:
            return None
        center_x, center_y, start_x, start_y, end_x, end_y = arc_geometry
        radius = hypot(start_x - center_x, start_y - center_y)
        radius_end = hypot(end_x - center_x, end_y - center_y)
        if radius <= 0:
            return None

        warning = None
        if abs(radius - radius_end) > ARC_RADIUS_TOLERANCE:
            warning = (
                f"Line {command.line_number}: arc radius mismatch "
                f"start={radius:.3f}, end={radius_end:.3f}; rendered as linear move"
            )
            return self._linear_segment(start, end, command, plane, warning)

        clockwise = command.command == "G2"
        sampled_points, sweep = self._sample_arc_points(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            clockwise=clockwise,
        )
        if plane == "XZ":
            sampled_points = [(point_y, point_x) for point_x, point_y in sampled_points]
        display_start_x, display_start_y = self._display_point(start, plane)
        display_end_x, display_end_y = self._display_point(end, plane)
        return ToolpathSegment(
            start_x=display_start_x,
            start_y=display_start_y,
            end_x=display_end_x,
            end_y=display_end_y,
            move_type=command.move_type,
            line_number=command.line_number,
            raw_line=command.raw_line,
            points=sampled_points,
            arc_length=radius * sweep,
            command=command,
            machine_start=start,
            machine_end=end,
            warning=warning,
        )

    def _arc_geometry(
        self,
        start: MachinePosition,
        end: MachinePosition,
        command: GCodeCommand,
        plane: str,
    ) -> tuple[float, float, float, float, float, float] | None:
        """Return center/start/end coordinates in the active interpolation plane."""
        if plane == "XZ":
            start_x, start_y = start.x, start.z
            end_x, end_y = end.x, end.z
            if command.i is not None and command.k is not None:
                return start.x + command.i, start.z + command.k, start_x, start_y, end_x, end_y
        else:
            start_x, start_y = start.x, start.y
            end_x, end_y = end.x, end.y
            if command.i is not None and command.j is not None:
                return start.x + command.i, start.y + command.j, start_x, start_y, end_x, end_y
        if command.r is not None:
            center = self._center_from_radius(start_x, start_y, end_x, end_y, command.r, command.command == "G2")
            if center is not None:
                return center[0], center[1], start_x, start_y, end_x, end_y
        return None

    def _center_from_radius(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        radius: float,
        clockwise: bool,
    ) -> tuple[float, float] | None:
        """Infer arc center from start/end/R using Fanuc-style short/long arc sign."""
        chord_x = end_x - start_x
        chord_y = end_y - start_y
        chord = hypot(chord_x, chord_y)
        abs_radius = abs(radius)
        if chord <= 0 or abs_radius < chord / 2:
            return None
        mid_x = (start_x + end_x) * 0.5
        mid_y = (start_y + end_y) * 0.5
        height = sqrt(max(abs_radius * abs_radius - (chord * 0.5) ** 2, 0.0))
        normal_x = -chord_y / chord
        normal_y = chord_x / chord
        if clockwise == (radius >= 0):
            normal_x = -normal_x
            normal_y = -normal_y
        return mid_x + normal_x * height, mid_y + normal_y * height

    def _sample_arc_points(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        center_x: float,
        center_y: float,
        radius: float,
        clockwise: bool,
    ) -> tuple[list[tuple[float, float]], float]:
        """Sample a clockwise or counter-clockwise arc, correctly handling wrap."""
        start_angle = atan2(start_y - center_y, start_x - center_x)
        end_angle = atan2(end_y - center_y, end_x - center_x)
        if clockwise:
            sweep = start_angle - end_angle
            if sweep <= 0:
                sweep += 2 * pi
            signed_sweep = -sweep
        else:
            sweep = end_angle - start_angle
            if sweep <= 0:
                sweep += 2 * pi
            signed_sweep = sweep

        steps = max(16, int(sweep / (pi / 36)))
        points: list[tuple[float, float]] = []
        for index in range(steps + 1):
            angle = start_angle + signed_sweep * index / steps
            points.append((center_x + radius * cos(angle), center_y + radius * sin(angle)))
        return points, sweep
