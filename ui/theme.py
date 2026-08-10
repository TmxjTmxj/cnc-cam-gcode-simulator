"""集中管理的 UI 颜色与主题常量。

极简技术风调色板，对齐 ``cnc-cam-ui-concept/pages/technical-minimal.html`` 设计概念。
``ui/style.py`` 中的 COLORS 字典在此重新声明，
新代码应优先从 ``ui.theme`` 导入颜色常量，便于后续主题切换。
"""

from __future__ import annotations

# 主色调（浅灰背景 + 钢蓝主色 + 零圆角 + 紧凑布局）
COLOR_PRIMARY: str = "#4682B4"
COLOR_PRIMARY_HOVER: str = "#3A6F9E"
COLOR_SECONDARY: str = "#E8ECF0"
COLOR_BACKGROUND: str = "#E8ECF0"
COLOR_SURFACE: str = "#F4F6F8"
COLOR_ELEVATED: str = "#FFFFFF"
COLOR_INSET: str = "#DDE1E5"
COLOR_HOVER: str = "#E0E4E8"
COLOR_ACTIVE: str = "#CDD3D9"
COLOR_BORDER: str = "#B0B8C0"
COLOR_BORDER_SUBTLE: str = "#C8CED4"
COLOR_TEXT: str = "#1A1E22"
COLOR_TEXT_SECONDARY: str = "#4A5058"
COLOR_TEXT_TERTIARY: str = "#7A828A"
COLOR_MUTED: str = "#7A828A"
COLOR_SUCCESS: str = "#3D8B37"
COLOR_WARNING: str = "#B8860B"
COLOR_DANGER: str = "#C0392B"

# 仿真专用色（与设计概念 CNC 色系一致）
COLOR_RAPID: str = "#808890"  # G0 快速移动
COLOR_LINEAR: str = "#4682B4"  # G1 直线切削
COLOR_ARC: str = "#CC6600"  # G2/G3 圆弧
COLOR_CUT_PATH: str = "#4682B4"
COLOR_STOCK: str = "#5B9BD5"
COLOR_TURNTABLE_FINAL: str = "#3D8B37"
COLOR_TOOL: str = "#B8860B"
COLOR_START: str = "#3D8B37"  # 起点标记
COLOR_END: str = "#C0392B"  # 终点标记
