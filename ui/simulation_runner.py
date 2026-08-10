"""基于 QTimer 的实时仿真动画控制器。

将 GCodeSimulator 输出的 ToolpathSegment 列表展开为细粒度插值点序列，
按进给速度（F 值）计算每段耗时，通过 QTimer 以约 30 fps 的节奏
发射信号驱动 UI 更新刀具位置、G 代码行号及进度信息。

维护两个坐标系：
- 机器坐标（real X, Y, Z）：从 GCodeCommand 模态追踪获得，用于 3D 画布
- 显示坐标（display plane）：映射后的平面坐标，用于控制面板文本显示
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QTimer, Signal

from core.constants import DEFAULT_RAPID_SPEED, MIN_LINEAR_SAMPLES
from core.gcode_parser import GCodeCommand, GCodeParseResult
from core.machine_state import MachineState
from core.simulator import SimulationResult, ToolpathSegment

DEFAULT_FEED_SPEED: float = 3000.0
TIMER_INTERVAL_MS: int = 33


@dataclass
class InterpolatedPoint:
    """单个插值点，同时存储机器坐标和显示坐标。"""

    mx: float
    my: float
    mz: float
    dx: float
    dy: float
    dz: float
    cumulative_time: float
    line_number: int
    segment_index: int
    move_type: str


@dataclass
class SegmentTiming:
    """预计算的一个段的计时信息。"""

    segment_index: int
    line_number: int
    move_type: str
    raw_line: str
    points: list[InterpolatedPoint] = field(default_factory=list)
    duration: float = 0.0


class SimulationRunner(QObject):
    """实时仿真动画控制器。

    将 G 代码刀具路径展开为插值点序列，用 QTimer 按时间推进并发射信号，
    支持播放、暂停、停止、单步前进/后退及速度倍率调节。
    """

    position_updated = Signal(float, float, float, int)
    line_changed = Signal(int)
    progress_changed = Signal(float)
    state_changed = Signal(str)
    coordinate_updated = Signal(str)
    segment_updated = Signal(str)
    time_updated = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """初始化仿真控制器，默认 5 倍速。"""
        super().__init__(parent)
        self._segments: list[SegmentTiming] = []
        self._real_positions: list[tuple[float, float, float]] = []
        self._total_duration: float = 0.0
        self._segment_start_times: list[float] = []
        self._current_segment_index: int = 0
        self._current_point_index: int = 0
        self._elapsed_time: float = 0.0
        self._speed_multiplier: float = 5.0
        self._state: str = "idle"

        self._timer = QTimer(self)
        self._timer.setInterval(TIMER_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timer_tick)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def load(self, parse_result: GCodeParseResult, simulation_result: SimulationResult) -> None:
        """Build interpolated point sequence from simulator output."""
        self._timer.stop()
        self._state = "idle"
        self._segments = []
        self._real_positions = []
        self._segment_start_times = []
        self._current_segment_index = 0
        self._current_point_index = 0
        self._elapsed_time = 0.0

        segments: list[SegmentTiming] = []
        real_positions: list[tuple[float, float, float]] = []
        segment_start_times: list[float] = []
        total_duration = 0.0
        # 模态 F 进给速度：当前行指定 F 就更新，后续行继承
        modal_feed: float | None = None

        for seg_idx, toolpath_seg in enumerate(simulation_result.segments):
            cmd = getattr(toolpath_seg, "command", None)
            start_pos = getattr(toolpath_seg, "machine_start", None)
            end_pos = getattr(toolpath_seg, "machine_end", None)
            if start_pos is None or end_pos is None:
                start_machine = _MachinePos(0.0, 0.0, 0.0)
                end_machine = start_machine.advance(cmd)
            else:
                start_machine = _MachinePos(start_pos.x, start_pos.y, start_pos.z)
                end_machine = _MachinePos(end_pos.x, end_pos.y, end_pos.z)

            points = self._interpolate_segment(
                toolpath_seg,
                cmd,
                start_machine,
                end_machine,
                simulation_result.plane,
            )
            # 模态 F 继承：当前行指定 F 就更新模态值
            if cmd is not None and cmd.f is not None and cmd.f > 0:
                modal_feed = cmd.f
            duration = self._calculate_duration(toolpath_seg, cmd, modal_feed)
            segment_start_times.append(total_duration)

            for pt in points:
                pt.cumulative_time = (
                    total_duration + pt.cumulative_time * duration
                    if duration > 0
                    else total_duration
                )
                pt.segment_index = seg_idx

            segments.append(
                SegmentTiming(
                    segment_index=seg_idx,
                    line_number=toolpath_seg.line_number,
                    move_type=toolpath_seg.move_type,
                    raw_line=toolpath_seg.raw_line,
                    points=points,
                    duration=duration,
                )
            )
            total_duration += duration
            for pt in points:
                real_positions.append((pt.mx, pt.my, pt.mz))

        self._segments = segments
        self._real_positions = real_positions
        self._segment_start_times = segment_start_times
        self._total_duration = total_duration
        self._current_segment_index = 0
        self._current_point_index = 0
        self._elapsed_time = 0.0
        self.progress_changed.emit(0.0)
        self._emit_initial_position()

    def get_real_positions(self) -> list[tuple[float, float, float]]:
        """Return all interpolated machine-coordinate points for 3D canvas."""
        return list(self._real_positions)

    def total_duration(self) -> float:
        """Return the current loaded simulation duration in seconds."""
        return self._total_duration

    def play(self) -> None:
        """Start or resume playback."""
        # 空数据保护：没有 segments 时拒绝进入 playing 状态
        if not self._segments:
            return
        if self._state == "finished":
            self._current_segment_index = 0
            self._current_point_index = 0
            self._elapsed_time = 0.0
        self._state = "playing"
        self._timer.start()
        self.state_changed.emit("playing")
        self._emit_all()

    def pause(self) -> None:
        """Pause at current position."""
        if self._state == "playing":
            self._timer.stop()
            self._state = "paused"
            self.state_changed.emit("paused")

    def stop(self) -> None:
        """Stop and reset to beginning."""
        self._timer.stop()
        self._state = "idle"
        self._current_segment_index = 0
        self._current_point_index = 0
        self._elapsed_time = 0.0
        self.state_changed.emit("idle")
        self.progress_changed.emit(0.0)
        self._emit_initial_position()

    def clear(self) -> None:
        """Drop all loaded simulation data and reset playback state.

        与 ``stop()``（仅重置播放索引、保留 segments 供重播）不同，
        本方法彻底清空 segments / real_positions / total_duration，
        用于编辑器清空或无有效 G代码等需要废弃旧仿真的场景。
        """
        self._timer.stop()
        self._state = "idle"
        self._segments = []
        self._real_positions = []
        self._segment_start_times = []
        self._total_duration = 0.0
        self._current_segment_index = 0
        self._current_point_index = 0
        self._elapsed_time = 0.0
        self.state_changed.emit("idle")
        self.progress_changed.emit(0.0)
        self._emit_initial_position()

    def step_forward(self) -> None:
        """Advance one segment forward."""
        if not self._segments:
            return
        if self._state == "playing":
            self.pause()
        nxt = self._current_segment_index + 1
        if nxt < len(self._segments):
            self._jump_to_segment(nxt)
        else:
            self._finish()

    def step_backward(self) -> None:
        """Go back one segment."""
        if not self._segments:
            return
        if self._state == "playing":
            self.pause()
        prv = max(0, self._current_segment_index - 1)
        self._jump_to_segment(prv)

    def set_speed(self, multiplier: float) -> None:
        """Set playback speed multiplier."""
        self._speed_multiplier = max(0.01, multiplier)

    def is_playing(self) -> bool:
        """Return whether playback is active."""
        return self._state == "playing"

    def current_segment_index(self) -> int:
        """Return current segment index."""
        return self._current_segment_index

    # ------------------------------------------------------------------
    # timer callback
    # ------------------------------------------------------------------

    def _on_timer_tick(self) -> None:
        """Advance elapsed time and find the matching interpolation point."""
        if self._state != "playing" or not self._segments:
            return

        step = (TIMER_INTERVAL_MS / 1000.0) * self._speed_multiplier
        self._elapsed_time += step

        if self._elapsed_time >= self._total_duration:
            self._finish()
            return

        seg_idx = bisect.bisect_right(self._segment_start_times, self._elapsed_time) - 1
        seg_idx = max(0, min(seg_idx, len(self._segments) - 1))
        if seg_idx != self._current_segment_index:
            self._current_segment_index = seg_idx
            self._current_point_index = 0
            self._on_segment_changed(self._segments[seg_idx])
        self._advance_within_segment(self._segments[seg_idx])
        self._emit_progress()
        self._emit_time()

    # ------------------------------------------------------------------
    # interpolation & timing
    # ------------------------------------------------------------------

    def _interpolate_segment(
        self,
        toolpath_seg: ToolpathSegment,
        command: GCodeCommand | None,
        start_machine: _MachinePos,
        end_machine: _MachinePos,
        plane: str,
    ) -> list[InterpolatedPoint]:
        """Build interpolated points with both machine and display coordinates."""
        points: list[InterpolatedPoint] = []

        if toolpath_seg.move_type in ("arc",) and toolpath_seg.points:
            arc_pts = toolpath_seg.points
            seg_len = toolpath_seg.length
            cumulative = 0.0
            for idx, (px, py) in enumerate(arc_pts):
                if idx > 0:
                    cumulative += math.hypot(px - arc_pts[idx - 1][0], py - arc_pts[idx - 1][1])
                t = cumulative / seg_len if seg_len > 0 else idx / max(1, len(arc_pts) - 1)
                mx, my, mz = self._machine_from_display_point(
                    px,
                    py,
                    start_machine,
                    end_machine,
                    plane,
                    t,
                )
                points.append(
                    InterpolatedPoint(
                        mx=mx, my=my, mz=mz,
                        dx=px, dy=py, dz=mz,
                        cumulative_time=t, line_number=toolpath_seg.line_number,
                        segment_index=0, move_type=toolpath_seg.move_type,
                    )
                )
        else:
            n = max(MIN_LINEAR_SAMPLES, 2)
            for i in range(n):
                t = i / (n - 1) if n > 1 else 0.0
                px = toolpath_seg.start_x + (toolpath_seg.end_x - toolpath_seg.start_x) * t
                py = toolpath_seg.start_y + (toolpath_seg.end_y - toolpath_seg.start_y) * t
                mx = self._lerp(start_machine.x, end_machine.x, t)
                my = self._lerp(start_machine.y, end_machine.y, t)
                mz = self._lerp(start_machine.z, end_machine.z, t)
                points.append(
                    InterpolatedPoint(
                        mx=mx, my=my, mz=mz,
                        dx=px, dy=py, dz=mz,
                        cumulative_time=t, line_number=toolpath_seg.line_number,
                        segment_index=0, move_type=toolpath_seg.move_type,
                    )
                )
        return points

    def _machine_from_display_point(
        self,
        display_x: float,
        display_y: float,
        start_machine: _MachinePos,
        end_machine: _MachinePos,
        plane: str,
        ratio: float,
    ) -> tuple[float, float, float]:
        """Map a sampled 2D simulator point back into machine XYZ coordinates."""
        if plane == "XZ":
            return (
                display_y,
                self._lerp(start_machine.y, end_machine.y, ratio),
                display_x,
            )
        return (
            display_x,
            display_y,
            self._lerp(start_machine.z, end_machine.z, ratio),
        )

    @staticmethod
    def _lerp(start: float, end: float, ratio: float) -> float:
        """Linear interpolation helper."""
        return start + (end - start) * ratio

    def _calculate_duration(
        self,
        toolpath_seg: ToolpathSegment,
        command: GCodeCommand | None,
        modal_feed: float | None = None,
    ) -> float:
        """Compute segment duration in seconds from length and feed rate.

        修复：F 进给速度模态继承 —— 当前行未指定 F 时使用 ``modal_feed``
        而非直接回退到默认值。
        """
        seg_len = toolpath_seg.length
        if seg_len <= 0:
            return 0.0
        if toolpath_seg.move_type == "rapid":
            feed = DEFAULT_RAPID_SPEED
        elif modal_feed is not None and modal_feed > 0:
            feed = modal_feed
        else:
            feed = DEFAULT_FEED_SPEED
        return seg_len / feed * 60.0

    # ------------------------------------------------------------------
    # internal state advance
    # ------------------------------------------------------------------

    def _advance_within_segment(self, seg: SegmentTiming) -> None:
        """Find and emit the interpolation point for current elapsed time."""
        if not seg.points or seg.duration <= 0:
            self._emit_position(seg, 0)
            self._emit_coordinate(seg, 0)
            return

        acc_before = self._segment_start_times[self._current_segment_index] if self._segment_start_times else 0.0
        local_elapsed = self._elapsed_time - acc_before
        local_ratio = max(0.0, min(1.0, local_elapsed / seg.duration))
        target_idx = min(int(local_ratio * (len(seg.points) - 1)), len(seg.points) - 1)

        self._current_point_index = target_idx
        self._emit_position(seg, target_idx)
        self._emit_coordinate(seg, target_idx)

    def _jump_to_segment(self, seg_index: int) -> None:
        """Jump directly to a specific segment."""
        self._current_segment_index = seg_index
        self._current_point_index = 0
        self._elapsed_time = self._segment_start_times[seg_index] if self._segment_start_times else 0.0
        seg = self._segments[seg_index]
        self._on_segment_changed(seg)
        self._emit_position(seg, 0)
        self._emit_coordinate(seg, 0)
        self._emit_progress()
        self._emit_time()

    def _finish(self) -> None:
        """End of simulation reached."""
        self._timer.stop()
        self._state = "finished"
        self._current_segment_index = len(self._segments) - 1 if self._segments else 0
        self._elapsed_time = self._total_duration
        if self._segments:
            last = self._segments[-1]
            if last.points:
                idx = len(last.points) - 1
                self._current_point_index = idx
                self._emit_position(last, idx)
                self._emit_coordinate(last, idx)
        self.progress_changed.emit(1.0)
        self.time_updated.emit(self._fmt_time(self._total_duration), self._fmt_time(0.0))
        self.state_changed.emit("finished")

    # ------------------------------------------------------------------
    # signal helpers
    # ------------------------------------------------------------------

    def _emit_all(self) -> None:
        """Emit position + coordinate for current state."""
        if self._segments:
            seg = self._segments[self._current_segment_index]
            idx = min(self._current_point_index, len(seg.points) - 1) if seg.points else 0
            self._emit_position(seg, idx)
            self._emit_coordinate(seg, idx)
        self._emit_progress()
        self._emit_time()

    def _emit_initial_position(self) -> None:
        """Emit signals for the initial (origin) state."""
        if self._segments:
            seg = self._segments[0]
            self._emit_position(seg, 0)
            self._emit_coordinate(seg, 0)
            self._on_segment_changed(seg)
        else:
            self.position_updated.emit(0.0, 0.0, 0.0, 0)
            self.line_changed.emit(0)
            self.coordinate_updated.emit("X 0.000  Y 0.000  Z 0.000")
            self.segment_updated.emit("")
        self.time_updated.emit(self._fmt_time(0.0), self._fmt_time(self._total_duration))

    def _emit_position(self, seg: SegmentTiming, idx: int) -> None:
        """Emit machine-coordinate position for 3D canvas."""
        if not seg.points:
            self.position_updated.emit(0.0, 0.0, 0.0, seg.segment_index)
            self.line_changed.emit(seg.line_number)
            return
        pt = seg.points[idx]
        self.position_updated.emit(pt.mx, pt.my, pt.mz, seg.segment_index)
        self.line_changed.emit(pt.line_number)

    def _emit_coordinate(self, seg: SegmentTiming, idx: int) -> None:
        """Emit formatted coordinate text for control panel."""
        if not seg.points:
            return
        pt = seg.points[idx]
        self.coordinate_updated.emit(
            f"X {pt.mx:.3f}  Y {pt.my:.3f}  Z {pt.mz:.3f}"
        )

    def _emit_progress(self) -> None:
        """Emit normalized progress value."""
        p = self._elapsed_time / self._total_duration if self._total_duration > 0 else 0.0
        self.progress_changed.emit(max(0.0, min(1.0, p)))

    def _emit_time(self) -> None:
        """Emit elapsed and remaining time text."""
        remaining = max(0.0, self._total_duration - self._elapsed_time)
        self.time_updated.emit(
            self._fmt_time(self._elapsed_time),
            self._fmt_time(remaining),
        )

    def _on_segment_changed(self, seg: SegmentTiming) -> None:
        """Emit line and segment info when entering a new segment."""
        self.line_changed.emit(seg.line_number)
        txt = f"N{seg.line_number} | {seg.move_type}"
        if seg.raw_line:
            txt += f" | {seg.raw_line.strip()}"
        self.segment_updated.emit(txt)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS for consistent timeline and summary displays."""
        s = max(0, int(seconds))
        h, remainder = divmod(s, 3600)
        m, sec = divmod(remainder, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"


# 向后兼容别名：原 _MachinePos 实现已抽到 core/machine_state.MachineState，
# 保留名称以便模块内部类型注解和未来测试兼容。
_MachinePos = MachineState
