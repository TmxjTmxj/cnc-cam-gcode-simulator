"""Shared visual theme for the CNC CAM desktop application.

极简技术风主题 —— 对齐 ``cnc-cam-ui-concept/pages/technical-minimal.html`` 设计概念，
灵感来自 SolidWorks / Fusion 360：浅灰背景 + 钢蓝主色 + 零圆角 + 紧凑布局 + 等宽字体。
"""

from __future__ import annotations


# 设计概念调色板（与 technical-minimal.html :root 变量一致）
COLORS = {
    "primary": "#4682B4",
    "primary_hover": "#3A6F9E",
    "secondary": "#E8ECF0",
    "background": "#E8ECF0",
    "surface": "#F4F6F8",
    "elevated": "#FFFFFF",
    "inset": "#DDE1E5",
    "hover": "#E0E4E8",
    "active": "#CDD3D9",
    "border": "#B0B8C0",
    "border_subtle": "#C8CED4",
    "text": "#1A1E22",
    "text_secondary": "#4A5058",
    "text_tertiary": "#7A828A",
    "muted": "#7A828A",
    "success": "#3D8B37",
    "warning": "#B8860B",
    "danger": "#C0392B",
    # CNC 专用色
    "cnc_rapid": "#808890",
    "cnc_linear": "#4682B4",
    "cnc_arc": "#CC6600",
    "cnc_tool": "#B8860B",
    "cnc_stock": "#5B9BD5",
    "cnc_start": "#3D8B37",
    "cnc_end": "#C0392B",
}


