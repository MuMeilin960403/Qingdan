"""Qingdan application entrypoint."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from . import icons, theme
from .paths import (
    APP_NAME,
    APP_NAME_EN,
    APP_VERSION,
    DataDirectoryError,
    ORG_NAME,
    app_data_dir,
    tasks_path,
)
from .store import StoreError, TaskStore
from .ui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setApplicationName(APP_NAME_EN)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    QApplication.setAttribute(
        Qt.ApplicationAttribute.AA_DontShowIconsInMenus,
        False,
    )
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationDisplayName(APP_NAME)
    app.setWindowIcon(icons.app_icon())
    app.setQuitOnLastWindowClosed(True)
    theme.configure_application(app)
    return app


def main(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    try:
        app_data_dir()  # resolves and verifies writability once
        store = TaskStore(tasks_path())
    except (OSError, StoreError, DataDirectoryError) as exc:
        QMessageBox.critical(
            None,
            "无法启动轻单",
            f"任务数据目录无法使用。\n\n{exc}",
        )
        return 1

    window = MainWindow(store)
    window.show()
    return app.exec()
