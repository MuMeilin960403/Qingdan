"""Compact always-on-top window for quick task checking."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QEvent, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import sort_tasks, today_progress, weekday_text
from ..models import Task
from ..recurrence import repeat_label
from .common import (
    BrandMark,
    CheckCircle,
    ElidedLabel,
    IconButton,
    attach_shadow,
    clear_layout,
    repolish,
)


class MiniTaskRow(QFrame):
    completionChanged = Signal(str, bool)

    def __init__(self, task: Task, today: date, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task = task
        self.today = today
        self.setObjectName("miniTaskRow")
        self.setProperty("hovered", False)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 0, 8, 0)
        layout.setSpacing(9)

        self.check = CheckCircle()
        self.check.setToolTip("完成任务")
        self.check.setAccessibleName(f"完成任务：{task.title}")
        self.check.clicked.connect(
            lambda: self.completionChanged.emit(task.id, self.check.isChecked())
        )
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignVCenter)

        title = ElidedLabel(task.title)
        title.setFont(theme.make_font(12, weight=QFont.Weight.Medium))
        title.setStyleSheet(f"color: {theme.INK_SOFT};")
        self.setToolTip(task.title)
        layout.addWidget(title, 1)

        if task.repeat is not None:
            repeat_icon = QLabel()
            repeat_icon.setPixmap(icons.icon_pixmap("repeat", theme.ACCENT, 13))
            repeat_icon.setFixedSize(14, 14)
            repeat_icon.setToolTip(f"重复：{repeat_label(task.repeat)}")
            layout.addWidget(repeat_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        if task.due is not None:
            delta = (task.due - today).days
            if delta < 0:
                label, fg, bg = f"逾期{-delta}天", theme.CORAL, theme.CORAL_SOFT
            elif delta == 0:
                label, fg, bg = "今天", theme.AMBER, theme.AMBER_SOFT
            elif delta == 1:
                label, fg, bg = "明天", theme.ACCENT_DARK, theme.ACCENT_SOFT
            else:
                label = f"{task.due.month}/{task.due.day}"
                fg, bg = theme.MUTED, "#F3F1EB"
            badge = QLabel(label)
            badge.setFont(theme.make_font(9))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedHeight(20)
            badge.setMinimumWidth(34)
            badge.setStyleSheet(
                f"color: {fg}; background: {bg}; border-radius: 6px; padding: 0 6px;"
            )
            layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        self._hovered = False

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hovered = True
        self.setProperty("hovered", True)
        repolish(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hovered = False
        self.setProperty("hovered", False)
        repolish(self)
        super().leaveEvent(event)


class MiniHeaderBand(QFrame):
    expandRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("miniHeaderBand")
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("拖动移动小窗 · 双击展开完整清单")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.expandRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class MiniWindow(QWidget):
    completionChanged = Signal(str, bool)
    taskAdded = Signal(str, object)
    restoreRequested = Signal()
    quitRequested = Signal()

    WIDTH = 380
    HEIGHT = 520
    OUTER_MARGIN = 14

    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.today = date.today()
        self._tasks: list[Task] = []
        self._mode = "today"
        self._pinned = bool(settings.value("mini/pinned", True, type=bool))
        self._drag_pos = None

        self.setWindowTitle("轻单 · 迷你清单")
        self.setWindowIcon(icons.app_icon())
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._apply_window_flags()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            self.OUTER_MARGIN,
            self.OUTER_MARGIN,
            self.OUTER_MARGIN,
            self.OUTER_MARGIN,
        )
        root.setSpacing(0)
        self.surface = QFrame()
        self.surface.setObjectName("miniSurface")
        root.addWidget(self.surface)
        attach_shadow(self.surface, blur=34, dy=10, alpha=58)

        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        self.header = MiniHeaderBand()
        self.header.expandRequested.connect(self.restoreRequested)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 0, 13, 0)
        header_layout.setSpacing(9)
        header_layout.addWidget(BrandMark(26), 0, Qt.AlignmentFlag.AlignVCenter)
        brand = QVBoxLayout()
        brand.setContentsMargins(0, 0, 0, 0)
        brand.setSpacing(0)
        brand_name = QLabel("轻单")
        brand_name.setFont(theme.make_font(14, weight=QFont.Weight.Bold))
        brand_name.setStyleSheet(f"color: {theme.SIDEBAR_TEXT};")
        brand_name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand_sub = QLabel("MINI LIST")
        brand_sub.setFont(
            theme.make_font(7.5, weight=QFont.Weight.DemiBold, letter_spacing=1.0)
        )
        brand_sub.setStyleSheet(f"color: {theme.GOLD};")
        brand_sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        brand.addWidget(brand_name)
        brand.addWidget(brand_sub)
        header_layout.addLayout(brand)
        header_layout.addStretch(1)

        self.pin_button = IconButton(
            "pin",
            button_size=28,
            icon_size=15,
            color=theme.GOLD if self._pinned else theme.SIDEBAR_MUTED,
            hover_color=theme.SIDEBAR_TEXT,
            hover_bg=theme.SIDEBAR_LINE,
            tooltip="取消置顶" if self._pinned else "置顶小窗",
        )
        self.pin_button.clicked.connect(self._toggle_pin)
        header_layout.addWidget(self.pin_button)
        self.expand_button = IconButton(
            "expand",
            button_size=28,
            icon_size=15,
            color=theme.SIDEBAR_MUTED,
            hover_color=theme.SIDEBAR_TEXT,
            hover_bg=theme.SIDEBAR_LINE,
            tooltip="展开完整清单 (Ctrl+M)",
        )
        self.expand_button.clicked.connect(self.restoreRequested)
        header_layout.addWidget(self.expand_button)
        self.close_button = IconButton(
            "close",
            button_size=28,
            icon_size=13,
            color=theme.SIDEBAR_MUTED,
            hover_color="#F0B5A6",
            hover_bg="#2A5048",
            tooltip="退出轻单",
        )
        self.close_button.clicked.connect(self.quitRequested)
        header_layout.addWidget(self.close_button)
        surface_layout.addWidget(self.header)

        content = QWidget()
        surface_layout.addWidget(content, 1)
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(16, 13, 16, 14)
        self.content_layout.setSpacing(0)

        self.date_label = QLabel()
        self.date_label.setFont(theme.make_font(10, weight=QFont.Weight.Medium))
        self.date_label.setStyleSheet(f"color: {theme.MUTED};")
        self.content_layout.addWidget(self.date_label)
        self.content_layout.addSpacing(3)

        headline = QHBoxLayout()
        headline.setContentsMargins(0, 0, 0, 0)
        headline.setSpacing(8)
        self.title_label = QLabel("今天")
        self.title_label.setFont(
            theme.make_font(20, weight=QFont.Weight.Bold, letter_spacing=-0.2)
        )
        self.title_label.setStyleSheet(f"color: {theme.INK};")
        headline.addWidget(self.title_label, 1)
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(theme.make_font(11, weight=QFont.Weight.DemiBold))
        self.percent_label.setStyleSheet(f"color: {theme.ACCENT};")
        headline.addWidget(self.percent_label, 0, Qt.AlignmentFlag.AlignBottom)
        self.content_layout.addLayout(headline)
        self.content_layout.addSpacing(8)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setStyleSheet(
            f"""
            QProgressBar {{
                background: #E8E2D6;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {theme.GOLD};
                border-radius: 2px;
            }}
            """
        )
        self.content_layout.addWidget(self.progress)
        self.content_layout.addSpacing(13)

        tabs = QHBoxLayout()
        tabs.setContentsMargins(0, 0, 0, 0)
        tabs.setSpacing(5)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.today_tab = self._make_tab("今天")
        self.all_tab = self._make_tab("全部")
        self.tab_group.addButton(self.today_tab)
        self.tab_group.addButton(self.all_tab)
        self.today_tab.setChecked(True)
        self.today_tab.clicked.connect(lambda: self._set_mode("today"))
        self.all_tab.clicked.connect(lambda: self._set_mode("all"))
        tabs.addWidget(self.today_tab)
        tabs.addWidget(self.all_tab)
        tabs.addStretch(1)
        self.mode_count = QLabel("")
        self.mode_count.setFont(theme.make_font(9.5))
        self.mode_count.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        tabs.addWidget(self.mode_count)
        self.content_layout.addLayout(tabs)
        self.content_layout.addSpacing(9)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.content_layout.addWidget(self.scroll, 1)
        self.content_layout.addSpacing(9)

        self.add_frame = QFrame()
        self.add_frame.setObjectName("miniComposerFrame")
        self.add_frame.setProperty("focused", False)
        self.add_frame.setFixedHeight(39)
        add_layout = QHBoxLayout(self.add_frame)
        add_layout.setContentsMargins(9, 0, 5, 0)
        add_layout.setSpacing(6)
        plus = QLabel()
        plus.setPixmap(icons.icon_pixmap("plus", theme.ACCENT, 14))
        plus.setFixedSize(15, 15)
        add_layout.addWidget(plus, 0, Qt.AlignmentFlag.AlignVCenter)
        self.input = QLineEdit()
        self.input.setObjectName("miniInput")
        self.input.setPlaceholderText("添加到今天…")
        self.input.setFont(theme.make_font(11.5))
        palette = self.input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.MUTED_LIGHT))
        self.input.setPalette(palette)
        self.input.textChanged.connect(self._update_add_button)
        self.input.returnPressed.connect(self._submit)
        self.input.installEventFilter(self)
        add_layout.addWidget(self.input, 1)
        self.add_button = IconButton(
            "arrow-up",
            button_size=27,
            icon_size=13,
            color=theme.MUTED_LIGHT,
            hover_color=theme.SURFACE,
            hover_bg=theme.ACCENT,
            tooltip="添加任务",
        )
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self._submit)
        add_layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.content_layout.addWidget(self.add_frame)

        self.error_label = QLabel("")
        self.error_label.setFont(theme.make_font(9))
        self.error_label.setStyleSheet(f"color: {theme.CORAL};")
        self.error_label.hide()
        self.content_layout.addWidget(self.error_label)
        self.content_layout.addSpacing(7)

        footer = QHBoxLayout()
        footer.setContentsMargins(1, 0, 1, 0)
        footer.setSpacing(6)
        hint = QLabel("勾掉一件，少一件。")
        hint.setFont(theme.make_font(9))
        hint.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        footer.addWidget(hint)
        footer.addStretch(1)
        self.expand_link = QPushButton("完整清单 ›")
        self.expand_link.setObjectName("flatButton")
        self.expand_link.setFont(theme.make_font(9.5))
        self.expand_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_link.setFixedHeight(22)
        self.expand_link.clicked.connect(self.restoreRequested)
        footer.addWidget(self.expand_link)
        self.content_layout.addLayout(footer)

        shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        shortcut.activated.connect(self.restoreRequested)

        self.today_tab.setText("今天")
        self._refresh_labels()

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _make_tab(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("miniTab")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFont(theme.make_font(11))
        button.setFixedHeight(27)
        return button

    def restore_position(self) -> None:
        values = []
        for key in ("mini/x", "mini/y"):
            try:
                values.append(int(self._settings.value(key)))
            except (TypeError, ValueError):
                values = []
                break
        if len(values) == 2:
            from PySide6.QtCore import QRect

            candidate = QRect(values[0], values[1], self.width(), self.height())
            visible = any(
                not screen.availableGeometry().intersected(candidate).isEmpty()
                for screen in QApplication.screens()
            )
            if visible:
                self.move(values[0], values[1])
                return
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.move(
                available.right() - self.width() - 24,
                available.top() + 24,
            )

    def save_position(self) -> None:
        self._settings.setValue("mini/x", self.x())
        self._settings.setValue("mini/y", self.y())
        self._settings.setValue("mini/pinned", self._pinned)
        self._settings.sync()

    def _toggle_pin(self) -> None:
        was_visible = self.isVisible()
        self._pinned = not self._pinned
        geometry = self.geometry()
        self._apply_window_flags()
        self.setGeometry(geometry)
        self._settings.setValue("mini/pinned", self._pinned)
        self._settings.sync()
        self.pin_button.set_icon("pin" if self._pinned else "pin-off")
        self.pin_button.set_color(
            theme.GOLD if self._pinned else theme.SIDEBAR_MUTED
        )
        self.pin_button.setToolTip("取消置顶" if self._pinned else "置顶小窗")
        if was_visible:
            self.show()
            self.raise_()

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "today":
            self.today_tab.setChecked(True)
        else:
            self.all_tab.setChecked(True)
        self.input.setPlaceholderText(
            "添加到今天…" if mode == "today" else "添加一项任务…"
        )
        self._render()

    def _refresh_labels(self) -> None:
        self.date_label.setText(f"{self.today.month}月{self.today.day}日 · {weekday_text(self.today)}")
        pending_today = [
            task
            for task in self._tasks
            if not task.completed
            and task.due is not None
            and task.due <= self.today
        ]
        pending_all = [task for task in self._tasks if not task.completed]
        done, total, percent = today_progress(self._tasks, self.today)
        self.today_tab.setText(f"今天 {len(pending_today)}")
        self.all_tab.setText(f"全部 {len(pending_all)}")
        self.mode_count.setText(f"今日已完成 {done}/{total}" if total else "今日暂无安排")
        self.percent_label.setText(f"{percent}%")
        self.progress.setValue(percent)
        if self._mode == "today":
            if pending_today:
                self.title_label.setText(f"今天还有 {len(pending_today)} 件事")
            else:
                self.title_label.setText("今天已经清空")
        else:
            if pending_all:
                self.title_label.setText(f"还有 {len(pending_all)} 件待办")
            else:
                self.title_label.setText("清单已经空了")

    def _render(self) -> None:
        clear_layout(self.list_layout)
        if self._mode == "today":
            items = [
                task
                for task in self._tasks
                if not task.completed
                and task.due is not None
                and task.due <= self.today
            ]
        else:
            items = [task for task in self._tasks if not task.completed]
        items = sort_tasks(items)

        if not items:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(0, 12, 0, 12)
            empty_layout.setSpacing(5)
            empty_layout.addStretch(1)
            icon = QLabel()
            icon.setPixmap(icons.icon_pixmap("check-circle", theme.ACCENT, 28))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(icon)
            headline = QLabel("今天没有待办" if self._mode == "today" else "清单已经空了")
            headline.setFont(theme.make_font(13, weight=QFont.Weight.DemiBold))
            headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
            headline.setStyleSheet(f"color: {theme.INK_SOFT};")
            empty_layout.addWidget(headline)
            body = QLabel("给自己留一点空白。" if self._mode == "today" else "写下一件想做的事吧。")
            body.setFont(theme.make_font(10))
            body.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body.setStyleSheet(f"color: {theme.MUTED};")
            empty_layout.addWidget(body)
            empty_layout.addStretch(1)
            self.list_layout.addWidget(empty)
        else:
            for task in items:
                row = MiniTaskRow(task, self.today)
                row.completionChanged.connect(self.completionChanged)
                self.list_layout.addWidget(row)
            self.list_layout.addStretch(1)

    def set_data(self, tasks: list[Task], today: date) -> None:
        self.today = today
        self._tasks = list(tasks)
        self._refresh_labels()
        self._render()

    def _update_add_button(self, text: str) -> None:
        self.add_button.setEnabled(bool(text.strip()))

    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        due = self.today if self._mode == "today" else None
        self.error_label.hide()
        self.taskAdded.emit(text, due)

    def confirm_added(self) -> None:
        self.input.clear()
        self.error_label.hide()
        self.input.setFocus(Qt.FocusReason.OtherFocusReason)

    def show_add_error(self, message: str = "保存失败，请重试") -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.input:
            if event.type() == QEvent.Type.FocusIn:
                self.add_frame.setProperty("focused", True)
                repolish(self.add_frame)
            elif event.type() == QEvent.Type.FocusOut:
                self.add_frame.setProperty("focused", False)
                repolish(self.add_frame)
        return super().eventFilter(watched, event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.save_position()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self.save_position()
        super().hideEvent(event)