APP_STYLE = """
/* ==================== 全局基底 ==================== */
QMainWindow {
    background: #E8ECF0;
    color: #1A1E22;
    font-family: "Source Sans 3", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 12px;
}
QDialog {
    background: #E8ECF0;
    color: #1A1E22;
    font-family: "Source Sans 3", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 12px;
}
QWidget#centralSurface {
    background: #E8ECF0;
}

/* ==================== 菜单栏（24px，文字不被裁切） ==================== */
QMenuBar {
    background: #DDE1E5;
    color: #4A5058;
    padding: 0;
    margin: 0;
    font-size: 12px;
    font-family: "Source Sans 3", "Segoe UI", "Microsoft YaHei", sans-serif;
    border-bottom: 1px solid #B0B8C0;
    min-height: 26px;
}
QMenuBar::item {
    padding: 4px 10px;
    background: transparent;
    color: #4A5058;
}
QMenuBar::item:selected {
    background: #CDD3D9;
    color: #1A1E22;
}

/* ==================== 工具栏（36px） ==================== */
QToolBar#mainToolbar {
    background: #DDE1E5;
    border: none;
    border-bottom: 2px solid #B0B8C0;
    spacing: 2px;
    padding: 4px 6px;
    min-height: 40px;
}
QToolBar#mainToolbar::separator {
    background: #B0B8C0;
    width: 1px;
    margin: 0 3px;
}
QToolButton#primaryToolButton,
QToolButton#secondaryToolButton {
    border-radius: 0;
    padding: 0 10px;
    font-weight: 600;
    font-size: 12px;
    min-width: 60px;
    margin: 0;
}
QToolButton#primaryToolButton {
    background: #4682B4;
    border: 1px solid #3A6F9E;
    color: #FFFFFF;
    font-weight: 600;
}
QToolButton#primaryToolButton:hover {
    background: #3A6F9E;
}
QToolButton#secondaryToolButton {
    background: #F4F6F8;
    border: 1px solid #B0B8C0;
    color: #4A5058;
}
QToolButton#secondaryToolButton:hover {
    background: #E0E4E8;
    color: #1A1E22;
}

/* ==================== 菜单弹出 ==================== */
QMenu {
    background: #FFFFFF;
    border: 1px solid #B0B8C0;
    padding: 2px;
}
QMenu::item {
    padding: 4px 24px 4px 16px;
    color: #4A5058;
    border-radius: 0;
}
QMenu::item:selected {
    background: #DCEAF5;
    color: #1A1E22;
}
QMenu::separator {
    background: #C8CED4;
    height: 1px;
    margin: 2px 8px;
}

/* ==================== 面板与分组 ==================== */
QFrame#workPanel, QGroupBox {
    background: #F4F6F8;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QFrame#workPanel {
    margin: 0;
}
QFrame#welcomeCard, QFrame#loginCard, QFrame#infoCard {
    background: #FFFFFF;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QLabel#panelTitle {
    color: #4A5058;
    font-size: 11px;
    font-weight: 700;
    padding: 0 4px;
    text-transform: uppercase;
    font-family: "Source Code Pro", "Consolas", "Microsoft YaHei", monospace;
    letter-spacing: 0.5px;
}

/* ==================== 欢迎卡 ==================== */
QLabel#welcomeTitle, QLabel#loginTitle {
    color: #1A1E22;
    font-size: 22px;
    font-weight: 700;
}
QLabel#dialogTitle {
    color: #1A1E22;
    font-size: 17px;
    font-weight: 700;
}
QLabel#emptyStateLabel {
    color: #7A828A;
    font-size: 14px;
    font-weight: 600;
}
QLabel#welcomeSubtitle, QLabel#loginSubtitle {
    color: #4A5058;
    font-size: 13px;
    font-weight: 400;
}
QLabel#welcomeFeature {
    color: #1A1E22;
    font-size: 12px;
    font-weight: 600;
    padding: 3px 0;
}
QLabel#welcomeHint {
    color: #4682B4;
    font-size: 13px;
    font-weight: 600;
}
QLabel#loginStatus {
    color: #C0392B;
    font-size: 11px;
    font-weight: 500;
}

/* ==================== G代码编辑器（黑底） ==================== */
QPlainTextEdit#gcodeEditor {
    background: #000000;
    color: #E0E0E0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
    padding: 4px;
    selection-background-color: #4682B4;
    selection-color: #FFFFFF;
    line-height: 135%;
    font-family: "Source Code Pro", "Consolas", monospace;
    font-size: 11px;
}
QPlainTextEdit#gcodeEditor QScrollBar:vertical,
QPlainTextEdit#gcodeEditor QScrollBar:horizontal {
    background: #F4F6F8;
    border: none;
    width: 10px;
    height: 10px;
}
QPlainTextEdit#gcodeEditor QScrollBar::handle {
    background: #B0B8C0;
    border-radius: 0;
}
QPlainTextEdit#gcodeEditor QScrollBar::handle:hover {
    background: #808890;
}
QPlainTextEdit#gcodeEditor QScrollBar::add-line,
QPlainTextEdit#gcodeEditor QScrollBar::sub-line {
    width: 0;
    height: 0;
}

/* ==================== 控制面板 ==================== */
QWidget#controlPanel {
    background: #E8ECF0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QScrollArea#parameterScrollArea {
    background: transparent;
    border: none;
}
QScrollArea#parameterScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollArea {
    background: transparent;
    border: none;
}

/* ==================== 分组框 ==================== */
QGroupBox {
    margin-top: 6px;
    padding: 6px 4px 4px 4px;
    font-weight: 700;
    color: #4A5058;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #4A5058;
    background: #F4F6F8;
    font-family: "Source Code Pro", "Consolas", "Microsoft YaHei", monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ==================== 表单标签与值 ==================== */
QLabel#formLabel {
    color: #7A828A;
    font-size: 10px;
    font-weight: 500;
    font-family: "Source Code Pro", "Consolas", monospace;
}
QLabel#metricTitle {
    color: #7A828A;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    font-family: "Source Code Pro", "Consolas", monospace;
    letter-spacing: 0.3px;
}
QLabel#metricValue {
    color: #1A1E22;
    font-weight: 700;
    font-size: 12px;
    font-family: "Source Code Pro", "Consolas", monospace;
}
QFrame#metricCard {
    background: #E8ECF0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}

/* ==================== 输入控件 ==================== */
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {
    min-height: 22px;
    border: 1px solid #B0B8C0;
    border-radius: 0;
    padding: 0 4px;
    background: #FFFFFF;
    color: #1A1E22;
    font-family: "Source Code Pro", "Consolas", monospace;
    font-size: 11px;
    selection-background-color: #DCEAF5;
}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #4682B4;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background: #DDE1E5;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: #CDD3D9;
}
QComboBox::drop-down {
    border: none;
    width: 18px;
    background: #DDE1E5;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #B0B8C0;
    color: #1A1E22;
    selection-background-color: #DCEAF5;
    selection-color: #4682B4;
    outline: none;
    padding: 2px;
}
QCheckBox {
    color: #4A5058;
    font-weight: 400;
    spacing: 4px;
    font-size: 11px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #B0B8C0;
    border-radius: 0;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #4682B4;
    border-color: #4682B4;
}

/* ==================== 按钮 ==================== */
QPushButton {
    min-height: 24px;
    padding: 0 10px;
    border-radius: 0;
    font-weight: 600;
    font-size: 12px;
}
QPushButton#primaryButton {
    border: 1px solid #3A6F9E;
    background: #4682B4;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background: #3A6F9E;
}
QPushButton#secondaryButton {
    border: 1px solid #B0B8C0;
    background: #F4F6F8;
    color: #4A5058;
}
QPushButton#secondaryButton:hover {
    background: #E0E4E8;
    color: #1A1E22;
}
QPushButton#easterButton {
    border: 1px solid #B0B8C0;
    background: #F4F6F8;
    color: #7A828A;
    font-weight: 400;
}
QPushButton#easterButton:hover {
    background: #E0E4E8;
    color: #4A5058;
}

/* ==================== 状态栏（24px） ==================== */
QStatusBar {
    background: #DDE1E5;
    color: #4A5058;
    border-top: 2px solid #B0B8C0;
    font-family: "Source Code Pro", "Consolas", monospace;
    font-size: 10px;
    padding: 0 8px;
    min-height: 24px;
}
QStatusBar::item {
    border: none;
}

/* ==================== 分割器 ==================== */
QSplitter::handle {
    background: #B0B8C0;
    width: 2px;
    height: 2px;
}
QSplitter::handle:hover {
    background: #4682B4;
}

/* ==================== 检查器标题 ==================== */
QLabel#inspectorTitle {
    color: #4682B4;
    font-size: 14px;
    font-weight: 700;
    padding: 4px 2px 6px 2px;
    border-bottom: 1px solid #B0B8C0;
    font-family: "Source Code Pro", "Consolas", "Microsoft YaHei", monospace;
}
QWidget#inspectorMetricCard {
    background: #E8ECF0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}

/* ==================== 项目导航器 ==================== */
QWidget#projectNavigator {
    background: #E8ECF0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QFrame#leftPanelGroup {
    background: #F4F6F8;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QLabel#leftGroupTitle {
    background: #DDE1E5;
    color: #4A5058;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-bottom: 1px solid #B0B8C0;
    font-family: "Source Code Pro", "Consolas", "Microsoft YaHei", monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ==================== 树与表 ==================== */
QTreeWidget#projectTree {
    background: #FFFFFF;
    border: none;
    color: #1A1E22;
    outline: none;
    font-size: 12px;
    alternate-background-color: #F4F6F8;
}
QTreeWidget#projectTree::item {
    min-height: 20px;
    padding: 1px 0;
    border-bottom: 1px solid #C8CED4;
}
QTreeWidget#projectTree::item:selected {
    background: #DCEAF5;
    color: #4682B4;
}
QTreeWidget#projectTree::branch:has-siblings:!adjoins-item {
    background: #FFFFFF;
}
QTreeWidget#projectTree::branch:has-siblings:adjoins-item {
    background: #FFFFFF;
}
QTreeWidget#projectTree::branch:!has-children:!has-siblings:adjoins-item {
    background: #FFFFFF;
}
QTreeWidget#projectTree::branch:has-children:!has-siblings:closed,
QTreeWidget#projectTree::branch:closed:has-children:has-siblings {
    background: #FFFFFF;
    border-image: none;
    image: none;
}
QTreeWidget#projectTree::branch:open:has-children:!has-siblings,
QTreeWidget#projectTree::branch:open:has-children:has-siblings {
    background: #FFFFFF;
    border-image: none;
    image: none;
}

QTableWidget#workstationTable,
QTableWidget#warningTable {
    background: #FFFFFF;
    alternate-background-color: #F4F6F8;
    border: 1px solid #B0B8C0;
    gridline-color: #C8CED4;
    color: #1A1E22;
    selection-background-color: #DCEAF5;
    selection-color: #4682B4;
    font-size: 11px;
}
QTableWidget#workstationTable::item,
QTableWidget#warningTable::item {
    padding: 1px 4px;
}
QHeaderView::section {
    background: #DDE1E5;
    color: #4A5058;
    border: none;
    border-right: 1px solid #B0B8C0;
    border-bottom: 1px solid #B0B8C0;
    padding: 2px 6px;
    font-weight: 700;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-family: "Source Code Pro", "Consolas", monospace;
}

/* ==================== 指标卡片 ==================== */
QFrame#metricBlue,
QFrame#metricGreen,
QFrame#metricAmber,
QFrame#metricSlate {
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QFrame#metricBlue {
    background: rgba(70, 130, 180, 0.08);
    color: #4682B4;
}
QFrame#metricGreen {
    background: rgba(61, 139, 55, 0.08);
    color: #3D8B37;
}
QFrame#metricAmber {
    background: rgba(184, 134, 11, 0.08);
    color: #B8860B;
}
QFrame#metricSlate {
    background: rgba(91, 155, 213, 0.08);
    color: #5B9BD5;
}
QLabel#metricCardTitle {
    color: #7A828A;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-family: "Source Code Pro", "Consolas", monospace;
}
QLabel#metricCardValue {
    font-size: 16px;
    font-weight: 700;
    color: #1A1E22;
    font-family: "Source Code Pro", "Consolas", monospace;
}

/* ==================== 仿真时间线 ==================== */
QWidget#simulationTimeline {
    background: #F4F6F8;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QFrame#timelineHeader {
    background: #DDE1E5;
    border-bottom: 1px solid #B0B8C0;
}
QLabel#timelineTitle {
    color: #4A5058;
    font-size: 11px;
    font-weight: 700;
    font-family: "Source Code Pro", "Consolas", "Microsoft YaHei", monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QPushButton#timelineButton {
    min-height: 22px;
    min-width: 28px;
    border: 1px solid #B0B8C0;
    border-radius: 0;
    background: #DDE1E5;
    color: #4A5058;
    padding: 0 8px;
    font-size: 11px;
}
QPushButton#timelineButton:hover {
    background: #E0E4E8;
    color: #1A1E22;
}
QPushButton#btnPlay {
    background: #4682B4;
    color: #FFFFFF;
    border: 1px solid #3A6F9E;
    font-weight: 600;
}
QPushButton#btnPlay:hover {
    background: #3A6F9E;
}
QFrame#timelineProgressFrame,
QFrame#timelineMetrics {
    background: #F4F6F8;
    border-bottom: 1px solid #B0B8C0;
}

/* ==================== 进度条 ==================== */
QProgressBar {
    border: 1px solid #B0B8C0;
    border-radius: 0;
    background: #DDE1E5;
    color: #1A1E22;
    text-align: center;
    font-weight: 600;
    font-size: 10px;
    min-height: 14px;
}
QProgressBar::chunk {
    background: #4682B4;
    border-radius: 0;
}

/* ==================== 时间线指标格 ==================== */
QFrame#timelineMetricCell {
    background: #E8ECF0;
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QLabel#timelineMetricTitle {
    color: #7A828A;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-family: "Source Code Pro", "Consolas", monospace;
}
QLabel#timelineMetricValue {
    color: #1A1E22;
    font-size: 12px;
    font-weight: 700;
    font-family: "Source Code Pro", "Consolas", monospace;
}

/* ==================== 滑块 ==================== */
QSlider::groove:horizontal {
    background: #DDE1E5;
    border: 1px solid #B0B8C0;
    height: 4px;
    border-radius: 0;
}
QSlider::sub-page:horizontal {
    background: #4682B4;
    border-radius: 0;
}
QSlider::handle:horizontal {
    background: #4682B4;
    border: 2px solid #FFFFFF;
    width: 10px;
    margin: -5px 0;
    border-radius: 0;
}
QSlider::handle:horizontal:hover {
    background: #3A6F9E;
}

/* ==================== 画布标签页 ==================== */
QTabWidget#canvasTabs::pane {
    border: none;
    background: transparent;
}
QTabWidget#canvasTabs QTabBar::tab {
    background: #E0E4E8;
    color: #4A5058;
    border: 1px solid #B0B8C0;
    border-bottom: none;
    padding: 4px 14px;
    font-weight: 600;
    font-size: 11px;
    margin-right: 0;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
}
QTabWidget#canvasTabs QTabBar::tab:selected {
    background: #F4F6F8;
    color: #1A1E22;
    border-top: 2px solid #4682B4;
    font-weight: 600;
}
QTabWidget#canvasTabs QTabBar::tab:hover {
    background: #DDE1E5;
    color: #1A1E22;
}

/* ==================== 画布图例覆盖层 ==================== */
QFrame#canvasLegend {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid #B0B8C0;
    border-radius: 0;
}
QLabel#legendTitle {
    color: #7A828A;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-family: "Source Code Pro", "Consolas", monospace;
}
QLabel#legendItem {
    color: #4A5058;
    font-size: 11px;
    font-weight: 400;
    font-family: "Source Code Pro", "Consolas", monospace;
}

/* ==================== 滚动条（全局） ==================== */
QScrollBar:vertical {
    background: #E8ECF0;
    border: none;
    width: 12px;
    margin: 0;
}
QScrollBar:horizontal {
    background: #E8ECF0;
    border: none;
    height: 12px;
    margin: 0;
}
QScrollBar::handle {
    background: #B0B8C0;
    border-radius: 0;
    min-width: 20px;
    min-height: 20px;
}
QScrollBar::handle:hover {
    background: #808890;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
    background: none;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: #E8ECF0;
}

/* ==================== 工具提示 ==================== */
QToolTip {
    background: #FFFFFF;
    color: #1A1E22;
    border: 1px solid #B0B8C0;
    border-radius: 0;
    padding: 4px 8px;
    font-size: 11px;
}
"""
