"""集中管理的工程常量。

各模块仍可保留自身模块级常量作为向后兼容的 re-export，
新代码应优先从 ``core.constants`` 导入。
"""

from __future__ import annotations

# 几何采样与容差
CIRCLE_SEGMENT_COUNT: int = 72
ARC_DEGREE_STEP: float = 5.0
LINE_JOIN_TOLERANCE: float = 1e-3
ARC_RADIUS_TOLERANCE: float = 0.05
SPLINE_SAMPLE_COUNT: int = 48

# CAM 加工模式字符串
MILLING_MODE: str = "铣削模式"
TURNING_MODE: str = "车削模式"

# CAM 输出策略
ARC_OUTPUT_G2G3: str = "G2/G3 圆弧"

# 进给率默认值
PLUNGE_FEED_RATE: int = 100
DEFAULT_RAPID_SPEED: float = 50000.0

# 仿真插值
MIN_LINEAR_SAMPLES: int = 20

# DXF 图层
ALL_LAYERS_LABEL: str = "全部图层"