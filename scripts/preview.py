"""Render a demo window to docs/preview.png for visual QA.

Run from the project root:
    ..\\.venv\\Scripts\\python.exe scripts\\preview.py

The demo data is written to a temporary directory so it can never touch the
real task file.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEMO_DIR = Path(tempfile.mkdtemp(prefix="qingdan-preview-"))
os.environ["QINGDAN_DATA_DIR"] = str(DEMO_DIR)


def seed(store) -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)

    store.add("提交第三季度预算表", yesterday)
    store.add("回复客户关于报价的邮件", today)
    store.add("给妈妈打个电话", today)
    store.add("每天喝够八杯水", today, "daily")
    store.add("预约下周的牙科复诊", today + timedelta(days=2))
    store.add("规划周末的徒步路线", today + timedelta(days=3))
    store.add("读完《保持松弛》的第三章", None)

    first = store.add("晨间拉伸 10 分钟", None)
    store.set_completed(first.id, True)
    second = store.add("购买手冲咖啡豆", today)
    store.set_completed(second.id, True)


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter

    from qingdan.app import create_application
    from qingdan.store import TaskStore
    from qingdan.ui.main_window import MainWindow

    app = create_application([])
    store = TaskStore(DEMO_DIR / "tasks.json")
    if not store.tasks:
        seed(store)

    window = MainWindow(store, persist_geometry=False)
    window.resize(1220, 820)
    window.show()
    app.processEvents()

    out_dir = ROOT / "docs"
    out_dir.mkdir(exist_ok=True)

    def capture() -> None:
        app.processEvents()
        pixmap = window.grab()

        # Grab returns a high-DPI pixmap (e.g. 1830×1230 for a 1220×820
        # window). Normalize the ratio so QPainter draws the full pixel data
        # rather than a logical-size 1220×820 image on a larger canvas.
        pixmap.setDevicePixelRatio(1.0)

        # Put the transparent window on a warm, subtle studio backdrop so the
        # PNG reads well when opened directly in an image viewer.
        pad = 120
        canvas = QImage(
            pixmap.width() + pad * 2,
            pixmap.height() + pad * 2,
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        painter = QPainter(canvas)
        gradient = QLinearGradient(0, 0, canvas.width(), canvas.height())
        gradient.setColorAt(0, QColor("#F1ECE3"))
        gradient.setColorAt(0.55, QColor("#EAE4D9"))
        gradient.setColorAt(1, QColor("#E4DDD1"))
        painter.fillRect(canvas.rect(), gradient)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.drawPixmap(pad, pad, pixmap)
        painter.end()
        canvas.save(str(out_dir / "preview.png"))
        print(f"saved {out_dir / 'preview.png'}  ({pixmap.width()}x{pixmap.height()} window)")
        app.quit()

    QTimer.singleShot(700, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
