"""Main window assembly for the CNC CAM and G-code simulator."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QStyle,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.cam_generator import CamGenerator
from core.dxf_reader import DxfReader, DxfReadResult
from core.gcode_parser import GCodeParseResult, GCodeParser
from core.resource_utils import read_text_with_fallback
from core.simulator import GCodeSimulator, SimulationResult
from ui.canvas_widget import SimulationCanvasWidget
from ui.control_panel import ControlPanelWidget
from ui.demo_effect import DemoEffectController
from ui.editor_widget import GCodeEditorWidget
from ui.simulation_3d_canvas_widget import Simulation3DCanvasWidget
from ui.simulation_info_dialog import SimulationInfoDialog
from ui.simulation_runner import SimulationRunner
from ui.style import APP_STYLE
from ui.workstation_panels import ProjectNavigatorWidget, SimulationTimelineWidget



class MainWindow(QMainWindow):
    """Industrial-style desktop shell for CNC CAM and G-code workflows."""

    def __init__(self) -> None:
        """Build the menu bar, work area, parameter panel, and status bar."""
        super().__init__()
        self.setWindowTitle("CNC CAM 与 G代码仿真分析软件")
        self.resize(1280, 820)
        self.setMinimumSize(1100, 720)

        self.editor = GCodeEditorWidget(self)
        self.canvas = SimulationCanvasWidget(self)
        self.control_panel = ControlPanelWidget(self)
        self.project_navigator = ProjectNavigatorWidget(self)
        self.timeline_panel = SimulationTimelineWidget(self)
        self.gcode_parser = GCodeParser()
        self.simulator = GCodeSimulator()
        self.dxf_reader = DxfReader()
        self.cam_generator = CamGenerator()
        self.demo_effects = DemoEffectController(self.canvas)
        # 3D 画布
        self.gl_canvas = Simulation3DCanvasWidget(self)
        # 仿真控制器
        self.simulation_runner = SimulationRunner(self)
        self._simulation_speed = 1.0
        self._latest_parse_result = None
        self._latest_simulation_result = None
        self.current_dxf_result: DxfReadResult | None = None
        self.latest_simulation_info: dict[str, str] | None = None
        self.status_label = QLabel("就绪")

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()
        self._connect_signals()
        self._apply_style()
        # 启动时铺满全屏，避免内容被遮挡
        self.showMaximized()

    def _build_actions(self) -> None:
        """Create reusable actions for menus and future toolbars."""
        self.import_dxf_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),
            "导入DXF",
            self,
        )
        self.import_gcode_action = QAction("导入G代码", self)
        self.save_gcode_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            "保存G代码",
            self,
        )
        self.generate_gcode_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            "生成G代码",
            self,
        )
        self.start_simulation_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay),
            "开始仿真",
            self,
        )
        self.pause_simulation_action = QAction("暂停", self)
        self.reset_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            "重置视图",
            self,
        )
        self.zoom_in_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
            "放大",
            self,
        )
        self.zoom_out_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown),
            "缩小",
            self,
        )
        self.fit_view_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton),
            "适配视图",
            self,
        )
        self.simulation_info_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
            "仿真信息",
            self,
        )
        self.easter_egg_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume),
            "播放彩蛋",
            self,
        )
        self.about_action = QAction("关于软件", self)

    def _build_menu(self) -> None:
        """Create the application menu bar."""
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(self.import_dxf_action)
        file_menu.addAction(self.import_gcode_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_gcode_action)

        simulation_menu = self.menuBar().addMenu("仿真")
        simulation_menu.addAction(self.start_simulation_action)
        simulation_menu.addAction(self.pause_simulation_action)
        simulation_menu.addAction(self.reset_action)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction(self.about_action)

    def _build_toolbar(self) -> None:
        """Create a compact engineering workflow toolbar."""
        toolbar = QToolBar("工程工具栏", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setContentsMargins(4, 4, 4, 4)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        toolbar.addWidget(self._toolbar_button(self.import_dxf_action, "secondaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.save_gcode_action, "secondaryToolButton"))
        toolbar.addSeparator()
        toolbar.addWidget(self._toolbar_button(self.generate_gcode_action, "primaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.start_simulation_action, "primaryToolButton"))
        toolbar.addSeparator()
        toolbar.addWidget(self._toolbar_button(self.reset_action, "secondaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.fit_view_action, "secondaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.simulation_info_action, "secondaryToolButton"))
        toolbar.addSeparator()
        toolbar.addWidget(self._toolbar_button(self.zoom_in_action, "secondaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.zoom_out_action, "secondaryToolButton"))
        toolbar.addWidget(self._toolbar_button(self.easter_egg_action, "secondaryToolButton"))

    def _toolbar_button(self, action: QAction, object_name: str) -> QToolButton:
        """Return one consistent icon-and-text toolbar button."""
        button = QToolButton(self)
        button.setDefaultAction(action)
        button.setObjectName(object_name)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setMinimumHeight(30)
        button.setMinimumWidth(64)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_central_widget(self) -> None:
        """Arrange the CAM workstation as project tree, workbench, and inspector."""
        root = QWidget(self)
        root.setObjectName("centralSurface")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        main_splitter = QSplitter(Qt.Orientation.Horizontal, root)
        main_splitter.setChildrenCollapsible(False)

        self.project_navigator.setMinimumWidth(290)
        self.project_navigator.setMaximumWidth(360)
        self.control_panel.setMinimumWidth(320)
        self.control_panel.setMaximumWidth(390)

        center_splitter = QSplitter(Qt.Orientation.Vertical, main_splitter)
        center_splitter.setChildrenCollapsible(False)

        # 用 QTabWidget 包裹 2D 和 3D 画布
        self.canvas_tabs = QTabWidget()
        self.canvas_tabs.setObjectName("canvasTabs")
        self.canvas_tabs.addTab(self._wrap_panel("二维刀路画布", self.canvas), "二维仿真")
        self.canvas_tabs.addTab(self._wrap_panel("三维刀路画布", self.gl_canvas), "三维仿真")
        center_splitter.addWidget(self.canvas_tabs)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal, center_splitter)
        bottom_splitter.setChildrenCollapsible(False)
        bottom_splitter.addWidget(self._wrap_panel("G代码编辑器", self.editor))
        bottom_splitter.addWidget(self.timeline_panel)
        bottom_splitter.setStretchFactor(0, 55)
        bottom_splitter.setStretchFactor(1, 45)
        bottom_splitter.setSizes([520, 480])

        center_splitter.addWidget(bottom_splitter)
        center_splitter.setStretchFactor(0, 66)
        center_splitter.setStretchFactor(1, 34)
        center_splitter.setSizes([560, 300])

        main_splitter.addWidget(self.project_navigator)
        main_splitter.addWidget(center_splitter)
        main_splitter.addWidget(self.control_panel)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 0)
        main_splitter.setSizes([320, 860, 350])

        root_layout.addWidget(main_splitter, 1)
        self.setCentralWidget(root)

    def _build_status_bar(self) -> None:
        """Create a status bar for current system feedback."""
        status = QStatusBar(self)
        status.addWidget(self.status_label, 1)
        self.setStatusBar(status)

    def _connect_signals(self) -> None:
        """Wire UI actions to first-stage placeholder behavior."""
        self.import_dxf_action.triggered.connect(self._import_dxf)
        self.import_gcode_action.triggered.connect(self._import_gcode)
        self.save_gcode_action.triggered.connect(self._save_gcode)
        self.generate_gcode_action.triggered.connect(self._generate_gcode)
        self.start_simulation_action.triggered.connect(self._start_simulation)
        self.pause_simulation_action.triggered.connect(self._pause_simulation)
        self.reset_action.triggered.connect(self._reset_view)
        self.zoom_in_action.triggered.connect(self.canvas.zoom_in)
        self.zoom_out_action.triggered.connect(self.canvas.zoom_out)
        self.fit_view_action.triggered.connect(self._fit_view)
        self.simulation_info_action.triggered.connect(self._show_simulation_info)
        self.easter_egg_action.triggered.connect(self._play_easter_egg)
        self.about_action.triggered.connect(self._show_about)

        # SimulationRunner 信号
        self.simulation_runner.position_updated.connect(self._on_runner_position_updated)
        self.simulation_runner.line_changed.connect(self._on_runner_line_changed)
        self.simulation_runner.progress_changed.connect(self._on_runner_progress_changed)
        self.simulation_runner.state_changed.connect(self._on_runner_state_changed)
        self.simulation_runner.coordinate_updated.connect(self._on_runner_coordinate_updated)
        self.simulation_runner.segment_updated.connect(self._on_runner_segment_updated)
        self.simulation_runner.time_updated.connect(self._on_runner_time_updated)
        # 连接时间线按钮
        self._connect_timeline_buttons()

    def _wrap_panel(self, title: str, content: QWidget) -> QFrame:
        """Wrap a main work widget with a consistent panel title."""
        frame = QFrame(self)
        frame.setObjectName("workPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        label = QLabel(title, frame)
        label.setObjectName("panelTitle")
        label.setFixedHeight(22)
        layout.addWidget(label)
        layout.addWidget(content, 1)
        return frame

    def _import_dxf(self) -> None:
        """Select, read, and preview a DXF file on the canvas."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入DXF文件",
            "",
            "DXF 文件 (*.dxf);;所有文件 (*.*)",
        )
        if not file_path:
            self._set_status("已取消导入DXF")
            return
        self._load_dxf_file(Path(file_path))

    def _load_dxf_file(self, file_path: Path) -> None:
        """Read one DXF file and update the drawing preview."""
        try:
            result = self.dxf_reader.read(file_path)
        except ValueError as exc:
            message = str(exc)
            self.current_dxf_result = None
            QMessageBox.warning(self, "DXF导入失败", message)
            self._set_status(f"DXF导入失败：{message}")
            return

        self.control_panel.set_available_layers(result.layers)
        self._update_dxf_info(result)
        self.project_navigator.update_project_file(file_path, result)
        self.project_navigator.update_dxf_result(result)
        self.timeline_panel.update_from_dxf(result)
        if result.entity_count == 0:
            self.canvas.reset_view()
            self.current_dxf_result = result
            self._set_status("DXF中未发现支持的图元")
            return

        self.current_dxf_result = result
        self.canvas.draw_dxf_geometry(result)
        warning_text = f"，警告 {len(result.warnings)} 条" if result.warnings else ""
        self._set_status(f"DXF导入成功：{result.summary()}{warning_text}")

    def _import_gcode(self) -> None:
        """Load a G-code text file into the editor."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入G代码文件",
            "",
            "G代码文件 (*.nc *.gcode *.tap *.txt);;所有文件 (*.*)",
        )
        if not file_path:
            self._set_status("已取消导入G代码")
            return
        try:
            content = read_text_with_fallback(Path(file_path))
        except UnicodeDecodeError as exc:
            QMessageBox.warning(self, "\u5bfc\u5165\u5931\u8d25", f"\u6587\u4ef6\u7f16\u7801\u65e0\u6cd5\u8bc6\u522b\uff1a{exc}")
            self._set_status("G\u4ee3\u7801\u5bfc\u5165\u5931\u8d25")
            return
        except OSError as exc:
            QMessageBox.warning(self, "导入失败", f"无法读取文件：{exc}")
            self._set_status("G代码导入失败")
            return

        self.editor.set_text(content)
        self._set_status(f"已导入G代码：{Path(file_path).name}")

    def _generate_gcode(self) -> None:
        """Generate Fanuc-style G-code from the currently imported DXF geometry."""
        if self.current_dxf_result is None:
            self._set_status("请先导入DXF图纸")
            return
        if self.current_dxf_result.entity_count == 0:
            self._set_status("未发现可生成刀路的图元")
            return

        try:
            parameters = self.control_panel.parameters()
            generated = self.cam_generator.generate(
                self.current_dxf_result,
                parameters,
            )
        except ValueError as exc:
            message = str(exc)
            if "未发现可生成刀路的图元" in message:
                self._set_status("未发现可生成刀路的图元")
            else:
                self._set_status(f"CAM参数错误：{message}")
            return
        except (RuntimeError, OSError) as exc:
            QMessageBox.warning(self, "G代码生成失败", f"生成过程中发生错误：{exc}")
            self._set_status("G代码生成失败")
            return

        self.editor.set_text(generated.text)
        self.project_navigator.update_generated_summary(generated.path_count, generated.line_count)
        self.control_panel.mode_label.setText(f"{self._short_mode(generated.machining_mode)} G代码生成")
        self.control_panel.parse_status_label.setText("已生成")
        self.control_panel.current_line_label.setText(
            f"轮廓 {generated.path_count} 条 / 代码 {generated.line_count} 行"
        )
        self._set_status(
            f"G代码生成成功：模式：{self._short_mode(generated.machining_mode)}，"
            f"轮廓数：{generated.path_count}，"
            f"图元数：{generated.entity_count}，"
            f"代码行数：{generated.line_count}，"
            f"是否归零：{'是' if generated.zero_origin else '否'}"
        )

    def _save_gcode(self) -> None:
        """Save the current editor content to a selected file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存G代码文件",
            "",
            "G代码文件 (*.nc);;文本文件 (*.txt);;所有文件 (*.*)",
        )
        if not file_path:
            self._set_status("已取消保存G代码")
            return
        try:
            Path(file_path).write_text(self.editor.text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", f"无法保存文件：{exc}")
            self._set_status("G代码保存失败")
            return

        self._set_status(f"已保存G代码：{Path(file_path).name}")

    def _start_simulation(self) -> None:
        """Parse editor G-code, simulate tool paths, and update the canvas."""
        self.pause_simulation_action.setText("暂停")
        if not self.editor.text().strip():
            # 无内容时彻底清空旧仿真，确保 runner 不残留播放状态或旧路径
            self.simulation_runner.clear()
            self.gl_canvas.stop_animation()
            self.canvas.reset_view()
            self.gl_canvas.load_toolpath_3d([])
            self.control_panel.parse_status_label.setText("未解析")
            self.latest_simulation_info = None
            self._set_status("没有可仿真的G代码")
            return

        try:
            parse_result = self.gcode_parser.parse(self.editor.text())
            simulation_result = self.simulator.simulate(
                parse_result,
                plane=self._simulation_plane_from_result(parse_result),
                honor_program_plane=False,
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "仿真失败", f"仿真过程中发生错误：{exc}")
            self.simulation_runner.clear()
            self.gl_canvas.stop_animation()
            self.control_panel.parse_status_label.setText("失败")
            self.latest_simulation_info = None
            self._set_status("G代码仿真失败")
            return

        self._update_simulation_info(parse_result, simulation_result)
        if not parse_result.commands:
            # 无有效命令时彻底清空旧仿真
            self.simulation_runner.clear()
            self.gl_canvas.stop_animation()
            self.canvas.reset_view()
            self.gl_canvas.load_toolpath_3d([])
            self.latest_simulation_info = None
            self._set_status("没有可仿真的G代码")
            return
        if parse_result.motion_count == 0:
            # 只有设置指令（G21/G90/M3 等），清空旧仿真
            self.simulation_runner.clear()
            self.gl_canvas.stop_animation()
            self.canvas.reset_view()
            self.gl_canvas.load_toolpath_3d([])
            self.latest_simulation_info = None
            self._set_status("未发现运动指令")
            return

        self.canvas.draw_toolpath(simulation_result)

        # 保存仿真结果供 3D 视图使用
        self._latest_parse_result = parse_result
        self._latest_simulation_result = simulation_result

        # 加载到仿真控制器
        # Load the runner before updating summary panels so all time displays use the
        # same feed-based duration model.
        self.simulation_runner.load(parse_result, simulation_result)
        estimated_seconds = self.simulation_runner.total_duration()
        self.project_navigator.update_simulation_summary(
            parse_result,
            simulation_result,
            estimated_seconds=estimated_seconds,
        )
        self.timeline_panel.update_from_simulation(
            parse_result,
            simulation_result,
            estimated_seconds=estimated_seconds,
        )

        # Load 2D segment metadata first, then let real machine coordinates define the 3D scene.
        self.gl_canvas.load_toolpath(simulation_result.segments, simulation_result.plane)
        real_positions = self.simulation_runner.get_real_positions()
        self.gl_canvas.load_toolpath_3d(
            real_positions,
            is_turning=(simulation_result.plane == "XZ"),
        )

        # 自动开始仿真动画
        self._simulation_speed = self.timeline_panel.speed_multiplier()
        self.simulation_runner.set_speed(self._simulation_speed)
        self.simulation_runner.play()
        self.gl_canvas.start_animation()

        self._set_status(self._simulation_status_text(parse_result, simulation_result))

    def _play_easter_egg(self) -> None:
        """Play optional demo image and audio effects from the quick action panel."""
        effect_messages = self._run_demo_effects()
        if effect_messages:
            self._set_status("；".join(effect_messages))
            return
        self._set_status("彩蛋已播放")

    def _on_runner_position_updated(self, x: float, y: float, z: float, segment_index: int) -> None:
        """Update 3D and 2D current cutter position markers."""
        plane = self._latest_simulation_result.plane if self._latest_simulation_result else "XY"
        self.gl_canvas.update_tool_position(x, y, z, segment_index)
        self.canvas.set_simulation_position(x, y, z, plane=plane)
        if plane == "XZ":
            self.control_panel.current_position_label.setText(f"X{x:.3f}  Z{z:.3f}")
        else:
            self.control_panel.current_position_label.setText(f"X{x:.3f}  Y{y:.3f}  Z{z:.3f}")

    def _on_runner_line_changed(self, line_number: int) -> None:
        """Highlight the current G-code line in the editor."""
        self.editor._editor.highlight_line(line_number)

    def _on_runner_progress_changed(self, progress: float) -> None:
        """Update progress bar and cut progress."""
        self.gl_canvas.update_cut_progress(progress)
        self.timeline_panel.update_progress(int(progress * 100))

    def _on_runner_state_changed(self, state: str) -> None:
        """Update UI controls according to simulation state."""
        if state == "finished":
            self.gl_canvas.stop_animation()
            self.gl_canvas.update_cut_progress(1.0)
            self.gl_canvas.update()
            self.pause_simulation_action.setText("暂停")
            self._set_status("仿真播放完成")
        elif state == "idle":
            self.gl_canvas.stop_animation()
            self.pause_simulation_action.setText("暂停")
            self._set_status("仿真已停止")

    def _on_runner_coordinate_updated(self, text: str) -> None:
        """Update control panel coordinate display."""
        self.control_panel.current_position_label.setText(text)

    def _on_runner_segment_updated(self, text: str) -> None:
        """Update current segment info on the status bar."""
        self.timeline_panel.current_line_label.setText(text.split("|")[0].strip() if "|" in text else text)
        self._set_status(f"正在执行: {text}")

    def _on_runner_time_updated(self, elapsed_text: str, remaining_text: str) -> None:
        """Update timeline elapsed/remaining time display."""
        self.timeline_panel.update_elapsed(elapsed_text)
        self.timeline_panel.remaining_label.setText(remaining_text)

    def _connect_timeline_buttons(self) -> None:
        """Connect timeline playback buttons to the simulation runner."""
        btn_prev = self.timeline_panel.findChild(QPushButton, "btnPrev")
        btn_play = self.timeline_panel.findChild(QPushButton, "btnPlay")
        btn_pause = self.timeline_panel.findChild(QPushButton, "btnPause")
        btn_stop = self.timeline_panel.findChild(QPushButton, "btnStop")
        btn_next = self.timeline_panel.findChild(QPushButton, "btnNext")

        if btn_prev:
            btn_prev.clicked.connect(self.simulation_runner.step_backward)
        if btn_play:
            btn_play.clicked.connect(self.simulation_runner.play)
            btn_play.clicked.connect(self.gl_canvas.start_animation)
        if btn_pause:
            btn_pause.clicked.connect(self.simulation_runner.pause)
            btn_pause.clicked.connect(self.gl_canvas.stop_animation)
        if btn_stop:
            btn_stop.clicked.connect(self.simulation_runner.stop)
        if btn_next:
            btn_next.clicked.connect(self.simulation_runner.step_forward)
        self.timeline_panel.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        self._on_speed_slider_changed(self.timeline_panel.speed_slider.value())

    def _on_speed_slider_changed(self, value: int) -> None:
        """Apply user-selected playback speed to the simulation runner."""
        self._simulation_speed = max(0.1, value / 10.0)
        self.timeline_panel.speed_label.setText(f"{self._simulation_speed:.1f}x")
        self.simulation_runner.set_speed(self._simulation_speed)

    def _pause_simulation(self) -> None:
        if self.simulation_runner.is_playing():
            self.simulation_runner.pause()
            self.gl_canvas.stop_animation()
            self.pause_simulation_action.setText("继续")
            return
        # 没有仿真数据时禁止进入播放状态
        if self.simulation_runner.total_duration() <= 0:
            self._set_status("没有可播放的仿真数据")
            return
        self.simulation_runner.play()
        self.gl_canvas.start_animation()
        self.pause_simulation_action.setText("暂停")

    def _reset_view(self) -> None:
        """Restore the canvas to its latest automatic view range."""
        self.canvas.fit_to_content()
        self.gl_canvas.reset_view()
        self._set_status("视图已恢复到自动适配范围")

    def _fit_view(self) -> None:
        """Fit the canvas to the latest generated or imported content."""
        self.canvas.fit_to_content()
        self._set_status("画布已适配当前内容")

    def _show_simulation_info(self) -> None:
        """Open the latest simulation information in a modal dialog."""
        dialog = SimulationInfoDialog(self.latest_simulation_info, self)
        dialog.exec()

    def _show_about(self) -> None:
        """Show basic project information."""
        QMessageBox.information(
            self,
            "关于软件",
            "CNC CAM 与 G代码仿真分析软件\n\n"
            "Version 1.0\n\n"
            "功能：\n"
            "DXF解析\n"
            "车削CAM\n"
            "铣削CAM\n"
            "G代码生成\n"
            "G代码仿真\n"
            "G2/G3支持\n"
            "EXE部署支持",
        )

    def _update_simulation_info(
        self,
        parse_result: GCodeParseResult,
        simulation_result: SimulationResult,
    ) -> None:
        """Update the bottom information panel from parser and simulator output."""
        position = simulation_result.final_position
        self.control_panel.current_position_label.setText(
            f"X{position.x:.3f}  Y{position.y:.3f}  Z{position.z:.3f}"
        )
        self.control_panel.current_line_label.setText(self._current_line_text(parse_result))
        self.control_panel.path_length_label.setText(
            f"{simulation_result.total_path_length:.3f} mm"
        )
        self.control_panel.parse_status_label.setText(
            "有警告" if parse_result.warnings else "成功"
        )
        if simulation_result.plane == "XZ":
            self.control_panel.current_position_label.setText(
                f"X{position.x:.3f}  Z{position.z:.3f}"
            )
            self.control_panel.mode_label.setText("车削仿真")
        else:
            self.control_panel.mode_label.setText("铣削仿真")
        self.control_panel.entity_count_label.setText("0")
        self.control_panel.drawing_bounds_label.setText("无")
        self.latest_simulation_info = self._simulation_info_dict(parse_result, simulation_result)

    def _update_dxf_info(self, result: DxfReadResult) -> None:
        """Update the bottom information panel for DXF preview mode."""
        self.control_panel.current_position_label.setText("当前模式 DXF图纸预览")
        self.control_panel.current_line_label.setText("DXF图纸预览")
        self.control_panel.path_length_label.setText("不适用")
        self.control_panel.parse_status_label.setText(
            "有警告" if result.warnings else "成功"
        )
        self.control_panel.mode_label.setText("DXF图纸预览")
        self.control_panel.entity_count_label.setText(str(result.entity_count))
        self.control_panel.drawing_bounds_label.setText(self._dxf_bounds_text(result))

    def _current_line_text(self, result: GCodeParseResult) -> str:
        """Format parsed line counts for the information panel."""
        if not result.commands:
            return "无有效G代码"
        return f"有效 {result.valid_line_count} / 总 {result.total_line_count} 行"

    def _current_command_text(self, result: GCodeParseResult) -> str:
        """Format the last parsed command line for the simulation info dialog."""
        if not result.commands:
            return "无有效G代码"
        command = result.commands[-1]
        return f"第 {command.line_number} 行 / {command.raw_line}"

    def _simulation_info_dict(
        self,
        parse_result: GCodeParseResult,
        simulation_result: SimulationResult,
    ) -> dict[str, str]:
        """Build the latest simulation information for the dialog."""
        position = simulation_result.final_position
        if simulation_result.plane == "XZ":
            coordinate_text = f"X{position.x:.3f}  Z{position.z:.3f}"
            mode_text = "车削仿真"
        else:
            coordinate_text = f"X{position.x:.3f}  Y{position.y:.3f}  Z{position.z:.3f}"
            mode_text = "铣削仿真"

        entity_count = self.current_dxf_result.entity_count if self.current_dxf_result else 0
        drawing_bounds = self._dxf_bounds_text(self.current_dxf_result) if self.current_dxf_result else "无"
        return {
            "当前坐标": coordinate_text,
            "当前行": self._current_command_text(parse_result),
            "路径长度": f"{simulation_result.total_path_length:.3f} mm",
            "解析状态": "有警告" if parse_result.warnings else "成功",
            "当前模式": mode_text,
            "图元数量": str(entity_count),
            "图纸范围": drawing_bounds,
            "代码行数": f"有效 {parse_result.valid_line_count} / 总 {parse_result.total_line_count} 行",
            "警告数量": str(len(parse_result.warnings)),
        }

    def _dxf_bounds_text(self, result: DxfReadResult) -> str:
        """Format DXF bounds for the information panel."""
        if result.bounds is None:
            return "无"
        min_x, min_y, max_x, max_y = result.bounds
        return f"X{min_x:.3f}~{max_x:.3f}  Y{min_y:.3f}~{max_y:.3f}"


    def _current_simulation_plane(self) -> str:
        """Return the plot plane implied by the current machining mode."""
        return "XZ" if self.control_panel.parameters().machining_mode == "车削模式" else "XY"

    def _simulation_plane_from_result(self, _parse_result: GCodeParseResult) -> str:
        """Use the selected UI machining mode as the authoritative simulation plane."""
        return self._current_simulation_plane()

    def _short_mode(self, machining_mode: str) -> str:
        """Return a compact machining mode label for status messages."""
        return "车削" if machining_mode == "车削模式" else "铣削"

    def _simulation_status_text(
        self,
        parse_result: GCodeParseResult,
        simulation_result: SimulationResult,
    ) -> str:
        """Format the status bar text for a completed simulation."""
        warning_text = (
            f"存在 {len(parse_result.warnings)} 条警告"
            if parse_result.warnings
            else "警告 0 条"
        )
        return (
            "仿真完成："
            f"运动指令 {parse_result.motion_count} 条，"
            f"路径长度 {simulation_result.total_path_length:.3f} mm，"
            f"{warning_text}"
        )

    def _set_status(self, message: str) -> None:
        """Update both the status label and the Qt status tip area."""
        self.status_label.setText(message)
        self.statusBar().showMessage(message, 5000)

    def _run_demo_effects(self) -> list[str]:
        """Trigger optional image/audio effects without interrupting the workflow."""
        try:
            return self.demo_effects.play_easter_egg()
        except (RuntimeError, OSError) as exc:
            return [f"演示效果已跳过：{exc}"]

    def _apply_style(self) -> None:
        """Apply a clean industrial software look with readable contrast."""
        self.setStyleSheet(APP_STYLE)
