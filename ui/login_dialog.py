"""Startup password dialog for demonstration access control."""

from __future__ import annotations

import hashlib

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


DEMO_PASSWORD_SHA256 = "5231631892cf4e3d8d643cb0542f800dc07914134d03564a3dbe112398bbcab7"
MAX_LOGIN_ATTEMPTS = 3


class LoginDialog(QDialog):
    """Simple password gate shown before the main window opens."""

    def __init__(self) -> None:
        """Create a password prompt with a three-attempt limit."""
        super().__init__()
        self._attempt_count = 0
        self.setWindowTitle("软件启动验证")
        self.setModal(True)
        self.setFixedSize(420, 260)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog using regular Qt widgets."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)

        card = QFrame(self)
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(12)

        title = QLabel("CNC CAM 启动验证", card)
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("请输入演示密码后进入主界面", card)
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        self.password_input = QLineEdit(card)
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._try_login)
        card_layout.addWidget(self.password_input)

        self.status_label = QLabel("", card)
        self.status_label.setObjectName("loginStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        cancel_button = QPushButton("退出", card)
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(cancel_button)

        login_button = QPushButton("进入软件", card)
        login_button.setObjectName("primaryButton")
        login_button.clicked.connect(self._try_login)
        button_row.addWidget(login_button)

        card_layout.addLayout(button_row)
        root_layout.addWidget(card)

    def _password_matches(self, password: str) -> bool:
        """Return whether the entered demo password matches the stored hash."""
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return digest == DEMO_PASSWORD_SHA256

    def _try_login(self) -> None:
        """Accept the dialog only when the configured demo password is entered."""
        if self._password_matches(self.password_input.text()):
            self.accept()
            return

        self._attempt_count += 1
        remaining = MAX_LOGIN_ATTEMPTS - self._attempt_count
        self.password_input.clear()

        if remaining <= 0:
            self.status_label.setText("密码错误次数过多，程序即将退出")
            self.reject()
            return

        self.status_label.setText(f"密码错误，还可尝试 {remaining} 次")
