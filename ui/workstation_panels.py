"""Workstation side panels for the high-fidelity CAM desktop shell."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.dxf_reader import DxfReadResult
from core.gcode_parser import GCodeParseResult
from core.simulator import SimulationResult


def _format_seconds(seconds: float | None) -> str:
    """Format a duration in seconds as HH:MM:SS."""
    if seconds is None:
        seconds = 0.0
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class ProjectNavigatorWidget(QWidget):
    """Left CAM workstation panel with project tree, layers, operations, and metrics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create a compact engineering navigation panel."""
        super().__init__(parent)
        self.setObjectName("projectNavigator")
        self.path_metric = QLabel("0.000\nmm", self)
        self.time_metric = QLabel("00:00:00", self)
        self.warning_metric = QLabel("0", self)
        self.line_metric = QLabel("0", self)
        self.project_tree = QTreeWidget(self)
        self.layer_table = QTableWidget(self)
        self.operation_table = QTableWidget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._project_tree_group())
        layout.addWidget(self._layer_group())
        layout.addWidget(self._operation_group())
        layout.addWidget(self._status_group())
        layout.addStretch(1)

    def update_project_file(self, file_path: str | Path, result: DxfReadResult) -> None:
        """Rebuild the project tree from the currently imported DXF file."""
        path = Path(file_path)
        self.project_tree.clear()
        root = QTreeWidgetItem([f"{path.name} ({result.entity_count} entities)"])
        layers_node = QTreeWidgetItem([f"Layers ({len(result.layers)})"])
        for layer in result.layers or ["0"]:
            layer_result = result.filtered_by_layer(layer)
            layers_node.addChild(QTreeWidgetItem([f"{layer} - {layer_result.entity_count} entities"]))
        geometry_node = QTreeWidgetItem([
            f"Geometry: LINE {len(result.lines)}, CIRCLE {len(result.circles)}, ARC {len(result.arcs)}, POLYLINE {len(result.polylines)}"
        ])
        root.addChild(layers_node)
        root.addChild(geometry_node)
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)
        layers_node.setExpanded(True)

    def update_dxf_result(self, result: DxfReadResult) -> None:
        """Update layer-like summary rows from the latest DXF read result."""
        rows = [
            ("LINE", len(result.lines), "#1769E8", "线段"),
            ("CIRCLE", len(result.circles), "#18A34A", "圆"),
            ("ARC", len(result.arcs), "#F47A00", "圆弧"),
            ("POLYLINE", len(result.polylines), "#14B8A6", "多段线"),
        ]
        visible_rows = [row for row in rows if row[1] > 0] or [("EMPTY", 0, "#94A3B8", "无图元")]
        self.layer_table.setRowCount(len(visible_rows))
        for row_index, (name, count, color, entity_type) in enumerate(visible_rows):
            self._set_table_item(self.layer_table, row_index, 0, name)
            self._set_table_item(self.layer_table, row_index, 1, "●")
            self._set_table_item(self.layer_table, row_index, 2, color)
            self._set_table_item(self.layer_table, row_index, 3, f"{entity_type} {count}")
        self.warning_metric.setText(str(len(result.warnings)))

    def update_generated_summary(self, path_count: int, line_count: int) -> None:
        """Update operation and line metrics after CAM generation."""
        self.line_metric.setText(str(line_count))
        self.operation_table.setRowCount(max(path_count, 1))
        for index in range(max(path_count, 1)):
            self._set_table_item(self.operation_table, index, 0, str(index + 1))
            self._set_table_item(self.operation_table, index, 1, f"轮廓加工 {index + 1}")
            self._set_table_item(self.operation_table, index, 2, "轮廓刀")
            self._set_table_item(self.operation_table, index, 3, "T01")
            self._set_table_item(self.operation_table, index, 4, "✓")

    def update_simulation_summary(
        self,
        parse_result: GCodeParseResult,
        simulation_result: SimulationResult,
        estimated_seconds: float | None = None,
    ) -> None:
        """Update left metric cards from a simulation result."""
        self.path_metric.setText(f"{simulation_result.total_path_length:.3f}\nmm")
        self.line_metric.setText(str(parse_result.total_line_count))
        self.warning_metric.setText(str(len(parse_result.warnings)))
        self.time_metric.setText(_format_seconds(estimated_seconds))

    def _project_tree_group(self) -> QFrame:
        """Return the project tree group."""
        frame = self._group_frame("Project")
        self.project_tree.setObjectName("projectTree")
        self.project_tree.setHeaderHidden(True)
        self.project_tree.clear()
        root = QTreeWidgetItem(["No DXF loaded"])
        root.addChild(QTreeWidgetItem(["Import a DXF file to build CAM operations"]))
        self.project_tree.addTopLevelItem(root)
        root.setExpanded(True)
        frame.layout().addWidget(self.project_tree)  # type: ignore[union-attr]
        return frame

    def _layer_group(self) -> QFrame:
        """Return the DXF layer summary table."""
        frame = self._group_frame("导入DXF")
        self.layer_table.setObjectName("workstationTable")
        self.layer_table.setColumnCount(4)
        self.layer_table.setHorizontalHeaderLabels(["图层", "可见", "颜色", "类型"])
        self.layer_table.verticalHeader().hide()
        self.layer_table.horizontalHeader().setStretchLastSection(True)
        self.layer_table.setAlternatingRowColors(True)
        self.layer_table.setRowCount(4)
        for row, values in enumerate(
            [
                ("0", "●", "#FFFFFF", "轮廓"),
                ("OUTER", "●", "#1769E8", "轮廓"),
                ("POCKET", "●", "#F47A00", "轮廓"),
                ("HOLE", "●", "#18A34A", "圆"),
            ]
        ):
            for col, value in enumerate(values):
                self._set_table_item(self.layer_table, row, col, value)
        frame.layout().addWidget(self.layer_table)  # type: ignore[union-attr]
        return frame

    def _operation_group(self) -> QFrame:
        """Return the operation list table."""
        frame = self._group_frame("工序列表")
        self.operation_table.setObjectName("workstationTable")
        self.operation_table.setColumnCount(5)
        self.operation_table.setHorizontalHeaderLabels(["#", "工序名称", "类型", "刀具", "状态"])
        self.operation_table.verticalHeader().hide()
        self.operation_table.horizontalHeader().setStretchLastSection(True)
        self.operation_table.setAlternatingRowColors(True)
        self.operation_table.setRowCount(5)
        rows = [
            ("1", "外轮廓加工", "轮廓刀", "T01", "✓"),
            ("2", "内轮廓加工", "轮廓刀", "T01", "✓"),
            ("3", "型腔粗加工", "口袋刀", "T02", "✓"),
            ("4", "孔加工", "钻孔", "T03", "✓"),
            ("5", "倒角加工", "倒角刀", "T04", "○"),
        ]
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self._set_table_item(self.operation_table, row, col, value)
        frame.layout().addWidget(self.operation_table)  # type: ignore[union-attr]
        return frame

    def _status_group(self) -> QFrame:
        """Return the status overview metric cards."""
        frame = self._group_frame("状态概览")
        grid = QGridLayout()
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)
        grid.addWidget(self._metric_card("路径长度", self.path_metric, "metricBlue"), 0, 0)
        grid.addWidget(self._metric_card("加工时间", self.time_metric, "metricGreen"), 0, 1)
        grid.addWidget(self._metric_card("警告", self.warning_metric, "metricAmber"), 1, 0)
        grid.addWidget(self._metric_card("G代码行数", self.line_metric, "metricSlate"), 1, 1)
        frame.layout().addLayout(grid)  # type: ignore[union-attr]
        return frame

    def _group_frame(self, title: str) -> QFrame:
        """Create a titled left-panel group."""
        frame = QFrame(self)
        frame.setObjectName("leftPanelGroup")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QLabel(title, frame)
        label.setObjectName("leftGroupTitle")
        layout.addWidget(label)
        return frame

    def _metric_card(self, title: str, value_label: QLabel, object_name: str) -> QFrame:
        """Create one colored metric card."""
        card = QFrame(self)
        card.setObjectName(object_name)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        title_label = QLabel(title, card)
        title_label.setObjectName("metricCardTitle")
        value_label.setObjectName("metricCardValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card

    def _set_table_item(self, table: QTableWidget, row: int, col: int, text: str) -> None:
        """Set one read-only table cell."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, col, item)


