"""Matplotlib based 3D machining simulation canvas.

The widget intentionally keeps the historical GLCanvasWidget API used by
MainWindow, but renders with matplotlib for reliable cross-machine behavior.
It shows stock, approximate material removal, cutter geometry, rapid/cut paths,
and supports mouse rotate/zoom/pan through the built-in navigation toolbar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


@dataclass(frozen=True)
class _Bounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    @property
    def span(self) -> float:
        return max(
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
            1.0,
        )


class GLCanvasWidget(QWidget):
    """3D stock, cutter, toolpath, and in-process-part visualization widget."""

    _MAX_STOCK_GRID = 58
    _MAX_REMOVAL_SAMPLES = 260

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)

        self._figure = Figure(figsize=(6, 4), dpi=100, facecolor="#1f2933")
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.updateGeometry()
        self._figure.subplots_adjust(left=0.12, right=0.78, bottom=0.18, top=0.88)
        self._toolbar = NavigationToolbar(self._canvas, self)
        self._axis = self._figure.add_subplot(111, projection="3d")
        self._axis.apply_aspect = lambda position=None: None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas, 1)

        self._segments: list = []
        self._real_path: list[tuple[float, float, float]] = []
        self._cut_progress = 0.0
        self._segment_index = -1
        self._tool_path_index = -1
        self._tool_x = 0.0
        self._tool_y = 0.0
        self._tool_z = 0.0
        self._tool_visible = False
        self._is_turning = False
        self._tool_diameter = 6.0
        self._stock_top_z = 0.0

        self._bounds = _Bounds(-50.0, 50.0, -50.0, 50.0, -5.0, 5.0)
        self._view_elev = 26.0
        self._view_azim = -48.0
        self._zoom_scale = 1.0
        self._draw_pending = False
        self._draw_pending_after_interaction = False
        self._user_interacting = False

        self._canvas.mpl_connect("scroll_event", self._on_scroll)
        self._canvas.mpl_connect("button_press_event", self._on_mouse_press)
        self._canvas.mpl_connect("button_release_event", self._on_mouse_release)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(80)
        self._anim_timer.timeout.connect(self._draw_scene)

        self._draw_scene()

    def set_workpiece(
        self,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        min_z: float,
        max_z: float,
        is_turning: bool = False,
    ) -> None:
        """Set stock bounds and machining mode."""
        self._bounds = self._expanded_bounds(min_x, max_x, min_y, max_y, min_z, max_z)
        self._stock_top_z = max_z if not is_turning else 0.0
        self._is_turning = is_turning
        self._request_draw()

    def load_toolpath(self, segments: list, plane: str = "XY") -> None:
        """Load simulator segments so rapid/cut movement can be drawn by type."""
        self._segments = list(segments)
        self._cut_progress = 0.0
        self._segment_index = -1
        self._tool_visible = False
        if self._segments and not self._real_path:
            path = self._segment_display_path(plane)
            if path:
                self._bounds = self._bounds_from_display_path(path, plane == "XZ")
                self._is_turning = plane == "XZ"
        self._request_draw()

    def load_toolpath_3d(self, real_positions: list, is_turning: bool = False) -> None:
        """Load the full path in machine XYZ coordinates."""
        self._real_path = [tuple(map(float, p[:3])) for p in real_positions]
        self._cut_progress = 0.0
        self._segment_index = -1
        self._tool_path_index = -1
        self._tool_visible = False
        self._is_turning = is_turning
        if self._real_path:
            self._bounds = self._bounds_from_machine_path(self._real_path, is_turning)
        self._request_draw()

    def update_tool_position(self, x: float, y: float, z: float, segment_index: int = -1) -> None:
        """Update current cutter position."""
        self._tool_x = float(x)
        self._tool_y = float(y)
        self._tool_z = float(z)
        self._tool_visible = True
        if segment_index >= 0:
            self._segment_index = segment_index
        self._tool_path_index = self._nearest_path_index((self._tool_x, self._tool_y, self._tool_z))
        self._request_draw()

    def update_cut_progress(self, progress: float) -> None:
        """Update completed cut progress in [0, 1]."""
        self._cut_progress = max(0.0, min(1.0, float(progress)))
        self._request_draw()

    def reset_view(self) -> None:
        """Reset the 3D camera to an engineering isometric view."""
        self._view_elev = 26.0
        self._view_azim = -48.0
        self._zoom_scale = 1.0
        self._request_draw()

    def start_animation(self) -> None:
        """Enable animation updates without running an extra full-redraw timer."""
        self._anim_timer.stop()
        self._request_draw()

    def stop_animation(self) -> None:
        """Stop any legacy periodic refresh timer."""
        self._anim_timer.stop()

    def _request_draw(self) -> None:
        if self._draw_pending:
            return
        self._draw_pending = True
        QTimer.singleShot(0, self._draw_scene)

    def _draw_scene(self) -> None:
        if self._user_interacting:
            self._draw_pending = False
            self._draw_pending_after_interaction = True
            return
        self._draw_pending = False
        self._capture_camera()
        self._axis.clear()
        self._figure.subplots_adjust(left=0.12, right=0.78, bottom=0.18, top=0.88)
        self._axis.set_position((0.12, 0.18, 0.66, 0.70))
        self._setup_axes()
        if self._is_turning:
            self._draw_turning_part()
            self._draw_turning_toolpath()
            self._draw_turning_tool()
        else:
            self._draw_milling_part()
            self._draw_milling_toolpath()
            self._draw_milling_tool()
        self._fit_axes()
        self._canvas.draw_idle()

    def _setup_axes(self) -> None:
        self._axis.set_facecolor("#202832")
        self._axis.grid(True, color="#536273", alpha=0.25)
        title = "3D Turning Simulation" if self._is_turning else "3D Milling Simulation"
        self._axis.set_title(title, color="#e5edf7", pad=2, fontsize=10)
        if self._is_turning:
            self._axis.set_xlabel("Z spindle axis / mm", color="#d8e1ec", labelpad=2)
            self._axis.set_ylabel("Radial Y / mm", color="#d8e1ec", labelpad=2)
            self._axis.set_zlabel("X radius / mm", color="#d8e1ec", labelpad=2)
        else:
            self._axis.set_xlabel("X / mm", color="#d8e1ec", labelpad=2)
            self._axis.set_ylabel("Y / mm", color="#d8e1ec", labelpad=2)
            self._axis.set_zlabel("Z / mm", color="#d8e1ec", labelpad=2)
        self._axis.tick_params(colors="#cbd5e1", labelsize=7, pad=1)
        self._axis.view_init(elev=self._view_elev, azim=self._view_azim)

    def _capture_camera(self) -> None:
        """Persist the current interactive Matplotlib 3D camera across animation redraws."""
        if self._axis is None:
            return
        self._view_elev = float(getattr(self._axis, "elev", self._view_elev))
        self._view_azim = float(getattr(self._axis, "azim", self._view_azim))

    def _on_mouse_press(self, event) -> None:  # type: ignore[no-untyped-def]
        """Mark interactive camera manipulation so animation redraws do not stutter."""
        if event.inaxes == self._axis:
            self._user_interacting = True

    def _on_mouse_release(self, _event) -> None:  # type: ignore[no-untyped-def]
        """Remember the view after a user rotation/pan gesture."""
        self._user_interacting = False
        self._capture_camera()
        if self._draw_pending_after_interaction:
            self._draw_pending_after_interaction = False
            self._request_draw()

    def _on_scroll(self, event) -> None:  # type: ignore[no-untyped-def]
        """Zoom the 3D scene with the mouse wheel without resetting the camera."""
        if event.inaxes != self._axis:
            return
        self._capture_camera()
        factor = 0.84 if event.step > 0 else 1.18
        self._zoom_scale = max(0.18, min(4.0, self._zoom_scale * factor))
        self._request_draw()

    def _draw_milling_part(self) -> None:
        bounds = self._bounds
        xs = np.linspace(bounds.min_x, bounds.max_x, self._MAX_STOCK_GRID)
        ys = np.linspace(bounds.min_y, bounds.max_y, self._MAX_STOCK_GRID)
        grid_x, grid_y = np.meshgrid(xs, ys)
        top_z = np.full_like(grid_x, bounds.max_z, dtype=float)

        cut_points = self._current_cut_machine_path(cutting_only=True)
        if cut_points:
            tool_radius = max(self._tool_diameter * 0.5, bounds.span * 0.025)
            for px, py, pz in self._subsample(cut_points, self._MAX_REMOVAL_SAMPLES):
                if pz >= bounds.max_z:
                    continue
                dist2 = (grid_x - px) ** 2 + (grid_y - py) ** 2
                mask = dist2 <= tool_radius ** 2
                top_z[mask] = np.minimum(top_z[mask], pz)

        self._axis.plot_surface(
            grid_x,
            grid_y,
            top_z,
            rstride=1,
            cstride=1,
            linewidth=0,
            antialiased=False,
            color="#6aa2ff",
            alpha=0.42,
            shade=True,
        )
        self._draw_milling_stock_edges()
        self._draw_milling_cut_floor(cut_points)

    def _draw_milling_stock_edges(self) -> None:
        b = self._bounds
        corners = [
            (b.min_x, b.min_y, b.min_z), (b.max_x, b.min_y, b.min_z),
            (b.max_x, b.max_y, b.min_z), (b.min_x, b.max_y, b.min_z),
            (b.min_x, b.min_y, b.max_z), (b.max_x, b.min_y, b.max_z),
            (b.max_x, b.max_y, b.max_z), (b.min_x, b.max_y, b.max_z),
        ]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
        for a, c in edges:
            self._axis.plot(
                [corners[a][0], corners[c][0]],
                [corners[a][1], corners[c][1]],
                [corners[a][2], corners[c][2]],
                color="#93c5fd",
                alpha=0.55,
                linewidth=1.0,
            )

    def _draw_milling_cut_floor(self, cut_points: list[tuple[float, float, float]]) -> None:
        if len(cut_points) < 2:
            return
        self._axis.plot(
            [p[0] for p in cut_points],
            [p[1] for p in cut_points],
            [p[2] for p in cut_points],
            color="#22c55e",
            alpha=0.70,
            linewidth=3.2,
        )

    def _draw_milling_toolpath(self) -> None:
        full = self._real_path
        if full:
            self._axis.plot([p[0] for p in full], [p[1] for p in full], [p[2] for p in full], color="#93c5fd", alpha=0.28, linewidth=1.2)
        if self._segments:
            self._draw_segment_paths_milling()
        cut = self._current_cut_machine_path(cutting_only=False)
        if len(cut) > 1:
            self._axis.plot([p[0] for p in cut], [p[1] for p in cut], [p[2] for p in cut], color="#0f6bff", alpha=0.95, linewidth=2.3)

    def _draw_segment_paths_milling(self) -> None:
        for segment in self._segments:
            points = getattr(segment, "points", None) or [(segment.start_x, segment.start_y), (segment.end_x, segment.end_y)]
            z = self._bounds.max_z + self._bounds.span * 0.015 if segment.move_type == "rapid" else self._bounds.min_z
            color = "#94a3b8" if segment.move_type == "rapid" else "#38bdf8" if segment.move_type == "linear" else "#f97316"
            style = "--" if segment.move_type == "rapid" else "-"
            self._axis.plot([p[0] for p in points], [p[1] for p in points], [z] * len(points), color=color, linestyle=style, alpha=0.42, linewidth=1.2)

    def _draw_milling_tool(self) -> None:
        if not self._tool_visible:
            return
        radius = max(self._tool_diameter * 0.5, self._bounds.span * 0.025)
        height = self._bounds.span * 0.22
        self._draw_cylinder_z(self._tool_x, self._tool_y, self._tool_z, self._tool_z + height, radius, "#e5e7eb", 0.96)
        self._axis.scatter([self._tool_x], [self._tool_y], [self._tool_z], s=46, color="#facc15", edgecolor="#111827", linewidth=0.8)

    def _draw_turning_part(self) -> None:
        profile_z, r_profile = self._turning_surface_profile()
        theta = np.linspace(0, 2 * math.pi, 56)
        zz, tt = np.meshgrid(profile_z, theta)
        rr = np.interp(zz, profile_z, r_profile)
        yy = rr * np.cos(tt)
        xx_radius = rr * np.sin(tt)
        self._axis.plot_surface(
            zz,
            yy,
            xx_radius,
            color="#6aa2ff",
            alpha=0.44,
            linewidth=0,
            antialiased=True,
            shade=True,
        )
        self._axis.plot(profile_z, np.zeros_like(profile_z), r_profile, color="#22c55e", linewidth=2.8, alpha=0.85)
        self._axis.plot(profile_z, np.zeros_like(profile_z), -r_profile, color="#22c55e", linewidth=1.6, alpha=0.45)

    def _turning_surface_profile(self) -> tuple[np.ndarray, np.ndarray]:
        """Return dense stock/profile radii for a continuous turning surface."""
        final_z, final_r = self._turning_final_profile()
        stock_radius = max(float(final_r.max(initial=5.0)), 5.0)
        if self._cut_progress <= 0.0:
            return final_z, np.full_like(final_z, stock_radius, dtype=float)
        if self._cut_progress >= 1.0:
            return final_z, final_r

        cut_path = self._current_cut_machine_path(cutting_only=True)
        if not cut_path:
            return final_z, np.full_like(final_z, stock_radius, dtype=float)

        cut_z = np.array([p[2] for p in cut_path], dtype=float)
        cut_min = float(cut_z.min())
        cut_max = float(cut_z.max())
        current_r = np.full_like(final_z, stock_radius, dtype=float)
        machined = (final_z >= cut_min) & (final_z <= cut_max)
        current_r[machined] = final_r[machined]
        return final_z, current_r

    def _turning_final_profile(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the final dense axial radius profile from the complete tool path."""
        path = self._real_path
        if not path:
            z_values = np.array([self._bounds.min_x, self._bounds.max_x], dtype=float)
            radius = max(self._bounds.span * 0.25, 5.0)
            return z_values, np.array([radius, radius], dtype=float)

        pairs: list[tuple[float, float]] = []
        for machine_x, _machine_y, machine_z in path:
            pairs.append((float(machine_z), max(abs(float(machine_x)) * 0.5, 0.1)))
        pairs.sort(key=lambda item: item[0])

        merged_z: list[float] = []
        merged_r: list[float] = []
        for z_value, radius in pairs:
            if merged_z and abs(z_value - merged_z[-1]) <= 1e-4:
                merged_r[-1] = min(merged_r[-1], radius)
            else:
                merged_z.append(z_value)
                merged_r.append(radius)

        if len(merged_z) < 2:
            center = merged_z[0] if merged_z else 0.0
            radius = merged_r[0] if merged_r else 5.0
            merged_z = [center - 0.5, center + 0.5]
            merged_r = [radius, radius]

        raw_z = np.array(merged_z, dtype=float)
        raw_r = np.array(merged_r, dtype=float)
        span = max(float(raw_z[-1] - raw_z[0]), 1.0)
        sample_count = max(96, min(420, int(span * 2.5)))
        dense_z = np.linspace(raw_z[0], raw_z[-1], sample_count)
        dense_r = np.interp(dense_z, raw_z, raw_r)
        return dense_z, dense_r

    def _draw_turning_toolpath(self) -> None:
        if self._real_path:
            mapped = [self._map_turning_point(p) for p in self._real_path]
            self._axis.plot([p[0] for p in mapped], [p[1] for p in mapped], [p[2] for p in mapped], color="#93c5fd", alpha=0.30, linewidth=1.2)
        cut = [self._map_turning_point(p) for p in self._current_cut_machine_path(cutting_only=False)]
        if len(cut) > 1:
            self._axis.plot([p[0] for p in cut], [p[1] for p in cut], [p[2] for p in cut], color="#0f6bff", alpha=0.96, linewidth=2.4)

    def _draw_turning_tool(self) -> None:
        if not self._tool_visible:
            return
        px, py, pz = self._map_turning_point((self._tool_x, self._tool_y, self._tool_z))
        size = self._bounds.span * 0.08
        self._axis.scatter([px], [py], [pz], s=70, color="#facc15", edgecolor="#111827", linewidth=0.8)
        self._axis.plot([px + size, px], [py, py], [pz + size * 0.35, pz], color="#e5e7eb", linewidth=3.0, alpha=0.95)

    def _draw_cylinder_z(self, cx: float, cy: float, z0: float, z1: float, radius: float, color: str, alpha: float) -> None:
        theta = np.linspace(0, 2 * math.pi, 22)
        z = np.linspace(z0, z1, 2)
        tt, zz = np.meshgrid(theta, z)
        xx = cx + radius * np.cos(tt)
        yy = cy + radius * np.sin(tt)
        self._axis.plot_surface(xx, yy, zz, color=color, alpha=alpha, linewidth=0, shade=True)

    def _current_cut_machine_path(self, *, cutting_only: bool) -> list[tuple[float, float, float]]:
        path = self._real_path
        if not path:
            return []
        count = int(len(path) * self._cut_progress)
        if self._cut_progress >= 1.0:
            count = len(path)
        if self._tool_visible and self._tool_path_index >= 0:
            count = self._tool_path_index + 1
        selected = path[: max(0, min(count, len(path)))]
        if self._tool_visible and self._tool_path_index >= 0:
            current = (self._tool_x, self._tool_y, self._tool_z)
            if not selected or selected[-1] != current:
                selected = [*selected, current]
        if not cutting_only:
            return selected
        threshold = self._stock_top_z - 1e-6 if not self._is_turning else None
        if threshold is None:
            return selected
        return [p for p in selected if p[2] <= threshold]

    def _segment_display_path(self, plane: str) -> list[tuple[float, float, float]]:
        result: list[tuple[float, float, float]] = []
        for segment in self._segments:
            points = getattr(segment, "points", None) or [(segment.start_x, segment.start_y), (segment.end_x, segment.end_y)]
            for px, py in points:
                if plane == "XZ":
                    result.append((py, 0.0, px))
                else:
                    result.append((px, py, 0.0))
        return result

    def _map_turning_point(self, point: tuple[float, float, float]) -> tuple[float, float, float]:
        machine_x, machine_y, machine_z = point
        radius = abs(machine_x) * 0.5
        return (machine_z, machine_y, radius)

    def _nearest_path_index(self, point: tuple[float, float, float]) -> int:
        """Return the nearest sampled machine path index to the current tool point."""
        if not self._real_path:
            return -1
        px, py, pz = point
        return min(
            range(len(self._real_path)),
            key=lambda idx: (self._real_path[idx][0] - px) ** 2
            + (self._real_path[idx][1] - py) ** 2
            + (self._real_path[idx][2] - pz) ** 2,
        )

    def _nearest_path_point(self, point: tuple[float, float, float]) -> tuple[float, float, float] | None:
        """Return the nearest sampled machine path point to a tool point."""
        idx = self._nearest_path_index(point)
        return self._real_path[idx] if idx >= 0 else None

    def _bounds_from_machine_path(self, path: list[tuple[float, float, float]], is_turning: bool) -> _Bounds:
        if is_turning:
            mapped = [self._map_turning_point(p) for p in path]
            return self._bounds_from_display_path(mapped, True)
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        zs = [p[2] for p in path]
        top_z = max(0.0, min(max(zs), max((z for z in zs if z <= 0.0), default=0.0)))
        self._stock_top_z = top_z
        bottom_z = min(min(zs), top_z - 1.0)
        return self._bounds_from_display_path(
            [(min(xs), min(ys), bottom_z), (max(xs), max(ys), top_z)],
            False,
        )

    def _bounds_from_display_path(self, path: list[tuple[float, float, float]], is_turning: bool) -> _Bounds:
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        zs = [p[2] for p in path]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)
        span = max(max_x - min_x, max_y - min_y, max_z - min_z, 20.0)
        padding = span * 0.12
        if is_turning:
            radial = max(max(abs(v) for v in zs), 5.0)
            min_y = min(min_y, -radial)
            max_y = max(max_y, radial)
            min_z = min(min_z, -radial)
            max_z = max(max_z, radial)
        return self._expanded_bounds(
            min_x - padding,
            max_x + padding,
            min_y - padding,
            max_y + padding,
            min_z - padding,
            max_z + padding,
        )

    def _expanded_bounds(self, min_x: float, max_x: float, min_y: float, max_y: float, min_z: float, max_z: float) -> _Bounds:
        if max_x - min_x < 1.0:
            min_x -= 0.5
            max_x += 0.5
        if max_y - min_y < 1.0:
            min_y -= 0.5
            max_y += 0.5
        if max_z - min_z < 1.0:
            min_z -= 0.5
            max_z += 0.5
        return _Bounds(min_x, max_x, min_y, max_y, min_z, max_z)

    def _fit_axes(self) -> None:
        b = self._bounds
        span = b.span
        cx = (b.min_x + b.max_x) * 0.5
        cy = (b.min_y + b.max_y) * 0.5
        cz = (b.min_z + b.max_z) * 0.5
        half = span * 0.58 * self._zoom_scale
        self._axis.set_xlim(cx - half, cx + half)
        self._axis.set_ylim(cy - half, cy + half)
        self._axis.set_zlim(cz - half, cz + half)
        try:
            self._axis.set_box_aspect(None, zoom=1.18)
        except (AttributeError, TypeError, ValueError):
            pass

    @staticmethod
    def _subsample(points: list[tuple[float, float, float]], max_count: int) -> list[tuple[float, float, float]]:
        if len(points) <= max_count:
            return points
        step = max(1, len(points) // max_count)
        return points[::step]
