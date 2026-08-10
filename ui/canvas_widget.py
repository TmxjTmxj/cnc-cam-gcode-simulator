"""Matplotlib based two-dimensional simulation canvas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from core.dxf_reader import DxfArc, DxfReadResult
from core.simulator import SimulationResult, ToolpathSegment

import matplotlib
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Circle


def configure_matplotlib_chinese_font() -> str | None:
    """Configure matplotlib to use a common Chinese font when available."""
    preferred_fonts = ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC")
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    selected_font = next((font for font in preferred_fonts if font in available_fonts), None)
    if selected_font:
        matplotlib.rcParams["font.sans-serif"] = [selected_font, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    return selected_font


CHINESE_FONT = configure_matplotlib_chinese_font()
PLOT_LAYOUT = {"left": 0.105, "right": 0.965, "bottom": 0.135, "top": 0.875}
WELCOME_LAYOUT = {"left": 0.0, "right": 1.0, "bottom": 0.0, "top": 1.0}
DEFAULT_XLIM = (-10.0, 100.0)
DEFAULT_YLIM = (-10.0, 80.0)
ZOOM_IN_FACTOR = 0.82
ZOOM_OUT_FACTOR = 1.22


class SimulationCanvasWidget(QWidget):
    """Two-dimensional plotting area reserved for G-code and CAM paths."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the plotting canvas and draw its initial coordinate system."""
        super().__init__(parent)
        self._figure = Figure(figsize=(6, 4), dpi=100, facecolor="#F4F6F8")
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.updateGeometry()
        self._axis = self._figure.add_subplot(111)
        self._home_xlim = DEFAULT_XLIM
        self._home_ylim = DEFAULT_YLIM
        self._drag_start: tuple[float, float, tuple[float, float], tuple[float, float]] | None = None
        self._current_marker = None
        self._current_annotation = None
        self._latest_plane = "XY"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._build_welcome_card()
        self._connect_canvas_events()
        self.reset_view()

    def draw_toolpath(self, result: SimulationResult) -> None:
        """Draw simulated linear and circular toolpath segments on the existing canvas."""
        self._hide_welcome_card()
        self._current_marker = None
        self._current_annotation = None
        self._latest_plane = result.plane
        is_turning = result.plane == "XZ"
        self._prepare_axis(
            title="二维车削回转体截面 / G代码仿真路径" if is_turning else "二维铣削 G代码 / CAM 仿真路径",
            x_label="Z / mm" if is_turning else "X / mm",
            y_label="X / mm" if is_turning else "Y / mm",
        )
        rapid_segments = [segment for segment in result.segments if segment.move_type == "rapid"]
        linear_segments = [segment for segment in result.segments if segment.move_type == "linear"]
        arc_segments = [segment for segment in result.segments if segment.move_type == "arc"]

        self._draw_segments(rapid_segments, "#808890", "--", "G0 快速移动", result.plane)
        self._draw_segments(linear_segments, "#4682B4", "-", "G1 切削路径", result.plane)
        self._draw_arc_segments(arc_segments, result.plane)
        if is_turning:
            self._draw_turning_mirror(linear_segments, arc_segments)
        self._draw_start_end_markers(result.segments, result.plane)
        self._fit_to_segments(result.segments, result.plane)
        self._remember_home_view()

        if result.segments:
            self._place_legend_outside()
        self._canvas.draw_idle()

    def draw_dxf_geometry(self, result: DxfReadResult) -> None:
        """Draw supported DXF geometry on the existing canvas."""
        self._hide_welcome_card()
        self._prepare_axis(title="二维 DXF 图纸预览", y_label="Y / mm")
        self._draw_dxf_lines(result)
        self._draw_dxf_circles(result)
        self._draw_dxf_arcs(result)
        self._draw_dxf_polylines(result)
        self._fit_to_bounds(result.bounds)
        self._remember_home_view()

        if result.entity_count:
            self._place_legend_outside()
        self._canvas.draw_idle()

    def reset_view(self) -> None:
        """Reset the canvas to a clean welcome state without plot overlap."""
        self._prepare_welcome_surface()
        self._remember_home_view()
        self._show_welcome_card()
        self._canvas.draw_idle()

    def zoom_in(self) -> None:
        """Zoom into the current view without changing plot layout."""
        self._zoom_about_center(ZOOM_IN_FACTOR)

    def zoom_out(self) -> None:
        """Zoom out from the current view without changing plot layout."""
        self._zoom_about_center(ZOOM_OUT_FACTOR)

    def fit_to_content(self) -> None:
        """Restore the latest automatically fitted data view."""
        self._axis.set_xlim(*self._home_xlim)
        self._axis.set_ylim(*self._home_ylim)
        self._canvas.draw_idle()

    def set_simulation_position(
        self,
        x: float,
        y: float,
        z: float,
        progress: float | None = None,
        plane: str | None = None,
    ) -> None:
        """Show the current cutter position on the 2D simulation canvas."""
        active_plane = plane or self._latest_plane
        if active_plane == "XZ":
            plot_x, plot_y = z, x / 2.0
            label = f"X{x:.3f} Z{z:.3f}"
        else:
            plot_x, plot_y = x, y
            label = f"X{x:.3f} Y{y:.3f} Z{z:.3f}"

        if self._current_marker is None:
            self._current_marker = self._axis.scatter(
                [plot_x],
                [plot_y],
                s=86,
                color="#B8860B",
                edgecolors="#FFFFFF",
                linewidths=1.2,
                zorder=8,
                label="Current tool",
            )
            self._current_annotation = self._axis.annotate(
                label,
                xy=(plot_x, plot_y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=8,
                color="#1A1E22",
                bbox={"boxstyle": "round,pad=0.25", "fc": "#FFFFFF", "ec": "#B8860B", "alpha": 0.92},
                zorder=9,
            )
        else:
            self._current_marker.set_offsets([[plot_x, plot_y]])
            if self._current_annotation is not None:
                self._current_annotation.xy = (plot_x, plot_y)
                self._current_annotation.set_text(label)
        self._canvas.draw_idle()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Keep the welcome card centered over the plotting surface."""
        super().resizeEvent(event)
        self._position_welcome_card()

    def _prepare_axis(
        self,
        title: str = "二维 G代码 / CAM 仿真路径",
        x_label: str = "X / mm",
        y_label: str = "Y / mm",
    ) -> None:
        """Clear the axis and restore the standard machining grid."""
        self._axis.clear()
        self._axis.set_axis_on()
        self._figure.subplots_adjust(**PLOT_LAYOUT)
        self._axis.set_facecolor("#FFFFFF")
        self._axis.set_title(title, pad=8, fontsize=12, fontweight="bold", color="#1A1E22")
        self._axis.set_xlabel(x_label)
        self._axis.set_ylabel(y_label)
        self._axis.set_aspect("auto")
        self._axis.grid(True, which="major", linestyle="-", linewidth=0.6, color="#C8CED4", alpha=0.9)
        self._axis.minorticks_on()
        self._axis.grid(True, which="minor", linestyle=":", linewidth=0.4, color="#DDE1E5", alpha=0.8)
        self._axis.axhline(0, color="#808890", linewidth=1.0)
        self._axis.axvline(0, color="#808890", linewidth=1.0)
        self._axis.tick_params(colors="#7A828A", labelsize=9)
        self._axis.xaxis.label.set_color("#4A5058")
        self._axis.yaxis.label.set_color("#4A5058")
        for spine in self._axis.spines.values():
            spine.set_color("#B0B8C0")
            spine.set_linewidth(0.8)

    def _prepare_welcome_surface(self) -> None:
        """Show a quiet blank plotting surface behind the Qt welcome card."""
        self._axis.clear()
        self._figure.subplots_adjust(**WELCOME_LAYOUT)
        self._figure.set_facecolor("#F4F6F8")
        self._axis.set_facecolor("#F4F6F8")
        self._axis.set_axis_off()
        self._axis.set_xlim(0, 1)
        self._axis.set_ylim(0, 1)

    def _place_legend_outside(self) -> None:
        """Place the legend inside the plot so the canvas keeps its full working area."""
        self._figure.subplots_adjust(**PLOT_LAYOUT)
        self._axis.legend(
            loc="upper right",
            borderaxespad=0.35,
            framealpha=0.88,
            fancybox=True,
            edgecolor="#B0B8C0",
            facecolor="#FFFFFF",
            fontsize=8,
            labelcolor="#1A1E22",
        )

    def _build_welcome_card(self) -> None:
        """Create the Qt welcome card used before data is loaded."""
        self._welcome_card = QFrame(self)
        self._welcome_card.setObjectName("welcomeCard")
        shadow = QGraphicsDropShadowEffect(self._welcome_card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(70, 130, 180, 35))
        self._welcome_card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._welcome_card)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        title = QLabel("CNC CAM 与 G代码仿真分析软件", self._welcome_card)
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("二维车削 / 铣削 CAM 平台", self._welcome_card)
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        feature_grid = QGridLayout()
        feature_grid.setHorizontalSpacing(22)
        feature_grid.setVerticalSpacing(8)
        features = ["DXF导入", "车削CAM", "铣削CAM", "G代码生成", "G代码仿真", "G2/G3圆弧", "EXE部署"]
        for index, feature in enumerate(features):
            label = QLabel(feature, self._welcome_card)
            label.setObjectName("welcomeFeature")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            feature_grid.addWidget(label, index // 3, index % 3)
        layout.addLayout(feature_grid)

        hint = QLabel("点击“导入DXF”开始", self._welcome_card)
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self._position_welcome_card()

    def _show_welcome_card(self) -> None:
        """Show the welcome card above the empty plot."""
        self._position_welcome_card()
        self._welcome_card.show()
        self._welcome_card.raise_()

    def _hide_welcome_card(self) -> None:
        """Hide the welcome card when real drawing content is available."""
        self._welcome_card.hide()

    def _position_welcome_card(self) -> None:
        """Center the welcome card and keep it within the canvas bounds."""
        width = min(620, max(360, self.width() - 140))
        height = min(270, max(220, self.height() - 130))
        x = max(20, (self.width() - width) // 2)
        y = max(20, (self.height() - height) // 2)
        self._welcome_card.setGeometry(x, y, width, height)

    def _connect_canvas_events(self) -> None:
        """Enable mouse wheel zoom, drag panning, and double-click fit."""
        self._canvas.mpl_connect("scroll_event", self._on_scroll)
        self._canvas.mpl_connect("button_press_event", self._on_button_press)
        self._canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self._canvas.mpl_connect("button_release_event", self._on_button_release)

    def _on_scroll(self, event) -> None:  # type: ignore[no-untyped-def]
        """Zoom around the cursor position when the mouse wheel is used."""
        if event.inaxes != self._axis:
            return
        factor = ZOOM_IN_FACTOR if event.step > 0 else ZOOM_OUT_FACTOR
        center_x = event.xdata if event.xdata is not None else sum(self._axis.get_xlim()) / 2
        center_y = event.ydata if event.ydata is not None else sum(self._axis.get_ylim()) / 2
        self._apply_zoom(center_x, center_y, factor)

    def _on_button_press(self, event) -> None:  # type: ignore[no-untyped-def]
        """Start panning or fit the plot on double-click."""
        if event.inaxes != self._axis:
            return
        if getattr(event, "dblclick", False):
            self.fit_to_content()
            return
        if event.button not in (1, 2):
            return
        self._drag_start = (event.x, event.y, self._axis.get_xlim(), self._axis.get_ylim())

    def _on_mouse_move(self, event) -> None:  # type: ignore[no-untyped-def]
        """Pan the plot while the primary mouse button is dragged."""
        if self._drag_start is None or event.inaxes != self._axis:
            return
        start_x, start_y, start_xlim, start_ylim = self._drag_start
        bbox = self._axis.bbox
        if bbox.width <= 0 or bbox.height <= 0:
            return

        delta_x = (event.x - start_x) * (start_xlim[1] - start_xlim[0]) / bbox.width
        delta_y = (event.y - start_y) * (start_ylim[1] - start_ylim[0]) / bbox.height
        self._axis.set_xlim(start_xlim[0] - delta_x, start_xlim[1] - delta_x)
        self._axis.set_ylim(start_ylim[0] - delta_y, start_ylim[1] - delta_y)
        self._canvas.draw_idle()

    def _on_button_release(self, _event) -> None:  # type: ignore[no-untyped-def]
        """End a panning gesture."""
        self._drag_start = None

    def _zoom_about_center(self, factor: float) -> None:
        """Zoom around the current axes center."""
        xlim = self._axis.get_xlim()
        ylim = self._axis.get_ylim()
        self._apply_zoom(sum(xlim) / 2, sum(ylim) / 2, factor)

    def _apply_zoom(self, center_x: float, center_y: float, factor: float) -> None:
        """Apply a data-space zoom factor around one point."""
        xlim = self._axis.get_xlim()
        ylim = self._axis.get_ylim()
        left = center_x - (center_x - xlim[0]) * factor
        right = center_x + (xlim[1] - center_x) * factor
        bottom = center_y - (center_y - ylim[0]) * factor
        top = center_y + (ylim[1] - center_y) * factor
        self._axis.set_xlim(left, right)
        self._axis.set_ylim(bottom, top)
        self._canvas.draw_idle()

    def _remember_home_view(self) -> None:
        """Store the current auto-fit limits for toolbar reset and double-click."""
        self._home_xlim = self._axis.get_xlim()
        self._home_ylim = self._axis.get_ylim()

    def _draw_segments(
        self,
        segments: list[ToolpathSegment],
        color: str,
        linestyle: str,
        label: str,
        plane: str = "XY",
        *,
        mirrored: bool = False,
        alpha: float | None = None,
    ) -> None:
        """Draw a batch of path segments with consistent styling."""
        line_segments = [
            self._segment_plot_points(segment, plane, mirrored=mirrored)
            for segment in segments
        ]
        self._add_line_collection(
            line_segments,
            color=color,
            linestyle=linestyle,
            linewidth=2.35 if linestyle == "-" else 1.65,
            alpha=alpha if alpha is not None else (0.96 if linestyle == "-" else 0.74),
            label=label,
        )

    def _draw_arc_segments(
        self,
        segments: list[ToolpathSegment],
        plane: str = "XY",
        *,
        mirrored: bool = False,
        alpha: float = 0.95,
        label: str = "G2/G3 arc",
    ) -> None:
        """Draw sampled G2/G3 circular interpolation segments."""
        line_segments = [
            self._segment_plot_points(segment, plane, mirrored=mirrored)
            for segment in segments
        ]
        self._add_line_collection(
            line_segments,
            color="#CC6600",
            linestyle="-",
            linewidth=2.25,
            alpha=alpha,
            label=label,
        )

    def _draw_turning_mirror(
        self,
        linear_segments: list[ToolpathSegment],
        arc_segments: list[ToolpathSegment],
    ) -> None:
        """Mirror turning cut geometry about the spindle centerline."""
        self._draw_segments(
            linear_segments,
            "#4682B4",
            "-",
            "回转体镜像",
            "XZ",
            mirrored=True,
            alpha=0.42,
        )
        self._draw_arc_segments(arc_segments, "XZ", mirrored=True, alpha=0.50, label="圆角镜像")

    def _draw_start_end_markers(self, segments: list[ToolpathSegment], plane: str = "XY") -> None:
        """Mark the first and last visible XY path points."""
        if not segments:
            return
        cutting_segments = [segment for segment in segments if segment.move_type != "rapid"]
        marker_segments = cutting_segments or segments
        first_segment = marker_segments[0]
        last_segment = marker_segments[-1]
        first_x, first_y = self._display_point(first_segment.start_x, first_segment.start_y, plane)
        last_x, last_y = self._display_point(last_segment.end_x, last_segment.end_y, plane)
        self._axis.scatter(
            first_x,
            first_y,
            s=72,
            color="#3D8B37",
            edgecolors="#FFFFFF",
            linewidths=1.4,
            zorder=5,
            label="起点",
        )
        self._axis.scatter(
            last_x,
            last_y,
            s=78,
            color="#C0392B",
            edgecolors="#FFFFFF",
            linewidths=1.4,
            zorder=5,
            label="终点",
        )

    def _fit_to_segments(self, segments: list[ToolpathSegment], plane: str = "XY") -> None:
        """Adjust axes to fit all visible path points with a small margin."""
        if not segments:
            self._fit_to_bounds(None)
            return

        plot_points = [
            point
            for segment in segments
            for point in self._segment_plot_points(segment, plane)
        ]
        if plane == "XZ":
            plot_points.extend((point[0], -point[1]) for point in plot_points if point[1] > 0)
        xs = [point[0] for point in plot_points]
        ys = [point[1] for point in plot_points]
        self._fit_to_bounds((min(xs), min(ys), max(xs), max(ys)))

    def _segment_plot_points(
        self,
        segment: ToolpathSegment,
        plane: str,
        *,
        mirrored: bool = False,
    ) -> list[tuple[float, float]]:
        """Return display points for one segment in the selected view plane."""
        source_points = segment.points or [(segment.start_x, segment.start_y), (segment.end_x, segment.end_y)]
        points = [self._display_point(point[0], point[1], plane) for point in source_points]
        if mirrored:
            return [(point[0], -point[1]) for point in points]
        return points

    def _display_point(self, x_value: float, y_value: float, plane: str) -> tuple[float, float]:
        """Convert simulator display coordinates to canvas coordinates."""
        if plane == "XZ":
            return x_value, y_value / 2.0
        return x_value, y_value

    def _fit_to_bounds(self, bounds: tuple[float, float, float, float] | None) -> None:
        """Fit all geometry while preserving equal data scale inside the full axes area."""
        if bounds is None:
            bounds = (-10.0, -10.0, 100.0, 80.0)

        min_x, min_y, max_x, max_y = bounds
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        margin = max(span_x, span_y) * 0.14
        span_x += margin * 2.0
        span_y += margin * 2.0

        bbox = self._axis.bbox
        pixel_aspect = (bbox.width / bbox.height) if bbox.height > 0 else 1.0
        target_x = max(span_x, span_y * pixel_aspect)
        target_y = max(span_y, target_x / pixel_aspect)

        self._axis.set_xlim(center_x - target_x * 0.5, center_x + target_x * 0.5)
        self._axis.set_ylim(center_y - target_y * 0.5, center_y + target_y * 0.5)

    def _draw_dxf_lines(self, result: DxfReadResult) -> None:
        """Draw DXF LINE entities."""
        self._add_line_collection(
            [[(line.start_x, line.start_y), (line.end_x, line.end_y)] for line in result.lines],
            color="#0f172a",
            linestyle="-",
            linewidth=2.0,
            alpha=1.0,
            label="LINE",
        )

    def _draw_dxf_circles(self, result: DxfReadResult) -> None:
        """Draw DXF CIRCLE entities."""
        for index, circle in enumerate(result.circles):
            patch = Circle(
                (circle.center_x, circle.center_y),
                radius=circle.radius,
                fill=False,
                edgecolor="#0f766e",
                linewidth=2.0,
                label="CIRCLE" if index == 0 else None,
            )
            self._axis.add_patch(patch)

    def _draw_dxf_arcs(self, result: DxfReadResult) -> None:
        """Draw DXF ARC entities."""
        for index, arc in enumerate(result.arcs):
            theta1, theta2 = self._normalized_arc_angles(arc)
            patch = Arc(
                (arc.center_x, arc.center_y),
                width=arc.radius * 2.0,
                height=arc.radius * 2.0,
                angle=0.0,
                theta1=theta1,
                theta2=theta2,
                color="#b45309",
                linewidth=2.0,
                label="ARC" if index == 0 else None,
            )
            self._axis.add_patch(patch)

    def _draw_dxf_polylines(self, result: DxfReadResult) -> None:
        """Draw DXF LWPOLYLINE and POLYLINE entities."""
        line_segments: list[list[tuple[float, float]]] = []
        for polyline in result.polylines:
            if len(polyline.points) < 2:
                continue
            points = list(polyline.points)
            if polyline.is_closed:
                points.append(points[0])
            line_segments.append(points)
        self._add_line_collection(
            line_segments,
            color="#7c3aed",
            linestyle="-",
            linewidth=2.0,
            alpha=1.0,
            label="POLYLINE",
        )

    def _add_line_collection(
        self,
        line_segments: list[list[tuple[float, float]]],
        *,
        color: str,
        linestyle: str,
        linewidth: float,
        alpha: float,
        label: str,
    ) -> None:
        """Add many 2D polylines as one Matplotlib collection."""
        clean_segments = [points for points in line_segments if len(points) >= 2]
        if not clean_segments:
            return
        collection = LineCollection(
            clean_segments,
            colors=color,
            linestyles=linestyle,
            linewidths=linewidth,
            alpha=alpha,
            label=label,
        )
        self._axis.add_collection(collection)

    def _normalized_arc_angles(self, arc: DxfArc) -> tuple[float, float]:
        """Return arc angles adjusted for counter-clockwise wraparound."""
        start = arc.start_angle
        end = arc.end_angle
        if end < start:
            end += 360.0
        return start, end
