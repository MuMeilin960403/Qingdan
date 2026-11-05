"""Render final screenshots for the mini window and deadline reminder."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["QINGDAN_DATA_DIR"] = tempfile.mkdtemp(prefix="qingdan-mini-preview-")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from qingdan.app import create_application  # noqa: E402
from qingdan.reminders import build_reminder_event  # noqa: E402
from qingdan.store import TaskStore  # noqa: E402
from qingdan.ui.main_window import MainWindow  # noqa: E402


def compose(pixmap, path: Path, pad: int = 52) -> None:
    pixmap.setDevicePixelRatio(1.0)
    canvas = QImage(
        pixmap.width() + pad * 2,
        pixmap.height() + pad * 2,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    painter = QPainter(canvas)
    gradient = QLinearGradient(0, 0, canvas.width(), canvas.height())
    gradient.setColorAt(0, QColor("#F2EEE6"))
    gradient.setColorAt(0.55, QColor("#EAE4D9"))
    gradient.setColorAt(1, QColor("#E3DCD0"))
    painter.fillRect(canvas.rect(), gradient)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.drawPixmap(pad, pad, pixmap)
    painter.end()
    canvas.save(str(path))
    print("saved", path)


def seed(store: TaskStore) -> None:
    today = date.today()
    store.add("提交第三季度预算表", today - timedelta(days=1))
    store.add("回复客户关于报价的邮件", today)
    store.add("给妈妈打个电话", today)
    store.add("每天喝够八杯水", today, "daily")
    store.add("准备明天下午的评审材料", today + timedelta(days=1))
    store.add("预约下周的牙科复诊", today + timedelta(days=2))
    store.add("规划周末的徒步路线", today + timedelta(days=3))
    for title in ("晨间拉伸 10 分钟", "购买手冲咖啡豆"):
        task = store.add(title, None)
        store.set_completed(task.id, True)


def main() -> int:
    app = create_application([])
    out_dir = ROOT / "docs"
    out_dir.mkdir(exist_ok=True)
    store = TaskStore(Path(tempfile.mkdtemp()) / "tasks.json")
    seed(store)

    window = MainWindow(store, persist_geometry=False, enable_reminders=False)
    window.resize(1220, 820)
    window.show()
    window.show_mini()
    QApplication.processEvents()
    mini = window._mini
    assert mini is not None
    compose(mini.grab(), out_dir / "preview-mini.png")

    event = build_reminder_event(
        store.tasks,
        date.today(),
        include_morning=True,
        include_evening=True,
    )
    assert event is not None
    window._show_reminder(event)
    QApplication.processEvents()
    popup = window._reminder_popup
    assert popup is not None
    compose(popup.grab(), out_dir / "preview-reminder.png")

    popup.close()
    mini.close()
    window.close()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
