"""Application entry point for the CNC CAM and G-code simulator."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.style import APP_STYLE


def _login_enabled() -> bool:
    """Return whether the startup password gate is enabled.

    默认启用，必须输入演示密码才能进入主界面；
    可通过环境变量 ``CNC_LOGIN_ENABLED=0`` 或命令行参数 ``--no-login`` 跳过。
    """
    if "--no-login" in sys.argv:
        return False
    return os.environ.get("CNC_LOGIN_ENABLED", "1").lower() not in {"0", "false", "no", "off"}


def main() -> int:
    """Start the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("CNC CAM G-Code Simulator")
    app.setOrganizationName("Course Design")
    app.setStyleSheet(APP_STYLE)

    if _login_enabled():
        login_dialog = LoginDialog()
        if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
            return 0

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