class SimulationTimelineWidget(QWidget):
    """Bottom-right simulation timeline and warning log panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create playback controls, progress, metrics, and warning rows."""
        super().__init__(parent)
        self.setObjectName("simulationTimeline")
        self.current_line_label = QLabel("00000 / 0", self)
        self.path_length_label = QLabel("0.000 mm", self)
        self.elapsed_label = QLabel("00:00:00", self)
        self.remaining_label = QLabel("00:00:00", self)
        self.speed_label = QLabel("1.0x", self)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.progress = QProgressBar(self)
        self.warning_table = QTableWidget(self)
        self._runner = None
        self._build_layout()

    def speed_multiplier(self) -> float:
        """Return playback speed multiplier selected by the user."""
        return self.speed_slider.value() / 10.0

    def set_speed_multiplier(self, multiplier: float) -> None:
        """Update the visible speed control from a multiplier."""
        value = max(self.speed_slider.minimum(), min(self.speed_slider.maximum(), int(round(multiplier * 10))))
        self.speed_slider.setValue(value)
        self.speed_label.setText(f"{value / 10.0:.1f}x")

    def update_from_simulation(
        self,
        parse_result: GCodeParseResult,
        simulation_result: SimulationResult,
        estimated_seconds: float | None = None,
    ) -> None:
        """Update timeline information after simulation."""
        self.current_line_label.setText(f"{parse_result.valid_line_count} / {parse_result.total_line_count}")
        self.path_length_label.setText(f"{simulation_result.total_path_length:.3f} mm")
        self.elapsed_label.setText("00:00:00")
        self.remaining_label.setText(_format_seconds(estimated_seconds))
        self.progress.setValue(0)
        self._set_warnings(parse_result.warnings)

    def update_from_dxf(self, result: DxfReadResult) -> None:
        """Show DXF warnings in the bottom log."""
        self.current_line_label.setText("DXF 预览")
        self.path_length_label.setText("不适用")
        self.elapsed_label.setText("00:00:00")
        self.remaining_label.setText("00:00:00")
        self.progress.setValue(0)
        self._set_warnings(result.warnings)

    def _build_layout(self) -> None:
        """Assemble the timeline surface."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame(self)
        header.setObjectName("timelineHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        title = QLabel("仿真时间线", header)
        title.setObjectName("timelineTitle")
        header_layout.addWidget(title)
        button_specs = [("|◀", "btnPrev"), ("▶", "btnPlay"), ("Ⅱ", "btnPause"), ("■", "btnStop"), ("▶|", "btnNext")]
        for text, obj_name in button_specs:
            button = QPushButton(text, header)
            button.setObjectName(obj_name)
            header_layout.addWidget(button)
        header_layout.addStretch(1)
        root.addWidget(header)

        progress_frame = QFrame(self)
        progress_frame.setObjectName("timelineProgressFrame")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(12, 8, 12, 8)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        progress_layout.addWidget(self.progress)

        speed_row = QHBoxLayout()
        self.speed_title = QLabel("\u64ad\u653e\u901f\u5ea6", progress_frame)
        speed_title = self.speed_title
        speed_title.setObjectName("timelineMetricTitle")
        self.speed_slider.setObjectName("speedSlider")
        self.speed_slider.setRange(1, 50)
        self.speed_slider.setValue(10)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setPageStep(5)
        self.speed_label.setObjectName("timelineMetricValue")
        self.speed_label.setMinimumWidth(42)
        speed_row.addWidget(speed_title)
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(self.speed_label)
        progress_layout.addLayout(speed_row)
        root.addWidget(progress_frame)

        metrics = QFrame(self)
        metrics.setObjectName("timelineMetrics")
        metric_layout = QGridLayout(metrics)
        metric_layout.setContentsMargins(8, 6, 8, 6)
        metric_layout.setSpacing(6)
        metric_layout.addWidget(self._metric("当前行", self.current_line_label), 0, 0)
        metric_layout.addWidget(self._metric("路径长度", self.path_length_label), 0, 1)
        metric_layout.addWidget(self._metric("已用时间", self.elapsed_label), 0, 2)
        metric_layout.addWidget(self._metric("预计剩余", self.remaining_label), 0, 3)
        root.addWidget(metrics)

        self.warning_table.setObjectName("warningTable")
        self.warning_table.setColumnCount(1)
        self.warning_table.setHorizontalHeaderLabels(["警告 / 错误日志"])
        self.warning_table.verticalHeader().hide()
        self.warning_table.horizontalHeader().setStretchLastSection(True)
        self.warning_table.setRowCount(1)
        self._set_table_text(0, "暂无警告")
        root.addWidget(self.warning_table, 1)

    def set_runner(self, runner) -> None:
        """Connect the simulation runner to timeline controls."""
        self._runner = runner

    def update_elapsed(self, elapsed_text: str) -> None:
        self.elapsed_label.setText(elapsed_text)

    def update_progress(self, value: int) -> None:
        self.progress.setValue(value)

    def _metric(self, title: str, value_label: QLabel) -> QFrame:
        """Create one timeline metric cell."""
        frame = QFrame(self)
        frame.setObjectName("timelineMetricCell")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 5, 8, 5)
        title_label = QLabel(title, frame)
        title_label.setObjectName("timelineMetricTitle")
        value_label.setObjectName("timelineMetricValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return frame

    def _set_warnings(self, warnings: list[str]) -> None:
        """Update warning table rows."""
        rows = warnings or ["暂无警告"]
        self.warning_table.setRowCount(len(rows))
        for row, warning in enumerate(rows):
            self._set_table_text(row, warning)

    def _set_table_text(self, row: int, text: str) -> None:
        """Set one read-only warning row."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.warning_table.setItem(row, 0, item)
