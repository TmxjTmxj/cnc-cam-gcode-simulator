"""Machine coordinate state machine shared by parser, simulator, and animation.

之前 ``core/simulator.py`` 的位置推进和 ``ui/simulation_runner.py`` 的
``_MachinePos.advance`` 各自实现了一份逻辑，后续若需要支持 G92/G52/G54-G59
等工作坐标系偏移会需要改两处。本模块统一暴露一个不可变 ``MachineState``，
让动画控制器等模块复用同一份模态推进语义，不破坏既有接口。
"""

from __future__ import annotations

from core.gcode_parser import GCodeCommand


class MachineState:
    """Track modal machine position by applying GCodeCommand coordinates.

    不可变：``advance`` 返回新的 ``MachineState`` 实例，便于在插值器中
    安全地保存起点而不必担心后续状态被修改。
    """

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def advance(self, cmd: GCodeCommand | None) -> "MachineState":
        """Return next position, inheriting omitted axes from current state.

        - 增量模式（G91）：在当前坐标上累加命令给出的轴偏移
        - 绝对模式（G90）：直接替换命令给出的轴，未给出的轴保持不变
        - 命令为 ``None``：返回与当前位置相同的新实例
        """
        if cmd is None:
            return MachineState(self.x, self.y, self.z)
        if cmd.distance_mode == "incremental":
            return MachineState(
                x=self.x + (cmd.x or 0.0),
                y=self.y + (cmd.y or 0.0),
                z=self.z + (cmd.z or 0.0),
            )
        return MachineState(
            x=cmd.x if cmd.x is not None else self.x,
            y=cmd.y if cmd.y is not None else self.y,
            z=cmd.z if cmd.z is not None else self.z,
        )

    def as_tuple(self) -> tuple[float, float, float]:
        """Return the machine position as an ``(x, y, z)`` tuple."""
        return (self.x, self.y, self.z)


__all__ = ["MachineState"]