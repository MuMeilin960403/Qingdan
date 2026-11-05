"""Main window and application chrome."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QRect,
    QSettings,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import (
    ViewKind,
    counts,
    date_range_text,
    due_marks,
    full_date_text,
    today_progress,
    visible_tasks,
    weekday_text,
)
from ..models import Task
from ..paths import APP_NAME, APP_NAME_EN, app_data_dir
from ..reminders import ReminderEvent, ReminderService, build_reminder_event, reminder_schedule_text
from ..store import StoreError, TaskStore
from .calendar import MonthCalendar
from .common import ElidedLabel, IconButton, WindowButton, clear_layout, repolish
from .mini_window import MiniWindow
from .reminder_popup import ReminderPopup
from .sidebar import Sidebar
from .task_panel import TaskPanel


class TopBar(QWidget):
    minimizeRequested = Signal()
    maximizeRequested = Signal()
    closeRequested = Signal()
    miniRequested = Signal()
    remindersRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("拖动移动窗口 · 双击最大化/还原")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(27, 8, 17, 4)
        layout.setSpacing(7)

        self.status_dot = QFrame()
        self.status_dot.setFixedSize(6, 6)
        self.status_dot.setStyleSheet("background: #6E9E8A; border-radius: 3px;")
        self.status_dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.status_label = QLabel("所有更改已自动保存")
        self.status_label.setFont(theme.make_font(10.5))
        self.status_label.setStyleSheet(f"color: {theme.MUTED};")
        self.status_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        self.reminder_button = IconButton(
            "bell",
            button_size=30,
            icon_size=16,
            color=theme.AMBER,
            hover_color=theme.AMBER,
            hover_bg=theme.AMBER_SOFT,
            tooltip="截止提醒：已开启",
        )
        self.reminder_button.setObjectName("reminderButton")
        self.reminder_button.clicked.connect(self.remindersRequested)
        self.mini_button = IconButton(
            "panel",
            button_size=30,
            icon_size=16,
            color=theme.INK_SOFT,
            hover_color=theme.ACCENT_DARK,
            hover_bg=theme.ACCENT_SOFT,
            tooltip="打开迷你窗口 (Ctrl+M)",
        )
        self.mini_button.setObjectName("miniButton")
        self.mini_button.clicked.connect(self.miniRequested)
        layout.addWidget(self.reminder_button)
        layout.addWidget(self.mini_button)
        layout.addSpacing(4)

        self.minimize_button = WindowButton("minimize")
        self.maximize_button = WindowButton("maximize")
        self.close_button = WindowButton("close")
        self.minimize_button.setObjectName("minimizeButton")
        self.maximize_button.setObjectName("maximizeButton")
        self.close_button.setObjectName("closeButton")
        self.minimize_button.clicked.connect(self.minimizeRequested)
        self.maximize_button.clicked.connect(self.maximizeRequested)
        self.close_button.clicked.connect(self.closeRequested)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def set_status(self, text: str, *, tone: str = "ok", tooltip: str = "") -> None:
        colors = {
            "ok": "#6E9E8A",
            "warn": theme.AMBER,
            "error": theme.CORAL,
        }
        self.status_dot.setStyleSheet(
            f"background: {colors.get(tone, colors['ok'])}; border-radius: 3px;"
        )
        self.status_label.setText(text)
        self.status_label.setToolTip(tooltip)

    def set_maximized(self, maximized: bool) -> None:
        self.maximize_button.set_kind("restore" if maximized else "maximize")

    def set_reminders_enabled(self, enabled: bool) -> None:
        self.reminder_button.set_color(
            theme.AMBER if enabled else theme.MUTED_LIGHT,
            hover_color=theme.AMBER if enabled else theme.INK_SOFT,
        )
        self.reminder_button.setToolTip(
            (
                "截止提醒：已开启\n09:00 提醒今天/逾期任务，20:00 提醒明天到期任务"
                if enabled
                else "截止提醒：已关闭\n点击可开启"
            )
        )
        self.reminder_button.setAccessibleName(self.reminder_button.toolTip())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximizeRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class ResizeHandle(QWidget):
    def __init__(self, parent: QWidget, edges: Qt.Edge, cursor: Qt.CursorShape) -> None:
        super().__init__(parent)
        self.edges = edges
        self.setCursor(cursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and handle.startSystemResize(self.edges):
                event.accept()
                return
        super().mousePressEvent(event)


class MainWindow(QWidget):
    def __init__(
        self,
        store: TaskStore,
        *,
        persist_geometry: bool = True,
        enable_reminders: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.persist_geometry = persist_geometry
        self.enable_reminders = enable_reminders
        self.today = date.today()
        self.current_view = ViewKind.TODAY
        self.selected_date: date | None = None
        self._settings = QSettings(
            str(app_data_dir() / "settings.ini"),
            QSettings.Format.IniFormat,
        )
        self._outer_margin = 20
        self._resize_margin = 5
        self._save_error = False
        self._mini: MiniWindow | None = None
        self._reminder_popup: ReminderPopup | None = None
        self._reminder_service: ReminderService | None = None

        self.setWindowTitle(f"{APP_NAME} · {APP_NAME_EN}")
        self.setWindowIcon(icons.app_icon())
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(1120, 680)
        self.setObjectName("mainWindow")

        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(
            self._outer_margin, self._outer_margin, self._outer_margin, self._outer_margin
        )
        self._outer_layout.setSpacing(0)
        self.surface = QFrame()
        self.surface.setObjectName("windowSurface")
        self._outer_layout.addWidget(self.surface)
        self._add_shadow()

        surface_layout = QHBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.viewRequested.connect(self._set_view)
        surface_layout.addWidget(self.sidebar)

        self.body = QFrame()
        self.body.setObjectName("body")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        surface_layout.addWidget(self.body, 1)

        self.topbar = TopBar()
        self.topbar.minimizeRequested.connect(self.showMinimized)
        self.topbar.maximizeRequested.connect(self.toggle_maximize)
        self.topbar.closeRequested.connect(self.close)
        self.topbar.miniRequested.connect(self.show_mini)
        self.topbar.remindersRequested.connect(self._open_reminders_menu)
        body_layout.addWidget(self.topbar)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(26, 6, 22, 20)
        content_layout.setSpacing(24)
        body_layout.addWidget(content, 1)

        self.task_panel = TaskPanel(self.today)
        self.task_panel.taskAdded.connect(self._add_task)
        self.task_panel.completionChanged.connect(self._toggle_task)
        self.task_panel.taskDeleted.connect(self._delete_task)
        self.task_panel.titleChanged.connect(self._rename_task)
        self.task_panel.dueChanged.connect(self._change_due)
        self.task_panel.repeatChanged.connect(self._change_repeat)
        content_layout.addWidget(self.task_panel, 1)

        self.right_column = QWidget()
        self.right_column.setFixedWidth(294)
        right_layout = QVBoxLayout(self.right_column)
        right_layout.setContentsMargins(0, 1, 0, 0)
        right_layout.setSpacing(15)

        self._build_calendar_card(right_layout)
        self._build_upcoming_card(right_layout)
        right_layout.addStretch(1)
        content_layout.addWidget(self.right_column)

        self._date_timer = QTimer(self)
        self._date_timer.setInterval(60_000)
        self._date_timer.timeout.connect(self._check_day_rollover)
        self._date_timer.start()

        self._make_shortcuts()
        self._install_resize_handles()
        self._restore_geometry()
        self._refresh(reset_composer=True, reset_scroll=True)
        self._set_initial_status()
        self._setup_reminders()

    # --------------------------------------------------------------- chrome
    def _add_shadow(self) -> None:
        effect = QGraphicsDropShadowEffect(self.surface)
        effect.setBlurRadius(42)
        effect.setOffset(0, 12)
        effect.setColor(QColor(18, 34, 30, 72))
        self.surface.setGraphicsEffect(effect)
        self._shadow = effect

    def _install_resize_handles(self) -> None:
        self._handles: list[ResizeHandle] = []
        specs = [
            (Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor),
            (Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor),
            (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.CursorShape.SizeFDiagCursor),
            (Qt.Edge.RightEdge | Qt.Edge.TopEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.LeftEdge | Qt.Edge.BottomEdge, Qt.CursorShape.SizeBDiagCursor),
            (Qt.Edge.RightEdge | Qt.Edge.BottomEdge, Qt.CursorShape.SizeFDiagCursor),
        ]
        for edges, cursor in specs:
            handle = ResizeHandle(self.surface, edges, cursor)
            self._handles.append(handle)
        self.surface.installEventFilter(self)
        self._position_resize_handles()

    def _position_resize_handles(self) -> None:
        if not hasattr(self, "_handles"):
            return
        width = self.surface.width()
        height = self.surface.height()
        m = self._resize_margin
        corner = 11
        top, bottom, left, right, tl, tr, bl, br = self._handles
        top.setGeometry(corner, 0, max(0, width - 2 * corner), m)
        bottom.setGeometry(corner, height - m, max(0, width - 2 * corner), m)
        left.setGeometry(0, corner, m, max(0, height - 2 * corner))
        right.setGeometry(width - m, corner, m, max(0, height - 2 * corner))
        tl.setGeometry(0, 0, corner, corner)
        tr.setGeometry(width - corner, 0, corner, corner)
        bl.setGeometry(0, height - corner, corner, corner)
        br.setGeometry(width - corner, height - corner, corner, corner)
        for handle in self._handles:
            handle.raise_()
            handle.setVisible(not self.isMaximized())

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.surface and event.type() == QEvent.Type.Resize:
            self._position_resize_handles()
        return super().eventFilter(watched, event)

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        QTimer.singleShot(0, self._update_window_chrome)

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_window_chrome()

    def _update_window_chrome(self) -> None:
        maximized = self.isMaximized()
        margin = 0 if maximized else self._outer_margin
        self._outer_layout.setContentsMargins(margin, margin, margin, margin)
        self.surface.setProperty("maximized", maximized)
        self.sidebar.setProperty("maximized", maximized)
        self.body.setProperty("maximized", maximized)
        self._shadow.setEnabled(not maximized)
        for widget in (self.surface, self.sidebar, self.body):
            repolish(widget)
        self.topbar.set_maximized(maximized)
        for handle in getattr(self, "_handles", []):
            handle.setVisible(not maximized)
        if not maximized:
            QTimer.singleShot(0, self._position_resize_handles)

    # -------------------------------------------------------------- geometry
    def _restore_geometry(self) -> None:
        restored = False
        if self.persist_geometry:
            values = []
            for key in ("window/x", "window/y", "window/w", "window/h"):
                value = self._settings.value(key)
                try:
                    values.append(int(value))
                except (TypeError, ValueError):
                    values = []
                    break
            if len(values) == 4:
                width = max(self.minimumWidth(), values[2])
                height = max(self.minimumHeight(), values[3])
                candidate = QRect(values[0], values[1], width, height)
                visible = any(
                    not screen.availableGeometry().intersected(candidate).isEmpty()
                    for screen in QApplication.screens()
                )
                if visible:
                    self.setGeometry(candidate)
                    restored = True

        if not restored:
            screen = QApplication.primaryScreen()
            available = screen.availableGeometry() if screen else None
            if available is not None:
                width = min(1220, max(self.minimumWidth(), available.width() - 48))
                height = min(820, max(662, available.height() - 36))
                x = available.x() + (available.width() - width) // 2
                y = available.y() + (available.height() - height) // 2
                self.setGeometry(x, y, width, height)
            else:
                self.resize(1220, 820)

    def _save_geometry(self) -> None:
        if not self.persist_geometry:
            return
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        self._settings.setValue("window/x", geometry.x())
        self._settings.setValue("window/y", geometry.y())
        self._settings.setValue("window/w", geometry.width())
        self._settings.setValue("window/h", geometry.height())
        self._settings.sync()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_geometry()
        if self._mini is not None:
            self._mini.close()
        if self._reminder_popup is not None:
            self._reminder_popup.close()
        super().closeEvent(event)

    # --------------------------------------------------------------- panels
    def _build_calendar_card(self, parent_layout: QVBoxLayout) -> None:
        card = QFrame()
        card.setObjectName("calendarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(17, 15, 17, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(1, 0, 0, 0)
        header.setSpacing(7)
        icon_label = QLabel()
        icon_label.setPixmap(icons.icon_pixmap("calendar", theme.ACCENT, 15))
        icon_label.setFixedSize(16, 16)
        header.addWidget(icon_label)
        title = QLabel("截止日历")
        title.setFont(theme.make_font(13, weight=QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK};")
        header.addWidget(title)
        header.addStretch(1)
        self.calendar_reset = QPushButton("回到今天")
        self.calendar_reset.setObjectName("flatButton")
        self.calendar_reset.setFont(theme.make_font(10))
        self.calendar_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.calendar_reset.setFixedHeight(24)
        self.calendar_reset.hide()
        self.calendar_reset.clicked.connect(lambda: self._set_view(ViewKind.TODAY))
        header.addWidget(self.calendar_reset)
        layout.addLayout(header)

        self.month_calendar = MonthCalendar()
        self.month_calendar.dateClicked.connect(self._on_calendar_date)
        layout.addWidget(self.month_calendar)

        legend = QHBoxLayout()
        legend.setContentsMargins(2, 2, 0, 0)
        legend.setSpacing(6)
        for color, text in ((theme.ACCENT, "有未完成"), (theme.MUTED_LIGHT, "仅有已完成")):
            dot = QLabel()
            dot.setFixedSize(5, 5)
            dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
            legend.addWidget(dot)
            label = QLabel(text)
            label.setFont(theme.make_font(9))
            label.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
            legend.addWidget(label)
            legend.addSpacing(6)
        legend.addStretch(1)
        layout.addLayout(legend)
        parent_layout.addWidget(card)

    def _build_upcoming_card(self, parent_layout: QVBoxLayout) -> None:
        self.upcoming_card = QFrame()
        self.upcoming_card.setObjectName("upcomingCard")
        layout = QVBoxLayout(self.upcoming_card)
        layout.setContentsMargins(17, 15, 17, 15)
        layout.setSpacing(9)

        header = QHBoxLayout()
        header.setContentsMargins(1, 0, 0, 0)
        header.setSpacing(7)
        icon_label = QLabel()
        icon_label.setPixmap(icons.icon_pixmap("bell", theme.GOLD, 15))
        icon_label.setFixedSize(16, 16)
        header.addWidget(icon_label)
        title = QLabel("临近截止")
        title.setFont(theme.make_font(13, weight=QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {theme.INK};")
        header.addWidget(title)
        header.addStretch(1)
        self.upcoming_count = QLabel("")
        self.upcoming_count.setFont(theme.make_font(10))
        self.upcoming_count.setStyleSheet(f"color: {theme.MUTED_LIGHT};")
        header.addWidget(self.upcoming_count)
        layout.addLayout(header)

        self.upcoming_list = QVBoxLayout()
        self.upcoming_list.setContentsMargins(0, 1, 0, 0)
        self.upcoming_list.setSpacing(2)
        layout.addLayout(self.upcoming_list)
        parent_layout.addWidget(self.upcoming_card)

    # ---------------------------------------------------------------- actions
    def _make_shortcuts(self) -> None:
        self._shortcuts = []
        for sequence, callback in (
            ("Ctrl+N", self.task_panel.focus_composer),
            ("Ctrl+M", self._toggle_mini),
            ("Ctrl+1", lambda: self._set_view(ViewKind.TODAY)),
            ("Ctrl+2", lambda: self._set_view(ViewKind.ALL)),
            ("Ctrl+3", lambda: self._set_view(ViewKind.UPCOMING)),
            ("Ctrl+4", lambda: self._set_view(ViewKind.COMPLETED)),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _set_initial_status(self) -> None:
        path_text = str(self.store.path)
        if self.store.load_warning:
            self.topbar.set_status(
                "任务数据已恢复",
                tone="warn",
                tooltip=self.store.load_warning,
            )
            QTimer.singleShot(
                500,
                lambda: QMessageBox.warning(self, "数据恢复", self.store.load_warning or ""),
            )
        else:
            self.topbar.set_status(
                "所有更改已自动保存",
                tone="ok",
                tooltip=f"任务保存在本机：{path_text}",
            )

    # -------------------------------------------------------------- reminders
    def _setup_reminders(self) -> None:
        if not self.enable_reminders:
            self.topbar.set_reminders_enabled(False)
            self.topbar.reminder_button.setEnabled(False)
            self.topbar.reminder_button.setToolTip("截止提醒已在测试中禁用")
            return
        self._reminder_service = ReminderService(
            self.store,
            self._settings,
            parent=self,
        )
        self._reminder_service.reminderDue.connect(self._on_reminder_due)
        self._reminder_service.enabledChanged.connect(
            self.topbar.set_reminders_enabled
        )
        self.topbar.set_reminders_enabled(self._reminder_service.enabled)

    def _open_reminders_menu(self) -> None:
        if self._reminder_service is None:
            return
        menu = QMenu(self)
        menu.setFont(theme.make_font(11))
        toggle = QAction(
            "截止提醒 · 已开启"
            if self._reminder_service.enabled
            else "截止提醒 · 已关闭",
            menu,
        )
        toggle.setCheckable(True)
        toggle.setChecked(self._reminder_service.enabled)
        menu.addAction(toggle)
        schedule_one = menu.addAction("09:00 · 今天 / 逾期未完成")
        schedule_one.setEnabled(False)
        schedule_two = menu.addAction("20:00 · 明天到期")
        schedule_two.setEnabled(False)
        menu.addSeparator()
        preview = menu.addAction("预览提醒")
        toggle.triggered.connect(self._set_reminders_enabled)
        preview.triggered.connect(self._preview_reminder)
        menu.exec(
            self.topbar.reminder_button.mapToGlobal(
                QPoint(0, self.topbar.reminder_button.height() + 4)
            )
        )

    def _set_reminders_enabled(self, enabled: bool) -> None:
        if self._reminder_service is None:
            return
        self._reminder_service.set_enabled(enabled)
        self.topbar.set_reminders_enabled(enabled)
        self.topbar.set_status(
            "截止提醒已开启" if enabled else "截止提醒已关闭",
            tone="ok",
            tooltip=reminder_schedule_text(),
        )

    def _preview_reminder(self) -> None:
        event = build_reminder_event(
            self.store.tasks,
            date.today(),
            include_morning=True,
            include_evening=True,
        )
        if event is None:
            self.topbar.set_status(
                "当前没有临期任务可供预览",
                tone="ok",
                tooltip="给任务设置今天、明天或更早的截止日期后再试。",
            )
            return
        self._show_reminder(event)

    def _on_reminder_due(self, event: object) -> None:
        if isinstance(event, ReminderEvent):
            self._show_reminder(event)

    def _show_reminder(self, event: ReminderEvent) -> None:
        if self._reminder_popup is None:
            self._reminder_popup = ReminderPopup(None)
            self._reminder_popup.openRequested.connect(self._restore_full)
        self._reminder_popup.show_event(event, date.today())

    # -------------------------------------------------------------- mini view
    def _toggle_mini(self) -> None:
        if self._mini is not None and self._mini.isVisible():
            self._restore_full()
        else:
            self.show_mini()

    def show_mini(self) -> None:
        if self._mini is None:
            self._mini = MiniWindow(self._settings)
            self._mini.completionChanged.connect(self._toggle_task)
            self._mini.taskAdded.connect(self._add_task_from_mini)
            self._mini.restoreRequested.connect(self._restore_full)
            self._mini.quitRequested.connect(self._quit_application)
        self._mini.set_data(list(self.store.tasks), self.today)
        self._mini.restore_position()
        self._mini.show()
        self._mini.raise_()
        self._mini.activateWindow()
        self.hide()

    def _restore_full(self) -> None:
        if self._mini is not None:
            self._mini.save_position()
            self._mini.hide()
        if self.isMaximized():
            self.showMaximized()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def _quit_application(self) -> None:
        self._save_geometry()
        if self._mini is not None:
            self._mini.save_position()
            self._mini.close()
        if self._reminder_popup is not None:
            self._reminder_popup.close()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _add_task_from_mini(self, title: str, due: object) -> None:
        if self._mini is None:
            return
        due_date = due if isinstance(due, date) else None
        try:
            self.store.add(title, due_date)
        except StoreError as exc:
            self._notify_save_error(exc)
            self._mini.show_add_error()
            return
        self._notify_saved()
        self._mini.confirm_added()
        self._refresh(reset_scroll=False)

    def _set_view(self, view: ViewKind) -> None:
        self.current_view = view
        self.selected_date = None
        self.sidebar.set_current(view)
        self._refresh(reset_composer=True, reset_scroll=True)

    def _on_calendar_date(self, value: object) -> None:
        if not isinstance(value, date):
            return
        if value == self.today:
            self.current_view = ViewKind.TODAY
            self.selected_date = None
            self.sidebar.set_current(ViewKind.TODAY)
            self._refresh(reset_composer=True, reset_scroll=True)
            return
        self.current_view = ViewKind.DATE
        self.selected_date = value
        self.sidebar.set_current(None)
        self._refresh(reset_composer=True, reset_scroll=True)

    def _check_day_rollover(self) -> None:
        if date.today() == self.today:
            return
        self.today = date.today()
        self.sidebar.set_today(self.today)
        self.task_panel.set_today(self.today)
        self.month_calendar.set_today(self.today)
        self._refresh(reset_composer=True, reset_scroll=True)

    # ---------------------------------------------------------------- refresh
    def _refresh(
        self,
        *,
        reset_composer: bool = False,
        reset_scroll: bool = False,
    ) -> None:
        self.task_panel.set_today(self.today)
        self.sidebar.set_today(self.today)
        self.sidebar.set_current(
            None if self.current_view is ViewKind.DATE else self.current_view
        )
        tasks = list(self.store.tasks)
        counts_map = counts(tasks, self.today)
        self.sidebar.set_counts(counts_map)
        done, total, percent = today_progress(tasks, self.today)
        self.sidebar.set_progress(done, total, percent)

        self.month_calendar.set_marks(due_marks(tasks))
        if self.current_view is ViewKind.TODAY:
            self.month_calendar.set_selected(self.today)
        elif self.current_view is ViewKind.DATE:
            self.month_calendar.set_selected(self.selected_date)
        else:
            self.month_calendar.set_selected(None)
        self.calendar_reset.setVisible(self.current_view is ViewKind.DATE)

        visible = visible_tasks(
            tasks,
            self.current_view,
            self.today,
            self.selected_date,
        )
        kicker, title, subtitle = self._header_copy(visible)
        default_due = self._default_due()
        allow_add = self.current_view is not ViewKind.COMPLETED
        self.task_panel.render(
            view=self.current_view,
            kicker=kicker,
            title=title,
            subtitle=subtitle,
            tasks=visible,
            allow_add=allow_add,
            default_due=default_due,
            reset_composer=reset_composer,
            reset_scroll=reset_scroll,
        )
        self._refresh_upcoming(tasks)
        if self._mini is not None:
            self._mini.set_data(tasks, self.today)

    def _header_copy(self, visible: list[Task]) -> tuple[str, str, str]:
        pending_count = sum(not task.completed for task in visible)
        done_count = sum(task.completed for task in visible)
        if self.current_view is ViewKind.TODAY:
            kicker = f"{full_date_text(self.today)} · {weekday_text(self.today)}"
            title = "今天"
            if pending_count and done_count:
                subtitle = f"{pending_count} 项待办 · {done_count} 项已完成"
            elif pending_count:
                subtitle = f"{pending_count} 项待办 · 按自己的节奏来"
            elif done_count:
                subtitle = "今天的事项都完成了，辛苦了。"
            else:
                subtitle = "给自己留一点空白。"
        elif self.current_view is ViewKind.ALL:
            total = len(visible)
            kicker = f"全部清单 · 共 {total} 项"
            title = "全部任务"
            if total == 0:
                subtitle = "从第一件小事开始。"
            elif done_count:
                subtitle = f"{pending_count} 项待办 · {done_count} 项已完成"
            else:
                subtitle = f"{pending_count} 项待办 · 慢慢来"
        elif self.current_view is ViewKind.UPCOMING:
            start = self.today + timedelta(days=1)
            end = self.today + timedelta(days=7)
            kicker = date_range_text(start, end)
            title = "未来 7 天"
            if pending_count and done_count:
                subtitle = f"{pending_count} 项待办 · {done_count} 项已完成"
            elif pending_count:
                subtitle = f"{pending_count} 项待办 · 提前一点，更从容"
            elif done_count:
                subtitle = "这一周的任务都完成了。"
            else:
                subtitle = "未来一周暂时没有截止任务。"
        elif self.current_view is ViewKind.COMPLETED:
            kicker = f"已经完成的 {done_count} 件小事"
            title = "已完成"
            subtitle = "每一件完成的小事，都算数。"
        else:
            selected = self.selected_date or self.today
            kicker = f"{full_date_text(selected)} · {weekday_text(selected)}"
            title = f"{selected.month}月{selected.day}日"
            if pending_count:
                subtitle = f"{pending_count} 项待办"
                if done_count:
                    subtitle += f" · {done_count} 项已完成"
            elif done_count:
                subtitle = "这一天的任务都完成了。"
            else:
                subtitle = "这一天还没有截止任务。"
        return kicker, title, subtitle

    def _default_due(self) -> date | None:
        if self.current_view is ViewKind.TODAY:
            return self.today
        if self.current_view is ViewKind.UPCOMING:
            return self.today + timedelta(days=1)
        if self.current_view is ViewKind.DATE:
            return self.selected_date
        return None

    def _refresh_upcoming(self, tasks: list[Task]) -> None:
        clear_layout(self.upcoming_list)
        pending_due = sorted(
            (task for task in tasks if not task.completed and task.due is not None),
            key=lambda task: task.due or date.max,
        )
        if not pending_due:
            self.upcoming_count.setText("")
            empty = QLabel("暂无临近截止的任务")
            empty.setFont(theme.make_font(11))
            empty.setStyleSheet(f"color: {theme.MUTED_LIGHT}; padding: 6px 1px 3px 1px;")
            self.upcoming_list.addWidget(empty)
            return

        self.upcoming_count.setText(f"{len(pending_due)} 项")
        for task in pending_due[:3]:
            self.upcoming_list.addWidget(self._make_upcoming_row(task))
        if len(pending_due) > 3:
            more = QLabel(f"还有 {len(pending_due) - 3} 项待办")
            more.setFont(theme.make_font(9.5))
            more.setStyleSheet(f"color: {theme.MUTED_LIGHT}; padding-left: 1px;")
            self.upcoming_list.addWidget(more)

    def _make_upcoming_row(self, task: Task) -> QWidget:
        due = task.due or self.today
        delta = (due - self.today).days
        if delta < 0:
            badge_text = "逾期"
            fg, bg = theme.CORAL, theme.CORAL_SOFT
        elif delta == 0:
            badge_text = "今天"
            fg, bg = theme.AMBER, theme.AMBER_SOFT
        elif delta == 1:
            badge_text = "明天"
            fg, bg = theme.ACCENT_DARK, theme.ACCENT_SOFT
        else:
            badge_text = f"{due.month}/{due.day}"
            fg, bg = theme.INK_SOFT, "#F2F4F0"

        row = QWidget()
        row.setFixedHeight(34)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(45, 25)
        badge.setFont(theme.make_font(9.5, weight=QFont.Weight.DemiBold))
        badge.setStyleSheet(
            f"color: {fg}; background: {bg}; border-radius: 7px;"
        )
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title = ElidedLabel(task.title)
        title.setFont(theme.make_font(11.5))
        title.setStyleSheet(f"color: {theme.INK_SOFT};")
        title.setToolTip(
            f"{task.title}\n截止：{full_date_text(due)} · {weekday_text(due)}"
        )
        layout.addWidget(title, 1)
        return row

    # ------------------------------------------------------------- mutations
    def _notify_saved(self) -> None:
        self._save_error = False
        self.topbar.set_status(
            "所有更改已自动保存",
            tone="ok",
            tooltip=f"任务保存在本机：{self.store.path}",
        )

    def _notify_save_error(self, exc: Exception) -> None:
        self._save_error = True
        self.topbar.set_status(
            "保存失败 · 请检查磁盘权限",
            tone="error",
            tooltip=str(exc),
        )

    def _add_task(self, title: str, due: object, repeat: object) -> None:
        due_date = due if isinstance(due, date) else None
        repeat_rule = repeat if isinstance(repeat, str) else None
        if repeat_rule is not None and due_date is None:
            due_date = self.today
        try:
            task = self.store.add(title, due_date, repeat_rule)
        except (StoreError, ValueError) as exc:
            self._notify_save_error(exc)
            return
        self._notify_saved()
        self.task_panel.reset_composer_after_add()
        self._refresh(reset_scroll=False)
        self.task_panel.reveal_task(task.id)
        self.task_panel.focus_composer()

    def _toggle_task(self, task_id: str, completed: bool) -> None:
        task = self.store.get(task_id)
        follow_up: Task | None = None
        try:
            if task is not None and task.repeat is not None:
                if completed:
                    _completed, follow_up = self.store.complete_recurring(
                        task_id, self.today
                    )
                else:
                    self.store.reopen_recurring(task_id)
            else:
                self.store.set_completed(task_id, completed)
        except StoreError as exc:
            self._notify_save_error(exc)
            self._refresh()
            return
        self._notify_saved()
        self._refresh()
        if follow_up is not None and follow_up.due is not None:
            self.topbar.set_status(
                f"已完成 · 下次 {full_date_text(follow_up.due)}",
                tone="ok",
                tooltip="重复事项已自动生成下一次。",
            )
        elif task is not None and task.repeat is not None and not completed:
            self.topbar.set_status(
                "已恢复重复事项",
                tone="ok",
                tooltip="下一次重复已收回。",
            )

    def _delete_task(self, task_id: str) -> None:
        try:
            deleted = self.store.delete(task_id)
        except StoreError as exc:
            self._notify_save_error(exc)
            return
        if deleted:
            self._notify_saved()
            self._refresh()

    def _rename_task(self, task_id: str, title: str) -> None:
        try:
            renamed = self.store.rename(task_id, title)
        except StoreError as exc:
            self._notify_save_error(exc)
            self._refresh()
            return
        if renamed:
            self._notify_saved()
            self._refresh()

    def _change_due(self, task_id: str, due: object) -> None:
        due_date = due if isinstance(due, date) else None
        try:
            changed = self.store.set_due(task_id, due_date)
        except StoreError as exc:
            self._notify_save_error(exc)
            self._refresh()
            return
        if changed:
            self._notify_saved()
            self._refresh()

    def _change_repeat(self, task_id: str, repeat: object) -> None:
        repeat_rule = repeat if isinstance(repeat, str) else None
        try:
            changed = self.store.set_repeat(
                task_id,
                repeat_rule,
                default_due=self.today,
            )
        except (StoreError, ValueError) as exc:
            self._notify_save_error(exc)
            self._refresh()
            return
        if changed:
            self._notify_saved()
            self._refresh()
