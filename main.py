"""Application entry point for the CNC CAM and G-code simulator."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.style import APP_STYLE


def main() -> int:
    """Start the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("CNC CAM G-Code Simulator")
    app.setOrganizationName("Course Design")
    app.setStyleSheet(APP_STYLE)

    login_dialog = LoginDialog()
    if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
        return 0

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
