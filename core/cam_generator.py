"""Basic CAM generator for converting DXF contours to Fanuc-style G-code."""

from __future__ import annotations

import logging
from math import ceil, cos, hypot, radians, sin

from core.constants import (
    ARC_DEGREE_STEP,
    ARC_OUTPUT_G2G3,
    CIRCLE_SEGMENT_COUNT,
    LINE_JOIN_TOLERANCE,
    MILLING_MODE,
    PLUNGE_FEED_RATE,
    TURNING_MODE,
)
from core.dxf_reader import DxfArc, DxfCircle, DxfLine, DxfReadResult
from core.toolpath import CamParameters, GeneratedGCode, Toolpath, ToolpathArc, ToolpathPoint

# 保留模块级名称以便向后兼容（测试中 `from core.cam_generator import MILLING_MODE` 仍可用）
logger = logging.getLogger(__name__)


class CamGenerator:
    """Generate simple two-dimensional contour machining G-code from DXF geometry."""

    def generate(self, geometry: DxfReadResult, parameters: CamParameters) -> GeneratedGCode:
        """Generate Fanuc-style G-code for supported DXF entities."""
        self._validate_parameters(parameters)
        source_geometry = geometry.filtered_by_layer(parameters.layer_filter)
        paths = self._build_toolpaths(source_geometry, parameters)
        paths = self._apply_zero_origin(paths, parameters)
        paths = [self._prepare_path(path, parameters) for path in paths]
        machinable_paths = [path for path in paths if path.is_machinable]
        if not machinable_paths:
            logger.error("CAM 生成失败: 未发现可生成刀路的图元")
            raise ValueError("未发现可生成刀路的图元")

        lines = self._program_header(parameters)
        for path in machinable_paths:
            lines.extend(self._path_to_gcode(path, parameters))
        lines.extend(self._program_footer(parameters))
        lines = self._standardize_program_lines(lines)

        return GeneratedGCode(
            text="\n".join(lines),
            line_count=len(lines),
            entity_count=source_geometry.entity_count,
            path_count=len(machinable_paths),
            machining_mode=parameters.machining_mode,
            zero_origin=parameters.zero_origin,
        )

    def _validate_parameters(self, parameters: CamParameters) -> None:
        """Validate CAM parameters before generating machine code."""
        if parameters.tool_diameter <= 0:
            raise ValueError("刀具直径必须大于 0")
        if parameters.spindle_speed <= 0:
            raise ValueError("主轴转速必须大于 0")
        if parameters.feed_rate <= 0:
            raise ValueError("进给速度必须大于 0")
        if parameters.cutting_depth >= parameters.safe_height:
            raise ValueError("切削深度必须低于安全高度")
        if parameters.machining_mode not in {MILLING_MODE, TURNING_MODE}:
            raise ValueError("加工模式无效")

    def _build_toolpaths(self, geometry: DxfReadResult, parameters: CamParameters) -> list[Toolpath]:
        """Convert supported DXF entities into simple contour paths."""
        paths: list[Toolpath] = []

        paths.extend(self._line_toolpaths(geometry.lines))
        for polyline in geometry.polylines:
            points = [ToolpathPoint(x, y) for x, y in polyline.points]
            if polyline.is_closed and points and points[0] != points[-1]:
                points.append(points[0])
            paths.append(Toolpath(points))
        if parameters.arc_output == ARC_OUTPUT_G2G3:
            for circle in geometry.circles:
                paths.append(Toolpath(arcs=self._circle_arcs(circle, parameters)))
            for arc in geometry.arcs:
                paths.append(Toolpath(arcs=[self._dxf_arc_to_toolpath_arc(arc, parameters)]))
        else:
            for circle in geometry.circles:
                paths.append(Toolpath(self._circle_points(circle)))
            for arc in geometry.arcs:
                paths.append(Toolpath(self._arc_points(arc)))

        return paths

    def _apply_zero_origin(self, paths: list[Toolpath], parameters: CamParameters) -> list[Toolpath]:
        """Apply mode-aware work-zero translation to source DXF geometry."""
        if not parameters.zero_origin:
            return paths

        source_paths = [
            path
            for path in paths
            if not (parameters.machining_mode == TURNING_MODE and self._is_turning_centerline(path))
        ]
        all_points = [
            point
            for path in source_paths
            for point in (
                path.points
                + [arc.start for arc in path.arcs]
                + [arc.end for arc in path.arcs]
                + [arc.center for arc in path.arcs]
            )
        ]
        if not all_points:
            return paths

        min_x = min(point.x for point in all_points)
        if parameters.machining_mode == TURNING_MODE:
            return [
                Toolpath(
                    points=[ToolpathPoint(point.x - min_x, point.y) for point in path.points],
                    arcs=[
                        ToolpathArc(
                            start=ToolpathPoint(arc.start.x - min_x, arc.start.y),
                            end=ToolpathPoint(arc.end.x - min_x, arc.end.y),
                            center=ToolpathPoint(arc.center.x - min_x, arc.center.y),
                            clockwise=arc.clockwise,
                        )
                        for arc in path.arcs
                    ],
                )
                for path in paths
            ]

        min_y = min(point.y for point in all_points)
        return [
            Toolpath(
                points=[ToolpathPoint(point.x - min_x, point.y - min_y) for point in path.points],
                arcs=[
                    ToolpathArc(
                        start=ToolpathPoint(arc.start.x - min_x, arc.start.y - min_y),
                        end=ToolpathPoint(arc.end.x - min_x, arc.end.y - min_y),
                        center=ToolpathPoint(arc.center.x - min_x, arc.center.y - min_y),
                        clockwise=arc.clockwise,
                    )
                    for arc in path.arcs
                ],
            )
            for path in paths
        ]

    def _prepare_path(self, path: Toolpath, parameters: CamParameters) -> Toolpath:
        """Apply direction and start-point optimization before G-code output."""
        if parameters.machining_mode == TURNING_MODE:
            if self._is_turning_centerline(path):
                return Toolpath()
            if path.arcs:
                return path
            return self._optimize_turning_start(path)
        if path.arcs:
            return path

        directed = self._apply_milling_direction(path, parameters.contour_direction)
        compensated = self._apply_milling_cutter_compensation(directed, parameters)
        return self._optimize_milling_start(compensated)

    def _apply_milling_direction(self, path: Toolpath, direction: str) -> Toolpath:
        """Reverse closed milling contours when the requested direction needs it."""
        if direction == "自动" or len(path.points) < 3:
            return path

        area = self._signed_area(path.points)
        points = list(path.points)
        if direction == "顺时针" and area > 0:
            points = list(reversed(points))
        elif direction == "逆时针" and area < 0:
            points = list(reversed(points))

        return Toolpath(self._normalize_closed_path(points))


    def _apply_milling_cutter_compensation(self, path: Toolpath, parameters: CamParameters) -> Toolpath:
        """Offset simple closed milling polylines by the selected tool radius."""
        side = self._cutter_compensation_side(parameters.cutter_compensation)
        if side is None or not self._is_closed_path(path.points) or len(path.points) < 4:
            return path

        radius = parameters.tool_diameter * 0.5
        if radius <= 0:
            return path

        contour = list(path.points[:-1])
        offset = radius if side == "left" else -radius
        compensated = self._offset_closed_polyline(contour, offset)
        if len(compensated) < 3:
            return path
        compensated.append(compensated[0])
        return Toolpath(compensated)

    def _cutter_compensation_side(self, value: str) -> str | None:
        """Normalize UI/API cutter compensation labels to left/right/none."""
        normalized = (value or "none").strip().lower()
        if normalized in {"left", "g41", "g41 left", "\u5de6\u8865\u507f"}:
            return "left"
        if normalized in {"right", "g42", "g42 right", "\u53f3\u8865\u507f"}:
            return "right"
        return None

    def _offset_closed_polyline(self, points: list[ToolpathPoint], offset: float) -> list[ToolpathPoint]:
        """Offset a non-self-intersecting closed polyline using adjacent offset-line intersections."""
        count = len(points)
        shifted_lines: list[tuple[ToolpathPoint, ToolpathPoint]] = []
        for index, start in enumerate(points):
            end = points[(index + 1) % count]
            dx = end.x - start.x
            dy = end.y - start.y
            length = hypot(dx, dy)
            if length <= LINE_JOIN_TOLERANCE:
                continue
            nx = -dy / length
            ny = dx / length
            shifted_lines.append((
                ToolpathPoint(start.x + nx * offset, start.y + ny * offset),
                ToolpathPoint(end.x + nx * offset, end.y + ny * offset),
            ))

        if len(shifted_lines) != count:
            return []

        compensated: list[ToolpathPoint] = []
        for index in range(count):
            previous_line = shifted_lines[index - 1]
            current_line = shifted_lines[index]
            compensated.append(self._line_intersection(previous_line[0], previous_line[1], current_line[0], current_line[1]))
        return compensated

    def _line_intersection(
        self,
        first_start: ToolpathPoint,
        first_end: ToolpathPoint,
        second_start: ToolpathPoint,
        second_end: ToolpathPoint,
    ) -> ToolpathPoint:
        """Return the intersection of two infinite 2D lines, falling back to the corner midpoint."""
        x1, y1 = first_start.x, first_start.y
        x2, y2 = first_end.x, first_end.y
        x3, y3 = second_start.x, second_start.y
        x4, y4 = second_end.x, second_end.y
        denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denominator) <= LINE_JOIN_TOLERANCE:
            return ToolpathPoint((first_end.x + second_start.x) * 0.5, (first_end.y + second_start.y) * 0.5)
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
        return ToolpathPoint(px, py)

    def _optimize_milling_start(self, path: Toolpath) -> Toolpath:
        """Use the point closest to work zero as the milling start point."""
        if len(path.points) < 2:
            return path
        if self._is_closed_path(path.points):
            return Toolpath(self._rotate_closed_path(path.points, self._closest_to_origin_index(path.points[:-1])))

        points = list(path.points)
        if self._distance_to_origin(points[-1]) < self._distance_to_origin(points[0]):
            points.reverse()
        return Toolpath(points)

    def _optimize_turning_start(self, path: Toolpath) -> Toolpath:
        """Prefer the largest source DXF X as the turning Z start."""
        if len(path.points) < 2:
            return path
        if self._is_closed_path(path.points):
            max_z_index = max(range(len(path.points) - 1), key=lambda index: path.points[index].x)
            return Toolpath(self._rotate_closed_path(path.points, max_z_index))

        points = list(path.points)
        if points[-1].x > points[0].x:
            points.reverse()
        return Toolpath(points)

    def _is_turning_centerline(self, path: Toolpath) -> bool:
        """Return whether a path is only a spindle centerline helper."""
        if path.arcs or not path.points:
            return False
        return all(abs(point.y) <= LINE_JOIN_TOLERANCE for point in path.points)

    def _signed_area(self, points: list[ToolpathPoint]) -> float:
        """Return polygon signed area; positive means counter-clockwise in XY."""
        if len(points) < 3:
            return 0.0
        area = 0.0
        for first, second in zip(points, points[1:]):
            area += first.x * second.y - second.x * first.y
        if not self._points_close(points[0], points[-1]):
            area += points[-1].x * points[0].y - points[0].x * points[-1].y
        return area / 2.0

    def _closest_to_origin_index(self, points: list[ToolpathPoint]) -> int:
        """Return the index of the point closest to X0/Y0."""
        return min(range(len(points)), key=lambda index: self._distance_to_origin(points[index]))

    def _distance_to_origin(self, point: ToolpathPoint) -> float:
        """Return XY distance from work zero."""
        return hypot(point.x, point.y)

    def _is_closed_path(self, points: list[ToolpathPoint]) -> bool:
        """Return whether the path starts and ends at the same point."""
        return len(points) >= 3 and self._points_close(points[0], points[-1])

    def _rotate_closed_path(self, points: list[ToolpathPoint], start_index: int) -> list[ToolpathPoint]:
        """Rotate a closed contour without changing its cutting direction."""
        contour = list(points[:-1]) if self._is_closed_path(points) else list(points)
        rotated = contour[start_index:] + contour[:start_index]
        rotated.append(rotated[0])
        return rotated

    def _line_toolpaths(self, lines: list[DxfLine]) -> list[Toolpath]:
        """Merge connectable LINE entities into continuous contour paths."""
        unused = [
            (
                ToolpathPoint(line.start_x, line.start_y),
                ToolpathPoint(line.end_x, line.end_y),
            )
            for line in lines
        ]
        paths: list[Toolpath] = []

        while unused:
            start, end = unused.pop(0)
            points = [start, end]

            changed = True
            while changed:
                changed = self._try_attach_line(points, unused)

            paths.append(Toolpath(self._normalize_closed_path(points)))

        return paths

    def _try_attach_line(
        self,
        points: list[ToolpathPoint],
        unused: list[tuple[ToolpathPoint, ToolpathPoint]],
    ) -> bool:
        """Attach the next matching segment to either end of the current path."""
        for index, (start, end) in enumerate(unused):
            if self._points_close(points[-1], start):
                points.append(end)
            elif self._points_close(points[-1], end):
                points.append(start)
            elif self._points_close(points[0], end):
                points.insert(0, start)
            elif self._points_close(points[0], start):
                points.insert(0, end)
            else:
                continue

            unused.pop(index)
            return True
        return False

    def _normalize_closed_path(self, points: list[ToolpathPoint]) -> list[ToolpathPoint]:
        """Snap nearly closed contours to an exact shared start/end point."""
        if len(points) >= 3 and self._points_close(points[0], points[-1]):
            return [*points[:-1], points[0]]
        return points

    def _points_close(self, first: ToolpathPoint, second: ToolpathPoint) -> bool:
        """Return whether two XY points are equivalent within line-join tolerance."""
        return (
            abs(first.x - second.x) <= LINE_JOIN_TOLERANCE
            and abs(first.y - second.y) <= LINE_JOIN_TOLERANCE
        )

    def _circle_points(self, circle: DxfCircle) -> list[ToolpathPoint]:
        """Approximate a circle with a 72-segment closed polyline."""
        points: list[ToolpathPoint] = []
        for index in range(CIRCLE_SEGMENT_COUNT + 1):
            angle = radians(360.0 * index / CIRCLE_SEGMENT_COUNT)
            points.append(
                ToolpathPoint(
                    x=circle.center_x + circle.radius * cos(angle),
                    y=circle.center_y + circle.radius * sin(angle),
                )
            )
        return points

    def _arc_points(self, arc: DxfArc) -> list[ToolpathPoint]:
        """Approximate an arc with G1 polyline points at about 5-degree spacing."""
        start = arc.start_angle
        end = arc.end_angle
        if end < start:
            end += 360.0
        span = max(end - start, ARC_DEGREE_STEP)
        steps = max(1, ceil(span / ARC_DEGREE_STEP))

        points: list[ToolpathPoint] = []
        for index in range(steps + 1):
            angle = radians(start + (end - start) * index / steps)
            points.append(
                ToolpathPoint(
                    x=arc.center_x + arc.radius * cos(angle),
                    y=arc.center_y + arc.radius * sin(angle),
                )
            )
        return points

    def _circle_arcs(self, circle: DxfCircle, parameters: CamParameters) -> list[ToolpathArc]:
        """Represent a full circle as two half-circle G2/G3 moves."""
        center = ToolpathPoint(circle.center_x, circle.center_y)
        right = ToolpathPoint(circle.center_x + circle.radius, circle.center_y)
        left = ToolpathPoint(circle.center_x - circle.radius, circle.center_y)
        clockwise = parameters.contour_direction != "逆时针"
        return [
            ToolpathArc(start=right, end=left, center=center, clockwise=clockwise),
            ToolpathArc(start=left, end=right, center=center, clockwise=clockwise),
        ]

    def _dxf_arc_to_toolpath_arc(self, arc: DxfArc, parameters: CamParameters) -> ToolpathArc:
        """Convert a DXF ARC to one circular interpolation move."""
        start_angle = radians(arc.start_angle)
        end_angle = radians(arc.end_angle)
        start = ToolpathPoint(
            arc.center_x + arc.radius * cos(start_angle),
            arc.center_y + arc.radius * sin(start_angle),
        )
        end = ToolpathPoint(
            arc.center_x + arc.radius * cos(end_angle),
            arc.center_y + arc.radius * sin(end_angle),
        )
        clockwise = parameters.contour_direction == "顺时针"
        if clockwise:
            start, end = end, start
        return ToolpathArc(
            start=start,
            end=end,
            center=ToolpathPoint(arc.center_x, arc.center_y),
            clockwise=clockwise,
        )

    def _program_header(self, parameters: CamParameters) -> list[str]:
        """Return standard program header lines."""
        if parameters.machining_mode == TURNING_MODE:
            return [
                "%",
                "O1001",
                "(GENERATED BY CNC CAM SIMULATOR - TURNING)",
                "G21",
                "G90",
                "G18",
                "G40",
                "G54",
                "G94",
                f"M3 S{parameters.spindle_speed}",
            ]

        return [
            "%",
            "O1000",
            "(GENERATED BY CNC CAM SIMULATOR - MILLING)",
            "G21",
            "G90",
            "G17",
            "G40",
            "G54",
            "G94",
            f"G0 Z{self._fmt(parameters.safe_height)}",
            f"M3 S{parameters.spindle_speed}",
        ]

    def _path_to_gcode(self, path: Toolpath, parameters: CamParameters) -> list[str]:
        """Convert one contour path to rapid, plunge, cut, and retract commands."""
        if parameters.machining_mode == TURNING_MODE:
            return self._turning_path_to_gcode(path, parameters)

        return self._milling_path_to_gcode(path, parameters)

    def _milling_path_to_gcode(self, path: Toolpath, parameters: CamParameters) -> list[str]:
        """Convert one milling contour to rapid, plunge, cut, and retract commands."""
        if path.arcs:
            return self._milling_arc_path_to_gcode(path, parameters)

        first = path.points[0]
        lines = [
            "",
            f"G0 X{self._fmt(first.x)} Y{self._fmt(first.y)}",
            f"G1 Z{self._fmt(parameters.cutting_depth)} F{PLUNGE_FEED_RATE}",
        ]

        for index, point in enumerate(path.points[1:]):
            feed = f" F{parameters.feed_rate}" if index == 0 else ""
            lines.append(f"G1 X{self._fmt(point.x)} Y{self._fmt(point.y)}{feed}")

        lines.append(f"G0 Z{self._fmt(parameters.safe_height)}")
        return lines

    def _milling_arc_path_to_gcode(self, path: Toolpath, parameters: CamParameters) -> list[str]:
        """Convert one milling arc path to G17 G2/G3 commands with I/J offsets."""
        first = path.arcs[0].start
        lines = [
            "",
            f"G0 X{self._fmt(first.x)} Y{self._fmt(first.y)}",
            f"G1 Z{self._fmt(parameters.cutting_depth)} F{PLUNGE_FEED_RATE}",
        ]

        for index, arc in enumerate(path.arcs):
            feed = f" F{parameters.feed_rate}" if index == 0 else ""
            lines.append(self._arc_command_xy(arc, feed))

        lines.append(f"G0 Z{self._fmt(parameters.safe_height)}")
        return lines

    def _turning_path_to_gcode(self, path: Toolpath, parameters: CamParameters) -> list[str]:
        """Convert a turning profile to X/Z G-code.

        In turning mode, source DXF is interpreted as a side profile:
        source DXF X -> machine Z, source DXF Y radius -> machine X diameter.
        Milling mode keeps the ordinary source DXF X/Y -> machine X/Y mapping.
        """
        if path.arcs:
            return self._turning_arc_path_to_gcode(path, parameters)

        profile_points = self._turning_profile_points(path.points)
        if len(profile_points) < 2:
            return []

        first = profile_points[0]
        safe_x = first.x + parameters.safe_height
        lines = [
            "",
            f"G0 X{self._fmt(safe_x)} Z{self._fmt(first.y)}",
            f"G1 X{self._fmt(first.x)} Z{self._fmt(first.y)} F{parameters.feed_rate}",
        ]

        for point in profile_points[1:]:
            lines.append(f"G1 X{self._fmt(point.x)} Z{self._fmt(point.y)}")

        last = profile_points[-1]
        lines.append(f"G0 X{self._fmt(last.x + parameters.safe_height)} Z{self._fmt(last.y)}")
        return lines

    def _turning_arc_path_to_gcode(self, path: Toolpath, parameters: CamParameters) -> list[str]:
        """Convert one turning arc path to G18 G2/G3 commands with I/K offsets."""
        first = self._turning_machine_point(path.arcs[0].start)
        safe_x = first.x + parameters.safe_height
        lines = [
            "",
            f"G0 X{self._fmt(safe_x)} Z{self._fmt(first.y)}",
            f"G1 X{self._fmt(first.x)} Z{self._fmt(first.y)} F{parameters.feed_rate}",
        ]

        for arc in path.arcs:
            lines.append(self._turning_arc_command_xz(arc))

        last = self._turning_machine_point(path.arcs[-1].end)
        lines.append(f"G0 X{self._fmt(last.x + parameters.safe_height)} Z{self._fmt(last.y)}")
        return lines

    def _turning_profile_points(self, points: list[ToolpathPoint]) -> list[ToolpathPoint]:
        """Return turning machine X/Z points, collapsing mirrored duplicate geometry."""
        source_points = self._turning_source_profile_points(points)
        machine_points = [self._turning_machine_point(point) for point in source_points]
        collapsed: list[ToolpathPoint] = []
        for point in machine_points:
            if collapsed and self._points_close(collapsed[-1], point):
                continue
            collapsed.append(point)
        if len(collapsed) >= 2 and self._points_close(collapsed[0], collapsed[-1]):
            collapsed.pop()
        return collapsed

    def _turning_source_profile_points(self, points: list[ToolpathPoint]) -> list[ToolpathPoint]:
        """Extract the machinable upper profile from a symmetric turning outline."""
        if not points:
            return []
        has_positive = any(point.y > LINE_JOIN_TOLERANCE for point in points)
        has_negative = any(point.y < -LINE_JOIN_TOLERANCE for point in points)
        if not (has_positive and has_negative):
            return points

        contour = list(points[:-1]) if self._is_closed_path(points) else list(points)
        upper_runs: list[list[ToolpathPoint]] = []
        current_run: list[ToolpathPoint] = []
        for point in contour + contour:
            if point.y >= -LINE_JOIN_TOLERANCE:
                if not current_run or not self._points_close(current_run[-1], point):
                    current_run.append(point)
                continue

            if len(current_run) >= 2:
                upper_runs.append(current_run)
            current_run = []

        if len(current_run) >= 2:
            upper_runs.append(current_run)

        if not upper_runs:
            return points

        upper = max(upper_runs, key=len)
        if len(upper) > len(contour):
            upper = upper[: len(contour)]
        if len(upper) < 2:
            return points
        if upper[0].x < upper[-1].x:
            upper = list(reversed(upper))
        return upper

    def _turning_machine_point(self, point: ToolpathPoint) -> ToolpathPoint:
        """Map source DXF profile coordinates into standard turning X/Z coordinates."""
        return ToolpathPoint(
            x=abs(point.y) * 2.0,
            y=point.x,
        )

    def _turning_radius_point(self, point: ToolpathPoint) -> ToolpathPoint:
        """Map source DXF profile coordinates into turning radius/Z coordinates."""
        return ToolpathPoint(
            x=abs(point.y),
            y=point.x,
        )

    def _arc_command_xy(self, arc: ToolpathArc, feed: str) -> str:
        """Format a G17 XY circular interpolation command."""
        code = "G2" if arc.clockwise else "G3"
        i = arc.center.x - arc.start.x
        j = arc.center.y - arc.start.y
        return (
            f"{code} X{self._fmt(arc.end.x)} Y{self._fmt(arc.end.y)} "
            f"I{self._fmt(i)} J{self._fmt(j)}{feed}"
        )

    def _arc_command_xz(self, arc: ToolpathArc, feed: str) -> str:
        """Format a G18 XZ circular interpolation command."""
        code = "G2" if arc.clockwise else "G3"
        i = arc.center.x - arc.start.x
        k = arc.center.y - arc.start.y
        return (
            f"{code} X{self._fmt(arc.end.x)} Z{self._fmt(arc.end.y)} "
            f"I{self._fmt(i)} K{self._fmt(k)}{feed}"
        )

    def _turning_arc_command_xz(self, arc: ToolpathArc) -> str:
        """Format a G18 turning arc with diameter X output and radius I/K offsets."""
        end = self._turning_machine_point(arc.end)

        # Fanuc-style turning outputs X as diameter, but G18 I/K arc-center
        # offsets stay in the programmed radius coordinate system: I is radial X,
        # K is spindle Z. Keep this mapping explicit to avoid doubling I.
        start_radius = self._turning_radius_point(arc.start)
        center_radius = self._turning_radius_point(arc.center)
        code = "G3" if arc.clockwise else "G2"
        i = center_radius.x - start_radius.x
        k = center_radius.y - start_radius.y
        return (
            f"{code} X{self._fmt(end.x)} Z{self._fmt(end.y)} "
            f"I{self._fmt(i)} K{self._fmt(k)}"
        )

    def _program_footer(self, parameters: CamParameters) -> list[str]:
        """Return standard program footer lines."""
        if parameters.machining_mode == TURNING_MODE:
            return [
                "",
                "M5",
                "G0 X0 Z0",
                "M30",
                "%",
            ]

        return [
            "",
            "M5",
            "G0 X0 Y0",
            "M30",
            "%",
        ]

    def _fmt(self, value: float) -> str:
        """Format numeric G-code values without noisy trailing zeros."""
        formatted = f"{value:.3f}".rstrip("0").rstrip(".")
        return formatted if formatted else "0"

    def _standardize_program_lines(self, lines: list[str]) -> list[str]:
        """Add standard N line numbers to executable G-code blocks."""
        numbered: list[str] = []
        sequence = 10
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped == "%" or stripped.startswith(("(", "O")):
                numbered.append(line)
                continue
            numbered.append(f"N{sequence:04d} {stripped}")
            sequence += 10
        return numbered
