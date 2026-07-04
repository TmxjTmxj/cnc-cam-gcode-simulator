"""Industrial CAM parameter and status panel widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.dxf_reader import ALL_LAYERS_LABEL
from core.toolpath import CamParameters


class ControlPanelWidget(QWidget):
    """Stable bottom parameter panel for CAM and simulation settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the parameter panel with engineering-style grouped controls."""
        super().__init__(parent)
        self.setObjectName("controlPanel")

        self._build_parameter_inputs()
        self._build_status_labels()
        self._build_layout()

    def parameters(self) -> CamParameters:
        """Return CAM parameters from the current UI control values."""
        return CamParameters(
            tool_diameter=self.tool_diameter_input.value(),
            spindle_speed=self.spindle_speed_input.value(),
            feed_rate=self.feed_rate_input.value(),
            cutting_depth=self.cutting_depth_input.value(),
            safe_height=self.safe_height_input.value(),
            machining_mode=("\u8f66\u524a\u6a21\u5f0f" if self.machining_mode_input.currentIndex() == 1 else "\u94e3\u524a\u6a21\u5f0f"),
            contour_direction=self.contour_direction_input.currentText(),
            zero_origin=self.zero_origin_input.isChecked(),
            arc_output=self.arc_output_input.currentText(),
            layer_filter=self.layer_filter_input.currentText(),
            cutter_compensation=self.cutter_compensation_input.currentData() or "none",
        )

    def set_available_layers(self, layers: list[str]) -> None:
        """Refresh the DXF layer filter while preserving the current choice when possible."""
        current = self.layer_filter_input.currentText() or ALL_LAYERS_LABEL
        values = [ALL_LAYERS_LABEL, *[layer for layer in layers if layer and layer != ALL_LAYERS_LABEL]]
        self.layer_filter_input.blockSignals(True)
        self.layer_filter_input.clear()
        self.layer_filter_input.addItems(values)

        self.cutter_compensation_input = QComboBox(self)
        self.cutter_compensation_input.addItem("\u65e0\u8865\u507f", "none")
        self.cutter_compensation_input.addItem("\u5de6\u8865\u507f", "left")
        self.cutter_compensation_input.addItem("\u53f3\u8865\u507f", "right")
        self.layer_filter_input.setCurrentText(current if current in values else ALL_LAYERS_LABEL)
        self.layer_filter_input.blockSignals(False)

    def _build_parameter_inputs(self) -> None:
        """Create reusable CAM input controls with sensible defaults."""
        self.tool_diameter_input = QDoubleSpinBox(self)
        self.tool_diameter_input.setRange(0.1, 100.0)
        self.tool_diameter_input.setDecimals(2)
        self.tool_diameter_input.setSuffix(" mm")
        self.tool_diameter_input.setValue(6.0)

        self.spindle_speed_input = QSpinBox(self)
        self.spindle_speed_input.setRange(100, 60000)
        self.spindle_speed_input.setSuffix(" rpm")
        self.spindle_speed_input.setSingleStep(500)
        self.spindle_speed_input.setValue(12000)

        self.feed_rate_input = QSpinBox(self)
        self.feed_rate_input.setRange(1, 10000)
        self.feed_rate_input.setSuffix(" mm/min")
        self.feed_rate_input.setSingleStep(50)
        self.feed_rate_input.setValue(300)

        self.cutting_depth_input = QDoubleSpinBox(self)
        self.cutting_depth_input.setRange(-100.0, 0.0)
        self.cutting_depth_input.setDecimals(2)
        self.cutting_depth_input.setSuffix(" mm")
        self.cutting_depth_input.setValue(-1.0)

        self.safe_height_input = QDoubleSpinBox(self)
        self.safe_height_input.setRange(0.1, 100.0)
        self.safe_height_input.setDecimals(2)
        self.safe_height_input.setSuffix(" mm")
        self.safe_height_input.setValue(5.0)

        self.machining_mode_input = QComboBox(self)
        self.machining_mode_input.addItems(["\u94e3\u524a\u6a21\u5f0f", "\u8f66\u524a\u6a21\u5f0f"])
        self.machining_mode_input.setCurrentText("\u94e3\u524a\u6a21\u5f0f")

        self.contour_direction_input = QComboBox(self)
        self.contour_direction_input.addItems(["自动", "顺时针", "逆时针"])

        self.arc_output_input = QComboBox(self)
        self.arc_output_input.addItems(["折线近似", "G2/G3 圆弧"])
        self.arc_output_input.setCurrentText("G2/G3 圆弧")

        self.layer_filter_input = QComboBox(self)
        self.layer_filter_input.addItems(["全部图层"])

        self.cutter_compensation_input = QComboBox(self)
        self.cutter_compensation_input.addItem("\u65e0\u8865\u507f", "none")
        self.cutter_compensation_input.addItem("\u5de6\u8865\u507f", "left")
        self.cutter_compensation_input.addItem("\u53f3\u8865\u507f", "right")

        self.zero_origin_input = QCheckBox("坐标归零", self)
        self.zero_origin_input.setChecked(True)

        for widget in (
            self.tool_diameter_input,
            self.spindle_speed_input,
            self.feed_rate_input,
            self.cutting_depth_input,
            self.safe_height_input,
            self.machining_mode_input,
            self.contour_direction_input,
            self.arc_output_input,
            self.layer_filter_input,
            self.cutter_compensation_input,
        ):
            widget.setMinimumWidth(170)
            widget.setMinimumHeight(24)
            widget.setMaximumHeight(26)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.zero_origin_input.setMinimumHeight(24)
        self.zero_origin_input.setMaximumHeight(26)

    def _build_status_labels(self) -> None:
        """Create public labels consumed by the main window update methods."""
        self.current_position_label = QLabel("X0.000  Y0.000  Z0.000", self)
        self.path_length_label = QLabel("0.000 mm", self)
        self.mode_label = QLabel("G代码仿真", self)
        self.current_line_label = QLabel("未开始", self)
        self.parse_status_label = QLabel("未解析", self)
        self.entity_count_label = QLabel("0", self)
        self.drawing_bounds_label = QLabel("无", self)

        for label in (
            self.current_position_label,
            self.path_length_label,
            self.mode_label,
            self.current_line_label,
            self.parse_status_label,
            self.entity_count_label,
            self.drawing_bounds_label,
        ):
            label.setObjectName("metricValue")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def _build_layout(self) -> None:
        """Assemble a right-side CAM inspector inside a scroll-safe surface."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("parameterScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget(scroll_area)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(10)

        title = QLabel("CAM参数", content)
        title.setObjectName("inspectorTitle")
        content_layout.addWidget(title)
        content_layout.addWidget(self._machining_mode_group())
        content_layout.addWidget(self._cam_parameter_group())
        content_layout.addWidget(self._engineering_parameter_group())
        content_layout.addWidget(self._status_group())
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)

    def _cam_parameter_group(self) -> QGroupBox:
        """Return the grouped CAM machining parameter section."""
        group = QGroupBox("刀具 / 切削参数", self)
        layout = self._form_layout(group)
        self._add_form_row(layout, "刀具直径", self.tool_diameter_input)
        self._add_form_row(layout, "主轴转速", self.spindle_speed_input)
        self._add_form_row(layout, "进给速度", self.feed_rate_input)
        self._add_form_row(layout, "切削深度", self.cutting_depth_input)
        self._add_form_row(layout, "安全高度", self.safe_height_input)
        return group

    def _engineering_parameter_group(self) -> QGroupBox:
        """Return the grouped simulation and engineering parameter section."""
        group = QGroupBox("工程策略", self)
        layout = self._form_layout(group)
        self._add_form_row(layout, "轮廓方向", self.contour_direction_input)
        self._add_form_row(layout, "坐标归零", self.zero_origin_input)
        self._add_form_row(layout, "圆弧输出", self.arc_output_input)
        self._add_form_row(layout, "图层选择", self.layer_filter_input)
        return group

    def _machining_mode_group(self) -> QGroupBox:
        """Return a compact machining mode group."""
        group = QGroupBox("加工模式", self)
        layout = self._form_layout(group)
        self._add_form_row(layout, "模式", self.machining_mode_input)
        return group

    def _status_group(self) -> QGroupBox:
        """Return visible status metrics consumed by the main window."""
        group = QGroupBox("仿真 / 图纸状态", self)
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        metrics = [
            ("当前坐标", self.current_position_label),
            ("路径长度", self.path_length_label),
            ("当前模式", self.mode_label),
            ("当前行", self.current_line_label),
            ("解析状态", self.parse_status_label),
            ("图元数量", self.entity_count_label),
            ("图纸范围", self.drawing_bounds_label),
        ]
        for index, (title, value) in enumerate(metrics):
            layout.addWidget(self._metric_card(title, value), index // 2, index % 2)
        return group

    def _metric_card(self, title: str, value: QLabel) -> QWidget:
        """Return one visible status metric card."""
        card = QWidget(self)
        card.setObjectName("inspectorMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)
        title_label = QLabel(title, card)
        title_label.setObjectName("metricTitle")
        layout.addWidget(title_label)
        layout.addWidget(value)
        return card

    def _form_layout(self, group: QGroupBox) -> QFormLayout:
        """Create a consistent non-overlapping form layout for parameter cards."""
        layout = QFormLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(7)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return layout

    def _add_form_row(self, layout: QFormLayout, label_text: str, widget: QWidget) -> None:
        """Add one consistent label/control row to a parameter form."""
        label = QLabel(label_text, self)
        label.setObjectName("formLabel")
        label.setMinimumWidth(80)
        layout.addRow(label, widget)
