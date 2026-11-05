"""Hand-drawn line icons and the Qingdan app mark."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from . import theme


def _pen(color: str | QColor, width: float) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def draw_icon(
    painter: QPainter,
    name: str,
    rect: QRectF,
    color: str | QColor,
    *,
    stroke: float = 1.8,
) -> None:
    """Paint a 24×24 outline icon into ``rect``."""

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = min(rect.width(), rect.height()) / 24.0
    painter.translate(
        rect.x() + (rect.width() - 24 * scale) / 2,
        rect.y() + (rect.height() - 24 * scale) / 2,
    )
    painter.scale(scale, scale)
    pen = _pen(color, stroke)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "inbox":
        path = QPainterPath()
        path.moveTo(3.5, 7.0)
        path.lineTo(3.5, 17.0)
        path.quadTo(3.5, 20.0, 6.5, 20.0)
        path.lineTo(17.5, 20.0)
        path.quadTo(20.5, 20.0, 20.5, 17.0)
        path.lineTo(20.5, 7.0)
        path.quadTo(20.5, 4.0, 17.5, 4.0)
        path.lineTo(6.5, 4.0)
        path.quadTo(3.5, 4.0, 3.5, 7.0)
        painter.drawPath(path)
        tray = QPainterPath()
        tray.moveTo(3.8, 13.5)
        tray.lineTo(8.0, 13.5)
        tray.lineTo(9.6, 16.0)
        tray.lineTo(14.4, 16.0)
        tray.lineTo(16.0, 13.5)
        tray.lineTo(20.2, 13.5)
        painter.drawPath(tray)
    elif name == "sun":
        painter.drawEllipse(QPointF(12, 12), 3.7, 3.7)
        for sx, sy, ex, ey in (
            (12, 2.7, 12, 4.4),
            (12, 19.6, 12, 21.3),
            (2.7, 12, 4.4, 12),
            (19.6, 12, 21.3, 12),
            (5.4, 5.4, 6.6, 6.6),
            (17.4, 17.4, 18.6, 18.6),
            (18.6, 5.4, 17.4, 6.6),
            (6.6, 17.4, 5.4, 18.6),
        ):
            painter.drawLine(QPointF(sx, sy), QPointF(ex, ey))
    elif name == "calendar":
        path = QPainterPath()
        path.addRoundedRect(QRectF(3.5, 5.0, 17.0, 15.0), 2.8, 2.8)
        painter.drawPath(path)
        painter.drawLine(QPointF(3.9, 9.2), QPointF(20.1, 9.2))
        painter.drawLine(QPointF(8.0, 2.9), QPointF(8.0, 6.1))
        painter.drawLine(QPointF(16.0, 2.9), QPointF(16.0, 6.1))
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(8.1, 12.6), 1.05, 1.05)
        painter.drawEllipse(QPointF(12.0, 12.6), 1.05, 1.05)
        painter.drawEllipse(QPointF(15.9, 12.6), 1.05, 1.05)
        painter.drawEllipse(QPointF(8.1, 16.2), 1.05, 1.05)
        painter.drawEllipse(QPointF(12.0, 16.2), 1.05, 1.05)
    elif name == "check-circle":
        painter.drawEllipse(QPointF(12, 12), 8.6, 8.6)
        path = QPainterPath()
        path.moveTo(8.0, 12.1)
        path.lineTo(10.8, 14.8)
        path.lineTo(16.2, 9.3)
        painter.drawPath(path)
    elif name == "check":
        path = QPainterPath()
        path.moveTo(5.5, 12.2)
        path.lineTo(9.8, 16.4)
        path.lineTo(18.5, 7.6)
        painter.drawPath(path)
    elif name == "plus":
        painter.drawLine(QPointF(12, 5.2), QPointF(12, 18.8))
        painter.drawLine(QPointF(5.2, 12), QPointF(18.8, 12))
    elif name == "chevron-left":
        path = QPainterPath()
        path.moveTo(14.5, 5.5)
        path.lineTo(8.0, 12.0)
        path.lineTo(14.5, 18.5)
        painter.drawPath(path)
    elif name == "chevron-right":
        path = QPainterPath()
        path.moveTo(9.5, 5.5)
        path.lineTo(16.0, 12.0)
        path.lineTo(9.5, 18.5)
        painter.drawPath(path)
    elif name == "chevron-down":
        path = QPainterPath()
        path.moveTo(5.5, 9.5)
        path.lineTo(12.0, 16.0)
        path.lineTo(18.5, 9.5)
        painter.drawPath(path)
    elif name == "trash":
        painter.drawLine(QPointF(4.5, 7.0), QPointF(19.5, 7.0))
        painter.drawLine(QPointF(9.2, 3.8), QPointF(14.8, 3.8))
        path = QPainterPath()
        path.moveTo(6.4, 7.2)
        path.lineTo(7.2, 19.0)
        path.quadTo(7.3, 20.4, 8.8, 20.4)
        path.lineTo(15.2, 20.4)
        path.quadTo(16.7, 20.4, 16.8, 19.0)
        path.lineTo(17.6, 7.2)
        painter.drawPath(path)
        painter.drawLine(QPointF(10.2, 10.6), QPointF(10.2, 16.8))
        painter.drawLine(QPointF(13.8, 10.6), QPointF(13.8, 16.8))
    elif name == "clock":
        painter.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        path = QPainterPath()
        path.moveTo(12.0, 7.0)
        path.lineTo(12.0, 12.3)
        path.lineTo(15.8, 14.4)
        painter.drawPath(path)
    elif name == "edit":
        path = QPainterPath()
        path.moveTo(4.0, 20.0)
        path.lineTo(5.0, 15.2)
        path.lineTo(15.4, 4.8)
        path.quadTo(16.6, 3.6, 17.8, 4.8)
        path.lineTo(19.2, 6.2)
        path.quadTo(20.4, 7.4, 19.2, 8.6)
        path.lineTo(8.8, 19.0)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(13.8, 6.4), QPointF(17.6, 10.2))
    elif name == "leaf":
        path = QPainterPath()
        path.moveTo(20.0, 4.5)
        path.cubicTo(11.0, 4.6, 5.0, 8.8, 5.0, 15.0)
        path.cubicTo(5.0, 18.0, 7.3, 20.0, 10.4, 20.0)
        path.cubicTo(16.2, 20.0, 19.7, 13.0, 20.0, 4.5)
        painter.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(5.4, 20.0)
        path2.quadTo(9.0, 12.0, 16.0, 8.2)
        painter.drawPath(path2)
    elif name == "bell":
        path = QPainterPath()
        path.moveTo(6.0, 17.2)
        path.lineTo(7.2, 15.8)
        path.lineTo(7.2, 10.5)
        path.quadTo(7.2, 5.8, 12.0, 5.8)
        path.quadTo(16.8, 5.8, 16.8, 10.5)
        path.lineTo(16.8, 15.8)
        path.lineTo(18.0, 17.2)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(5.5, 17.2), QPointF(18.5, 17.2))
        bell_clap = QPainterPath()
        bell_clap.moveTo(10.0, 20.0)
        bell_clap.quadTo(12.0, 21.5, 14.0, 20.0)
        painter.drawPath(bell_clap)
    elif name == "close":
        painter.drawLine(QPointF(6.0, 6.0), QPointF(18.0, 18.0))
        painter.drawLine(QPointF(18.0, 6.0), QPointF(6.0, 18.0))
    elif name in ("pin", "pin-off"):
        path = QPainterPath()
        path.moveTo(8.3, 9.0)
        path.quadTo(8.3, 4.8, 12.0, 4.8)
        path.quadTo(15.7, 4.8, 15.7, 9.0)
        path.lineTo(16.5, 14.0)
        path.lineTo(7.5, 14.0)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(12.0, 14.0), QPointF(12.0, 20.0))
        painter.drawLine(QPointF(8.6, 20.0), QPointF(15.4, 20.0))
        if name == "pin-off":
            painter.drawLine(QPointF(4.5, 4.5), QPointF(19.5, 19.5))
    elif name == "expand":
        painter.drawLine(QPointF(14.0, 4.0), QPointF(20.0, 4.0))
        painter.drawLine(QPointF(20.0, 4.0), QPointF(20.0, 10.0))
        painter.drawLine(QPointF(10.0, 20.0), QPointF(4.0, 20.0))
        painter.drawLine(QPointF(4.0, 20.0), QPointF(4.0, 14.0))
        painter.drawLine(QPointF(20.0, 4.0), QPointF(13.8, 10.2))
        painter.drawLine(QPointF(4.0, 20.0), QPointF(10.2, 13.8))
    elif name == "panel":
        path = QPainterPath()
        path.addRoundedRect(QRectF(3.5, 4.5, 17.0, 15.0), 3.0, 3.0)
        painter.drawPath(path)
        painter.drawLine(QPointF(3.9, 9.4), QPointF(20.1, 9.4))
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(6.3, 12.0, 4.6, 4.5), 1.0, 1.0)
    elif name == "repeat":
        path = QPainterPath()
        path.moveTo(5.0, 10.0)
        path.cubicTo(5.0, 6.0, 8.4, 4.5, 12.0, 4.5)
        path.lineTo(17.0, 4.5)
        painter.drawPath(path)
        arrow = QPainterPath()
        arrow.moveTo(14.5, 1.8)
        arrow.lineTo(17.4, 4.5)
        arrow.lineTo(14.5, 7.2)
        painter.drawPath(arrow)
        path2 = QPainterPath()
        path2.moveTo(19.0, 14.0)
        path2.cubicTo(19.0, 18.0, 15.6, 19.5, 12.0, 19.5)
        path2.lineTo(7.0, 19.5)
        painter.drawPath(path2)
        arrow2 = QPainterPath()
        arrow2.moveTo(9.5, 16.8)
        arrow2.lineTo(6.6, 19.5)
        arrow2.lineTo(9.5, 22.2)
        painter.drawPath(arrow2)
    elif name == "arrow-up":
        painter.drawLine(QPointF(12.0, 19.0), QPointF(12.0, 5.5))
        path = QPainterPath()
        path.moveTo(6.0, 11.5)
        path.lineTo(12.0, 5.5)
        path.lineTo(18.0, 11.5)
        painter.drawPath(path)
    elif name == "more":
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        for x in (6.0, 12.0, 18.0):
            painter.drawEllipse(QPointF(x, 12.0), 1.2, 1.2)
    else:
        painter.drawEllipse(QPointF(12, 12), 7, 7)

    painter.restore()


def icon_pixmap(
    name: str,
    color: str | QColor,
    size: int = 20,
    *,
    dpr: float = 2.0,
    stroke: float = 1.8,
) -> QPixmap:
    pixmap = QPixmap(round(size * dpr), round(size * dpr))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    draw_icon(painter, name, QRectF(0, 0, size, size), color, stroke=stroke)
    painter.end()
    return pixmap


def icon(name: str, color: str | QColor, size: int = 20, *, stroke: float = 1.8) -> QIcon:
    return QIcon(icon_pixmap(name, color, size, stroke=stroke))


def make_app_pixmap(size: int = 256) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = size / 256.0
    painter.scale(scale, scale)

    painter.setPen(Qt.PenStyle.NoPen)
    gradient = QLinearGradient(20, 20, 236, 236)
    gradient.setColorAt(0, QColor("#1E4C41"))
    gradient.setColorAt(1, QColor(theme.SIDEBAR_DEEP))
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(8, 8, 240, 240), 56, 56)

    painter.setBrush(QColor(theme.GOLD))
    painter.drawEllipse(QPointF(128, 128), 70, 70)

    pen = QPen(QColor(theme.SIDEBAR_DEEP), 20)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    path = QPainterPath()
    path.moveTo(96, 129)
    path.lineTo(119, 152)
    path.lineTo(164, 103)
    painter.drawPath(path)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(theme.GOLD))
    painter.drawEllipse(QPointF(178, 69), 8, 8)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon_obj = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon_obj.addPixmap(make_app_pixmap(size))
    return icon_obj
