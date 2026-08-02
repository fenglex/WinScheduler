"""图标生成：使用 QPainter 程序化绘制图标，无需外部 .ico 文件。"""

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import QStyle, QStyleFactory


def _make_pixmap(size: int = 64) -> QPixmap:
    """绘制应用主图标：蓝底白色时钟。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # 背景圆角方块
    rect = QRectF(2, 2, size - 4, size - 4)
    p.setBrush(QBrush(QColor("#0455A4")))
    p.setPen(QPen(QColor("#034B8A"), 1))
    p.drawRoundedRect(rect, size * 0.18, size * 0.18)

    # 时钟外圆
    cx, cy = size / 2, size / 2
    r = size * 0.32
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#FFFFFF"), max(1.5, size * 0.035)))
    p.drawEllipse(QPointF(cx, cy), r, r)

    # 时针和分针
    p.setPen(QPen(QColor("#FFFFFF"), max(1.5, size * 0.04), Qt.SolidLine, Qt.RoundCap))
    # 分针（指向上方）
    p.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.7))
    # 时针（指向右上方）
    p.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.5, cy - r * 0.35))

    # 中心点
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), size * 0.035, size * 0.035)

    p.end()
    return pm


def get_app_icon() -> QIcon:
    """获取应用图标。"""
    return QIcon(_make_pixmap(64))


def get_tray_icon() -> QIcon:
    """获取系统托盘图标（32x32 更适合托盘）。"""
    return QIcon(_make_pixmap(32))


# ── 通用风格化图标（用标准像素图模拟图标集）──────────────

def _text_icon(text: str, bg: str, fg: str = "#FFFFFF", size: int = 24) -> QIcon:
    """用单字/emoji 文本生成简单图标。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(0, 0, size, size)
    p.setBrush(QBrush(QColor(bg)))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(rect, 4, 4)
    p.setPen(QPen(QColor(fg)))
    font = QFont()
    font.setPixelSize(int(size * 0.6))
    font.setBold(True)
    p.setFont(font)
    p.drawText(rect, Qt.AlignCenter, text)
    p.end()
    return QIcon(pm)


def icon_add() -> QIcon:
    return _text_icon("＋", "#2D8C3C")


def icon_edit() -> QIcon:
    return _text_icon("✎", "#0455A4")


def icon_delete() -> QIcon:
    return _text_icon("✕", "#C0392B")


def icon_run() -> QIcon:
    return _text_icon("▶", "#2D8C3C")


def icon_stop() -> QIcon:
    return _text_icon("■", "#C0392B")


def icon_refresh() -> QIcon:
    return _text_icon("↻", "#555555")


def icon_settings() -> QIcon:
    return _text_icon("⚙", "#555555")
