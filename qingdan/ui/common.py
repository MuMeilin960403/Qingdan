"""Reusable painted widgets shared across the app."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import icons, theme
from ..filters import due_text
from ..recurrence import repeat_label


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            # Hide immediately so removed cards can never flash on top of the
            # replacement content before deleteLater is processed.
            widget.hide()
            widget.deleteLater()
        child = item.layout()
        if child is not None:
            clear_layout(child)


class BrandMark(QWidget):
    def __init__(self, size: int = 40, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.GOLD))
        painter.drawRoundedRect(rect, self.width() * 0.31, self.width() * 0.31)
        pen = QPen(QColor(theme.SIDEBAR_DEEP), 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(self.width() * 0.27, self.height() * 0.52)
        path.lineTo(self.width() * 0.44, self.height() * 0.68)
        path.lineTo(self.width() * 0.74, self.height() * 0.34)
        painter.drawPath(path)


class NavButton(QAbstractButton):
    def __init__(
        self,
        icon_name: str,
        text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self._count = 0
        self._hover = False
        self.setText(text)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(text)

    def set_count(self, value: int) -> None:
        value = max(0, int(value))
        if value != self._count:
            self._count = value
            self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(0, 1, 0, -1)
        selected = self.isChecked()
        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 24))
            painter.drawRoundedRect(rect, 11, 11)
            painter.setBrush(QColor(theme.GOLD))
            painter.drawRoundedRect(QRectF(0, 14, 3, self.height() - 28), 1.5, 1.5)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(233, 187, 107, 118), 1))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 11, 11)
        elif self._hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 11))
            painter.drawRoundedRect(rect, 11, 11)

        icon_color = (
            QColor(theme.GOLD) if selected else QColor(theme.SIDEBAR_TEXT)
        )
        if not selected:
            icon_color.setAlpha(188)
        icons.draw_icon(
            painter,
            self.icon_name,
            QRectF(16, (self.height() - 19) / 2, 19, 19),
            icon_color,
            stroke=1.65,
        )

        font = theme.make_font(
            14,
            weight=QFont.Weight.DemiBold
            if selected
            else QFont.Weight.Medium,
        )
        painter.setFont(font)
        painter.setPen(
            QColor(theme.SIDEBAR_TEXT) if selected else QColor(theme.SIDEBAR_MUTED).darker(110)
        )
        text_rect = QRectF(46, 0, self.width() - 86, self.height())
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self.text(),
        )

        if self._count:
            label = "99+" if self._count > 99 else str(self._count)
            count_font = theme.make_font(11, weight=QFont.Weight.DemiBold)
            metrics = QFontMetrics(count_font)
            width = max(23, metrics.horizontalAdvance(label) + 12)
            badge = QRectF(self.width() - width - 14, (self.height() - 21) / 2, width, 21)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(255, 255, 255, 25) if selected else QColor(255, 255, 255, 12)
            )
            painter.drawRoundedRect(badge, 10.5, 10.5)
            painter.setFont(count_font)
            painter.setPen(QColor(theme.GOLD) if selected else QColor(theme.SIDEBAR_MUTED))
            painter.drawText(badge, int(Qt.AlignmentFlag.AlignCenter), label)




class IconButton(QAbstractButton):
    def __init__(
        self,
        icon_name: str,
        *,
        button_size: int = 30,
        icon_size: int = 16,
        color: str = theme.MUTED,
        hover_color: str = theme.INK,
        hover_bg: str = "#F2EFE8",
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self._icon_size = icon_size
        self._color = color
        self._hover_color = hover_color
        self._hover_bg = QColor(hover_bg)
        self._hover = False
        self.setFixedSize(button_size, button_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)

    def set_icon(self, name: str) -> None:
        self.icon_name = name
        self.update()

    def set_color(self, color: str, *, hover_color: str | None = None) -> None:
        self._color = color
        if hover_color is not None:
            self._hover_color = hover_color
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hover and self.isEnabled():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._hover_bg)
            painter.drawRoundedRect(
                QRectF(1, 1, self.width() - 2, self.height() - 2), 8, 8
            )
        color = (
            QColor(self._hover_color)
            if self._hover and self.isEnabled()
            else QColor(self._color)
        )
        if not self.isEnabled():
            color.setAlpha(100)
        size = self._icon_size
        icons.draw_icon(
            painter,
            self.icon_name,
            QRectF(
                (self.width() - size) / 2,
                (self.height() - size) / 2,
                size,
                size,
            ),
            color,
            stroke=1.7,
        )


class WindowButton(QAbstractButton):
    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._hover = False
        labels = {"minimize": "最小化", "maximize": "最大化", "restore": "还原", "close": "关闭"}
        self.setToolTip(labels.get(kind, ""))
        self.setAccessibleName(labels.get(kind, ""))
        self.setFixedSize(32, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_kind(self, kind: str) -> None:
        self._kind = kind
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._hover:
            bg = QColor("#F3DED7") if self._kind == "close" else QColor(28, 46, 41, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 7, 7)
        color = QColor(theme.CORAL) if self._hover and self._kind == "close" else QColor(theme.INK_SOFT)
        pen = QPen(color, 1.45)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        cx, cy = self.width() / 2, self.height() / 2
        if self._kind == "minimize":
            painter.drawLine(QPointF(cx - 5, cy + 3), QPointF(cx + 5, cy + 3))
        elif self._kind == "maximize":
            painter.drawRoundedRect(QRectF(cx - 4.5, cy - 4.5, 9, 9), 1.5, 1.5)
        elif self._kind == "restore":
            painter.drawRoundedRect(QRectF(cx - 5, cy - 3.5, 8, 8), 1.2, 1.2)
            painter.drawRoundedRect(QRectF(cx - 2, cy - 5.5, 8, 8), 1.2, 1.2)
        else:
            painter.drawLine(QPointF(cx - 4, cy - 4), QPointF(cx + 4, cy + 4))
            painter.drawLine(QPointF(cx + 4, cy - 4), QPointF(cx - 4, cy + 4))


class CheckCircle(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(25, 25)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._hover = False

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(2.2, 2.2, 20.6, 20.6)
        if self.isChecked():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawEllipse(rect)
            icons.draw_icon(
                painter,
                "check",
                QRectF(6.1, 6.1, 12.8, 12.8),
                theme.SURFACE,
                stroke=2.1,
            )
        else:
            border = QColor(theme.ACCENT) if self._hover else QColor("#CFC7B8")
            painter.setBrush(QColor(255, 255, 255, 0))
            painter.setPen(QPen(border, 1.65))
            painter.drawEllipse(rect)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(theme.GOLD), 1.2))
            painter.drawEllipse(QRectF(0.8, 0.8, 23.4, 23.4))


class CircularAddButton(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("添加任务")
        self.setAccessibleName("添加任务")
        self._hover = False
        self.setEnabled(False)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        if not self.isEnabled():
            bg = QColor("#E7ECE8")
            color = QColor("#B8C4BD")
        else:
            bg = QColor(theme.ACCENT_DARK if self._hover else theme.ACCENT)
            color = QColor(theme.SURFACE)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawEllipse(rect)
        icons.draw_icon(
            painter,
            "plus",
            QRectF(9, 9, 18, 18),
            color,
            stroke=2.0,
        )


class ProgressBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._display = 0.0
        self._target = 0.0
        self._animation = QPropertyAnimation(self, b"displayValue", self)
        self._animation.setDuration(360)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setFixedHeight(7)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def get_display_value(self) -> float:
        return self._display

    def set_display_value(self, value: float) -> None:
        self._display = value
        self.update()

    displayValue = Property(float, get_display_value, set_display_value)

    def set_value(self, value: int, animate: bool = True) -> None:
        self._target = max(0, min(100, int(value)))
        self._animation.stop()
        if not animate:
            self.set_display_value(float(self._target))
            return
        self._animation.setStartValue(self._display)
        self._animation.setEndValue(float(self._target))
        self._animation.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 28))
        painter.drawRoundedRect(rect, 3.5, 3.5)
        if self._display <= 0:
            return
        fill_width = max(7.0, rect.width() * self._display / 100.0)
        gradient = QLinearGradient(0, 0, fill_width, 0)
        gradient.setColorAt(0, QColor(theme.GOLD))
        gradient.setColorAt(1, QColor("#F6D79B"))
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(0, 0, fill_width, self.height()), 3.5, 3.5)


class DuePill(QAbstractButton):
    """A compact, editable due-date chip."""

    def __init__(
        self,
        *,
        today: date,
        due: date | None,
        completed: bool = False,
        allow_empty: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._today = today
        self._due = due
        self._completed = completed
        self._allow_empty = allow_empty
        self._hover = False
        self._font = theme.make_font(12, weight=QFont.Weight.Medium)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip("点击设置截止日期")
        self.setAccessibleName("截止日期")
        self.setVisible(self._allow_empty or due is not None)

    def set_state(self, due: date | None, today: date, completed: bool) -> None:
        self._due = due
        self._today = today
        self._completed = completed
        self.setVisible(self._allow_empty or due is not None)
        self.updateGeometry()
        self.update()

    def _label(self) -> str:
        if self._due is None:
            return "截止日期"
        return due_text(self._due, self._today, completed=self._completed)

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self._font)
        return QSize(metrics.horizontalAdvance(self._label()) + 37, 28)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        bg = QColor(0, 0, 0, 0)
        border = QColor(0, 0, 0, 0)
        text = QColor(theme.MUTED)
        icon = QColor(theme.MUTED_LIGHT)

        if self._completed:
            text = QColor(theme.DONE)
            icon = QColor(theme.MUTED_LIGHT)
            if self._hover:
                bg = QColor("#F7F4ED")
        elif self._due is None:
            border = QColor(theme.BORDER)
            if self._hover:
                border = QColor(theme.BORDER_STRONG)
                bg = QColor(theme.SURFACE_SOFT)
        else:
            delta = (self._due - self._today).days
            if delta < 0:
                bg = QColor(theme.CORAL_SOFT)
                text = QColor(theme.CORAL)
                icon = QColor(theme.CORAL)
            elif delta == 0:
                bg = QColor(theme.AMBER_SOFT)
                text = QColor(theme.AMBER)
                icon = QColor(theme.AMBER)
            else:
                bg = QColor("#F1F5F2")
                text = QColor(theme.ACCENT_DARK)
                icon = QColor(theme.ACCENT)
            if self._hover:
                bg = bg.darker(104) if bg.lightness() < 245 else QColor("#E9F0EB")

        painter.setPen(QPen(border, 1) if border.alpha() else Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8.5, 8.5)

        icons.draw_icon(
            painter,
            "calendar",
            QRectF(9, 7.5, 13, 13),
            icon,
            stroke=1.7,
        )
        painter.setFont(self._font)
        painter.setPen(text)
        painter.drawText(
            QRectF(26, 0, self.width() - 33, self.height()),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self._label(),
        )


class RepeatPill(QAbstractButton):
    """A compact recurrence editor: icon-only when off, label pill when on."""

    def __init__(
        self,
        repeat: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repeat = repeat
        self._hover = False
        self._font = theme.make_font(11, weight=QFont.Weight.Medium)
        self.setFixedHeight(28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._sync_tooltip()

    @property
    def repeat(self) -> str | None:
        return self._repeat

    def set_repeat(self, repeat: str | None) -> None:
        self._repeat = repeat
        self._sync_tooltip()
        self.updateGeometry()
        self.update()

    def _sync_tooltip(self) -> None:
        if self._repeat is None:
            text = "设置重复"
        else:
            text = f"重复：{repeat_label(self._repeat)} · 点击修改"
        self.setToolTip(text)
        self.setAccessibleName(text)

    def sizeHint(self) -> QSize:
        if self._repeat is None:
            return QSize(28, 28)
        metrics = QFontMetrics(self._font)
        return QSize(metrics.horizontalAdvance(repeat_label(self._repeat)) + 42, 28)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(0.5, 0.5, -0.5, -0.5)
        active = self._repeat is not None
        if active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT_SOFT))
            painter.drawRoundedRect(rect, 8.5, 8.5)
            icon_color = QColor(theme.ACCENT)
            text_color = QColor(theme.ACCENT_DARK)
        else:
            if self._hover:
                painter.setPen(QPen(QColor(theme.BORDER), 1))
                painter.setBrush(QColor(theme.SURFACE_SOFT))
                painter.drawRoundedRect(rect, 8.5, 8.5)
            icon_color = QColor(theme.MUTED_LIGHT)
            text_color = QColor(theme.MUTED)
        if active:
            icons.draw_icon(
                painter,
                "repeat",
                QRectF(9, 7.5, 13, 13),
                icon_color,
                stroke=1.7,
            )
            painter.setFont(self._font)
            painter.setPen(text_color)
            painter.drawText(
                QRectF(25, 0, self.width() - 32, self.height()),
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                repeat_label(self._repeat),
            )
        else:
            icons.draw_icon(
                painter,
                "repeat",
                QRectF(7.5, 7.5, 13, 13),
                icon_color,
                stroke=1.7,
            )


class EmptyIllustration(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(112, 104)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#EAF1EA"))
        painter.drawEllipse(QRectF(8, 14, 92, 82))
        painter.setBrush(QColor("#F3E8D0"))
        painter.drawEllipse(QRectF(68, 10, 26, 26))

        painter.save()
        painter.translate(54, 53)
        painter.rotate(-6)
        painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        painter.setBrush(QColor(theme.SURFACE))
        painter.drawRoundedRect(QRectF(-27, -32, 56, 66), 9, 9)
        painter.setPen(QPen(QColor("#D9D1C2"), 1.2))
        painter.drawLine(QPointF(-16, -19), QPointF(17, -19))
        painter.drawLine(QPointF(-16, -10), QPointF(5, -10))
        for row in range(3):
            y = 1 + row * 12
            painter.setPen(QPen(QColor(theme.ACCENT), 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(-17, y), 3.5, 3.5)
            painter.setPen(QPen(QColor("#D9D1C2"), 1.2))
            painter.drawLine(QPointF(-8, y), QPointF(16 if row != 2 else 5, y))
        painter.restore()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.GOLD))
        painter.drawEllipse(QPointF(85, 77), 15, 15)
        icons.draw_icon(
            painter,
            "check",
            QRectF(77, 69, 16, 16),
            theme.SIDEBAR_DEEP,
            stroke=2.2,
        )


class EmptyState(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 24)
        layout.setSpacing(0)
        layout.addStretch(1)
        illustration = EmptyIllustration()
        layout.addWidget(illustration, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)
        self.title_label = QLabel("今天还没有安排")
        self.title_label.setFont(theme.make_font(16, weight=QFont.Weight.DemiBold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"color: {theme.INK};")
        layout.addWidget(self.title_label)
        layout.addSpacing(6)
        self.body_label = QLabel("在上方输入一件小事，给今天一个轻盈的开始。")
        self.body_label.setFont(theme.make_font(13))
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_label.setStyleSheet(f"color: {theme.MUTED};")
        layout.addWidget(self.body_label)
        layout.addStretch(1)

    def set_text(self, title: str, body: str) -> None:
        self.title_label.setText(title)
        self.body_label.setText(body)


class ElidedLabel(QLabel):
    """QLabel that elides long text while keeping the full value in a tooltip."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(text)
        self.setMinimumWidth(10)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text
        self.setToolTip(text)
        super().setText(text)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        metrics = QFontMetrics(self.font())
        text = metrics.elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            max(0, self.width()),
        )
        painter.drawText(
            self.rect(),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )


def attach_shadow(widget: QWidget, *, blur: int = 28, dy: int = 8, alpha: int = 30) -> None:
    from PySide6.QtWidgets import QGraphicsDropShadowEffect

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(28, 46, 41, alpha))
    widget.setGraphicsEffect(effect)
