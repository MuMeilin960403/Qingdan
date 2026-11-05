"""Small flat text button used inside popovers."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractButton, QWidget


class TextChipButton(QAbstractButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._font = QFont()
        self._font.setFamilies(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"])
        self._font.setPixelSize(12)

    def setFont(self, font: QFont) -> None:  # noqa: N802
        self._font = font
        super().setFont(font)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self._font)
        return QSize(metrics.horizontalAdvance(self.text()) + 24, 30)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        from .. import theme

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        bg = QColor(theme.CORAL_SOFT) if self._hover and self.text() == "清除" else (
            QColor(theme.ACCENT_SOFT) if self._hover else QColor(theme.SURFACE_SOFT)
        )
        if self.text() == "清除" and not self._hover:
            bg = QColor(0, 0, 0, 0)
        border = QColor(theme.BORDER) if self.text() != "清除" else QColor(0, 0, 0, 0)
        if self._hover and self.text() != "清除":
            border = QColor("#C9DCD3")
        painter.setPen(border if border.alpha() else Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        color = QColor(theme.CORAL) if self._hover and self.text() == "清除" else QColor(theme.INK_SOFT)
        if self._hover and self.text() != "清除":
            color = QColor(theme.ACCENT_DARK)
        painter.setFont(self._font)
        painter.setPen(color)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text())
