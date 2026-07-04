"""Dialog for on-demand simulation information display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QVBoxLayout,
)


class SimulationInfoDialog(QDialog):
    """Show the latest simulation summary without occupying the main window."""

    def __init__(self, info: dict[str, str] | None, parent=None) -> None:  # type: ignore[no-untyped-def]
        """Create the dialog from an optional simulation info dictionary."""
        super().__init__(parent)
        self.setWindowTitle("仿真信息")
        self.setMinimumSize(460, 360)
        self._build_ui(info)

    def _build_ui(self, info: dict[str, str] | None) -> None:
        """Build a compact form or empty state."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        card = QFrame(self)
        card.setObjectName("infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        title = QLabel("仿真信息", card)
        title.setObjectName("dialogTitle")
        card_layout.addWidget(title)

        if not info:
            empty_label = QLabel("暂无仿真数据", card)
            empty_label.setObjectName("emptyStateLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(empty_label, 1)
        else:
            form = QFormLayout()
            form.setHorizontalSpacing(18)
            form.setVerticalSpacing(10)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for key in (
                "当前坐标",
                "当前行",
                "路径长度",
                "解析状态",
                "当前模式",
                "图元数量",
                "图纸范围",
                "代码行数",
                "警告数量",
            ):
                name_label = QLabel(key, card)
                name_label.setObjectName("formLabel")
                value_label = QLabel(info.get(key, "-"), card)
                value_label.setObjectName("metricValue")
                value_label.setWordWrap(True)
                value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                form.addRow(name_label, value_label)
            card_layout.addLayout(form)

        root_layout.addWidget(card, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        root_layout.addWidget(buttons)
