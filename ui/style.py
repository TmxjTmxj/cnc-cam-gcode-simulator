"""Shared visual theme for the CNC CAM desktop application."""

from __future__ import annotations


COLORS = {
    "primary": "#2563EB",
    "secondary": "#0F172A",
    "background": "#F1F5F9",
    "surface": "#FFFFFF",
    "border": "#CBD5E1",
    "text": "#0F172A",
    "muted": "#64748B",
    "success": "#16A34A",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}


APP_STYLE = """
QMainWindow {
    background: #D9E0E8;
    color: #0F172A;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}
QDialog {
    background: #F1F5F9;
    color: #0F172A;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}
QWidget#centralSurface {
    background: #D9E0E8;
}
QMenuBar {
    background: #172632;
    color: #F8FAFC;
    padding: 4px;
    font-size: 14px;
}
QMenuBar::item {
    padding: 7px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #1E293B;
}
QToolBar#mainToolbar {
    background: #172632;
    border: none;
    border-top: 1px solid #1E293B;
    border-bottom: 1px solid #020617;
    spacing: 8px;
    padding: 8px 12px;
}
QToolBar#mainToolbar::separator {
    background: #334155;
    width: 1px;
    margin: 6px 8px;
}
QToolButton#primaryToolButton,
QToolButton#secondaryToolButton {
    border-radius: 7px;
    padding: 7px 10px;
    font-weight: 700;
    min-width: 72px;
}
QToolButton#primaryToolButton {
    background: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
}
QToolButton#primaryToolButton:hover {
    background: #1D4ED8;
}
QToolButton#secondaryToolButton {
    background: #1E293B;
    border: 1px solid #475569;
    color: #E2E8F0;
}
QToolButton#secondaryToolButton:hover {
    background: #334155;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    padding: 6px;
}
QMenu::item {
    padding: 7px 28px 7px 18px;
}
QMenu::item:selected {
    background: #E2E8F0;
    color: #0F172A;
}
QFrame#workPanel, QGroupBox {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}
QFrame#workPanel {
    margin: 0;
}
QFrame#welcomeCard, QFrame#loginCard, QFrame#infoCard {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 14px;
}
QFrame#welcomeCard {
    border: 1px solid #BFDBFE;
}
QLabel#panelTitle {
    color: #0F172A;
    font-size: 14px;
    font-weight: 800;
    padding: 2px 0 6px 0;
}
QLabel#welcomeTitle, QLabel#loginTitle {
    color: #0F172A;
    font-size: 23px;
    font-weight: 900;
}
QLabel#dialogTitle {
    color: #0F172A;
    font-size: 18px;
    font-weight: 900;
}
QLabel#emptyStateLabel {
    color: #64748B;
    font-size: 15px;
    font-weight: 800;
}
QLabel#welcomeSubtitle, QLabel#loginSubtitle {
    color: #64748B;
    font-size: 14px;
    font-weight: 700;
}
QLabel#welcomeFeature {
    color: #1E293B;
    font-size: 13px;
    font-weight: 800;
    padding: 4px 0;
}
QLabel#welcomeHint {
    color: #2563EB;
    font-size: 14px;
    font-weight: 800;
}
QLabel#loginStatus {
    color: #EF4444;
    font-size: 12px;
    font-weight: 700;
}
QPlainTextEdit#gcodeEditor {
    background: #0B1220;
    color: #DBEAFE;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #2563EB;
    line-height: 135%;
}
QPlainTextEdit#gcodeEditor QScrollBar:vertical,
QPlainTextEdit#gcodeEditor QScrollBar:horizontal {
    background: #111827;
    border: none;
    width: 12px;
    height: 12px;
}
QPlainTextEdit#gcodeEditor QScrollBar::handle {
    background: #334155;
    border-radius: 6px;
}
QPlainTextEdit#gcodeEditor QScrollBar::handle:hover {
    background: #475569;
}
QPlainTextEdit#gcodeEditor QScrollBar::add-line,
QPlainTextEdit#gcodeEditor QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QWidget#controlPanel {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}
QScrollArea#parameterScrollArea {
    background: transparent;
    border: none;
}
QScrollArea#parameterScrollArea > QWidget > QWidget {
    background: transparent;
}
QGroupBox {
    margin-top: 6px;
    padding: 6px;
    font-weight: 800;
    color: #0F172A;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0F172A;
    background: #FFFFFF;
}
QLabel#formLabel {
    color: #64748B;
    font-size: 11px;
    font-weight: 700;
}
QLabel#metricTitle {
    color: #64748B;
    font-size: 12px;
    font-weight: 800;
}
QLabel#metricValue {
    color: #0F172A;
    font-weight: 900;
    font-size: 12px;
}
QFrame#metricCard {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 9px;
}
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {
    min-height: 24px;
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 2px 8px;
    background: #FFFFFF;
    color: #0F172A;
}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QLineEdit:focus {
    border: 1px solid #2563EB;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QCheckBox {
    color: #334155;
    font-weight: 800;
}
QPushButton {
    min-height: 32px;
    padding: 5px 14px;
    border-radius: 7px;
    font-weight: 800;
}
QPushButton#primaryButton {
    border: 1px solid #2563EB;
    background: #2563EB;
    color: #FFFFFF;
}
QPushButton#primaryButton:hover {
    background: #1D4ED8;
}
QPushButton#secondaryButton {
    border: 1px solid #CBD5E1;
    background: #F8FAFC;
    color: #0F172A;
}
QPushButton#secondaryButton:hover {
    background: #E2E8F0;
}
QPushButton#easterButton {
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
    color: #64748B;
    font-weight: 700;
}
QPushButton#easterButton:hover {
    background: #F8FAFC;
    color: #334155;
}
QStatusBar {
    background: #172632;
    color: #F8FAFC;
}
QSplitter::handle {
    background: #111B23;
    width: 4px;
    height: 4px;
}
QLabel#inspectorTitle {
    color: #172033;
    font-size: 18px;
    font-weight: 900;
    padding: 4px 2px 8px 2px;
    border-bottom: 1px solid #CBD5E1;
}
QWidget#inspectorMetricCard {
    background: #F4F7FA;
    border: 1px solid #D7DFE8;
    border-radius: 4px;
}
QWidget#projectNavigator {
    background: #EEF3F7;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}
QFrame#leftPanelGroup {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}
QLabel#leftGroupTitle {
    background: #1D2D39;
    color: #F8FAFC;
    font-size: 13px;
    font-weight: 900;
    padding: 7px 10px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTreeWidget#projectTree {
    background: #F8FAFC;
    border: none;
    color: #243443;
    outline: none;
}
QTreeWidget#projectTree::item {
    min-height: 24px;
}
QTreeWidget#projectTree::item:selected {
    background: #DBEAFE;
    color: #0F4EB8;
}
QTableWidget#workstationTable,
QTableWidget#warningTable {
    background: #F8FAFC;
    alternate-background-color: #EEF3F7;
    border: none;
    gridline-color: #CBD5E1;
    color: #243443;
    selection-background-color: #DBEAFE;
    selection-color: #0F172A;
}
QHeaderView::section {
    background: #E8EDF2;
    color: #445565;
    border: none;
    border-right: 1px solid #CBD5E1;
    border-bottom: 1px solid #CBD5E1;
    padding: 5px;
    font-weight: 800;
}
QFrame#metricBlue,
QFrame#metricGreen,
QFrame#metricAmber,
QFrame#metricSlate {
    border: 1px solid #D7DFE8;
    border-radius: 7px;
}
QFrame#metricBlue {
    background: #EAF2FF;
    color: #1056BD;
}
QFrame#metricGreen {
    background: #EAF8ED;
    color: #08783A;
}
QFrame#metricAmber {
    background: #FFF3DD;
    color: #C46600;
}
QFrame#metricSlate {
    background: #EDF4FB;
    color: #1F5C9D;
}
QLabel#metricCardTitle {
    color: #516477;
    font-size: 12px;
    font-weight: 800;
}
QLabel#metricCardValue {
    font-size: 20px;
    font-weight: 900;
}
QWidget#simulationTimeline {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
}
QFrame#timelineHeader {
    background: #F8FAFC;
    border-bottom: 1px solid #D7DFE8;
}
QLabel#timelineTitle {
    color: #172033;
    font-size: 14px;
    font-weight: 900;
}
QPushButton#timelineButton {
    min-height: 26px;
    min-width: 30px;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    background: #EEF3F7;
    color: #1E293B;
    padding: 2px 8px;
}
QPushButton#timelineButton:hover {
    background: #DBEAFE;
    border-color: #93C5FD;
}
QFrame#timelineProgressFrame,
QFrame#timelineMetrics {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QProgressBar {
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    background: #E2E8F0;
    color: #172033;
    text-align: center;
    font-weight: 800;
}
QProgressBar::chunk {
    background: #1769E8;
    border-radius: 4px;
}
QFrame#timelineMetricCell {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
}
QLabel#timelineMetricTitle {
    color: #64748B;
    font-size: 11px;
    font-weight: 800;
}
QLabel#timelineMetricValue {
    color: #172033;
    font-size: 13px;
    font-weight: 900;
}
QTabWidget#canvasTabs::pane {
    border: none;
    background: transparent;
}
QTabWidget#canvasTabs QTabBar::tab {
    background: #E2E8F0;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 16px;
    font-weight: 800;
    font-size: 13px;
    margin-right: 3px;
}
QTabWidget#canvasTabs QTabBar::tab:selected {
    background: #FFFFFF;
    color: #0F172A;
    border-bottom: 2px solid #2563EB;
}
QTabWidget#canvasTabs QTabBar::tab:hover {
    background: #F1F5F9;
}
"""
