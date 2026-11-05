"""The deep-green navigation sidebar."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import WEEKDAYS, ViewKind
from .common import BrandMark, NavButton, ProgressBar


class Sidebar(QFrame):
    viewRequested = Signal(object)

    NAV_ITEMS = (
        (ViewKind.TODAY, "sun", "今天"),
        (ViewKind.ALL, "inbox", "全部任务"),
        (ViewKind.UPCOMING, "calendar", "未来 7 天"),
        (ViewKind.COMPLETED, "check-circle", "已完成"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(238)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self.today = date.today()
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 22, 20, 20)
        root.setSpacing(0)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(11)
        brand_row.addWidget(BrandMark(39), 0, Qt.AlignmentFlag.AlignVCenter)
        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(0)
        name = QLabel("轻单")
        name.setFont(theme.make_font(21, weight=QFont.Weight.Bold))
        name.setStyleSheet(f"color: {theme.SIDEBAR_TEXT};")
        tagline = QLabel("QINGDAN · TODOS")
        tagline.setFont(theme.make_font(8, weight=QFont.Weight.DemiBold, letter_spacing=1.1))
        tagline.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        brand_text.addWidget(name)
        brand_text.addWidget(tagline)
        brand_row.addLayout(brand_text)
        brand_row.addStretch(1)
        root.addLayout(brand_row)

        root.addSpacing(33)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(1, 0, 0, 0)
        date_row.setSpacing(7)
        dot = QFrame()
        dot.setFixedSize(5, 5)
        dot.setStyleSheet(f"background: {theme.GOLD}; border-radius: 2px;")
        date_row.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.date_label = QLabel()
        self.date_label.setFont(theme.make_font(11, weight=QFont.Weight.Medium))
        self.date_label.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        date_row.addWidget(self.date_label)
        date_row.addStretch(1)
        root.addLayout(date_row)
        root.addSpacing(21)

        self.greeting_label = QLabel()
        self.greeting_label.setFont(theme.make_font(24, weight=QFont.Weight.Bold))
        self.greeting_label.setStyleSheet(f"color: {theme.SIDEBAR_TEXT};")
        root.addWidget(self.greeting_label)
        root.addSpacing(4)
        greeting_sub = QLabel("把今天，过得刚刚好。")
        greeting_sub.setFont(theme.make_font(12))
        greeting_sub.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        root.addWidget(greeting_sub)

        root.addSpacing(40)
        section = QLabel("我的清单")
        section.setFont(theme.make_font(10, weight=QFont.Weight.DemiBold, letter_spacing=0.6))
        section.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        root.addWidget(section)
        root.addSpacing(10)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.nav_buttons: dict[ViewKind, NavButton] = {}
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(5)
        for view, icon_name, label in self.NAV_ITEMS:
            button = NavButton(icon_name, label)
            button.clicked.connect(lambda checked=False, v=view: self.viewRequested.emit(v))
            self.group.addButton(button)
            self.nav_buttons[view] = button
            nav_layout.addWidget(button)
        root.addLayout(nav_layout)
        root.addStretch(1)

        self.progress_card = QFrame()
        self.progress_card.setObjectName("progressCard")
        card_layout = QVBoxLayout(self.progress_card)
        card_layout.setContentsMargins(15, 14, 15, 14)
        card_layout.setSpacing(0)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        progress_title = QLabel("今日完成度")
        progress_title.setFont(theme.make_font(11, weight=QFont.Weight.Medium))
        progress_title.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        top.addWidget(progress_title)
        top.addStretch(1)
        self.progress_value = QLabel("0%")
        self.progress_value.setFont(theme.make_font(12, weight=QFont.Weight.Bold))
        self.progress_value.setStyleSheet(f"color: {theme.GOLD};")
        top.addWidget(self.progress_value)
        card_layout.addLayout(top)
        card_layout.addSpacing(9)
        self.progress_bar = ProgressBar()
        self.progress_bar.set_value(0, animate=False)
        card_layout.addWidget(self.progress_bar)
        card_layout.addSpacing(9)
        self.progress_caption = QLabel("今天还没有安排")
        self.progress_caption.setFont(theme.make_font(11))
        self.progress_caption.setWordWrap(True)
        self.progress_caption.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        card_layout.addWidget(self.progress_caption)
        root.addWidget(self.progress_card)

        root.addSpacing(15)
        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        footer.setSpacing(6)

        shield = QLabel()
        shield.setFixedSize(14, 14)
        shield.setPixmap(icons.icon_pixmap("leaf", theme.SIDEBAR_MUTED, 12, stroke=1.5))
        footer.addWidget(shield)
        storage_hint = QLabel("本地保存 · 不上传云端")
        storage_hint.setFont(theme.make_font(9))
        storage_hint.setStyleSheet(f"color: {theme.SIDEBAR_MUTED};")
        footer.addWidget(storage_hint)
        footer.addStretch(1)
        root.addLayout(footer)

        self.set_today(self.today)

    def set_today(self, today: date) -> None:
        self.today = today
        self.date_label.setText(f"{today.month:02d} / {today.day:02d} · {WEEKDAYS[today.weekday()]}")
        from datetime import datetime

        hour = datetime.now().hour
        if 5 <= hour < 11:
            greeting = "早上好"
        elif 11 <= hour < 14:
            greeting = "中午好"
        elif 14 <= hour < 18:
            greeting = "下午好"
        else:
            greeting = "晚上好"
        self.greeting_label.setText(greeting)

    def set_counts(self, counts: dict[ViewKind, int]) -> None:
        for view, button in self.nav_buttons.items():
            button.set_count(counts.get(view, 0))

    def set_current(self, view: ViewKind | None) -> None:
        if view is None:
            self.group.setExclusive(False)
            for button in self.nav_buttons.values():
                button.setChecked(False)
            self.group.setExclusive(True)
            return
        button = self.nav_buttons.get(view)
        if button is not None:
            button.setChecked(True)

    def set_progress(self, done: int, total: int, percent: int) -> None:
        self.progress_value.setText(f"{percent}%")
        self.progress_bar.set_value(percent)
        if total == 0:
            caption = "今天还没有安排，慢慢来。"
        elif done >= total:
            caption = "今天全部完成，辛苦了。"
        else:
            caption = f"已完成 {done} 项，还剩 {total - done} 项。"
        self.progress_caption.setText(caption)
