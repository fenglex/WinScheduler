"""图标生成：使用 QPainter 程序化绘制矢量图标，无需外部资源文件。

设计原则：
- 统一 24×24 像素，使用矢量路径绘制保证跨平台一致。
- 优先用「色块 + 几何符号」组合，强化识别度（纯线条图标在暗色背景下易糊）。
- 颜色按功能区分：绿色 = 新建/运行，红色 = 删除/停止，蓝色 = 编辑/设置，灰色 = 刷新。
"""

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)


# ── 应用主图标（保持原有风格：蓝底白色时钟）────────────

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
    p.drawLine(QPointF(cx, cy), QPointF(cx, cy - r * 0.7))   # 分针
    p.drawLine(QPointF(cx, cy), QPointF(cx + r * 0.5, cy - r * 0.35))  # 时针

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
    """获取系统托盘图标（32×32 更适合托盘）。"""
    return QIcon(_make_pixmap(32))


# ── 工具栏图标（统一线条 + 色块风格）─────────────────────

_ICON_SIZE = 24


def _begin_icon(size: int = _ICON_SIZE) -> tuple[QPixmap, QPainter, float, float, float]:
    """创建透明画布并返回 (pixmap, painter, cx, cy, side)。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    return pm, p, size / 2, size / 2, float(size)


def _stroke_pen(color: str, width: float) -> QPen:
    """构造统一的描边笔：圆头、圆角。"""
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def icon_add() -> QIcon:
    """新建：绿色圆底白色 + 号。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setBrush(QBrush(QColor("#2D8C3C")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), s * 0.45, s * 0.45)
    p.setPen(_stroke_pen("#FFFFFF", s * 0.1))
    r = s * 0.18
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
    p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
    p.end()
    return QIcon(pm)


def icon_edit() -> QIcon:
    """编辑：蓝色铅笔。"""
    pm, p, cx, cy, s = _begin_icon()
    color = QColor("#0455A4")
    p.setPen(_stroke_pen("#0455A4", s * 0.09))
    p.setBrush(QBrush(color))

    # 铅笔笔身（倾斜矩形 + 笔尖三角）
    path = QPainterPath()
    # 笔身四点（左下 → 左上 → 右上 → 右下）
    path.moveTo(cx - s * 0.32, cy + s * 0.32)
    path.lineTo(cx - s * 0.18, cy + s * 0.18)
    path.lineTo(cx + s * 0.22, cy - s * 0.22)
    path.lineTo(cx + s * 0.32, cy - s * 0.08)
    path.lineTo(cx + s * 0.18, cy + s * 0.06)
    path.lineTo(cx - s * 0.08, cy + s * 0.32)
    path.closeSubpath()
    p.drawPath(path)

    # 笔尖（深色三角）
    p.setBrush(QBrush(QColor("#1E1E1E")))
    p.setPen(Qt.NoPen)
    tip = QPainterPath()
    tip.moveTo(cx + s * 0.22, cy - s * 0.22)
    tip.lineTo(cx + s * 0.42, cy - s * 0.42)
    tip.lineTo(cx + s * 0.32, cy - s * 0.08)
    tip.closeSubpath()
    p.drawPath(tip)
    p.end()
    return QIcon(pm)


def icon_delete() -> QIcon:
    """删除：红色垃圾桶。"""
    pm, p, cx, cy, s = _begin_icon()
    color = QColor("#C0392B")
    p.setPen(_stroke_pen("#C0392B", s * 0.08))
    p.setBrush(QBrush(QColor(192, 57, 43, 50)))

    # 桶身梯形
    p.drawPolygon([
        QPointF(cx - s * 0.28, cy - s * 0.08),
        QPointF(cx - s * 0.2,  cy + s * 0.32),
        QPointF(cx + s * 0.2,  cy + s * 0.32),
        QPointF(cx + s * 0.28, cy - s * 0.08),
    ])

    # 顶部提手
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(cx - s * 0.38, cy - s * 0.12),
               QPointF(cx + s * 0.38, cy - s * 0.12))
    p.drawLine(QPointF(cx - s * 0.12, cy - s * 0.12),
               QPointF(cx - s * 0.12, cy - s * 0.26))
    p.drawLine(QPointF(cx + s * 0.12, cy - s * 0.12),
               QPointF(cx + s * 0.12, cy - s * 0.26))
    p.drawLine(QPointF(cx - s * 0.12, cy - s * 0.26),
               QPointF(cx + s * 0.12, cy - s * 0.26))

    # 桶身内两条竖线（细节）
    p.drawLine(QPointF(cx - s * 0.08, cy + s * 0.02),
               QPointF(cx - s * 0.05, cy + s * 0.22))
    p.drawLine(QPointF(cx + s * 0.08, cy + s * 0.02),
               QPointF(cx + s * 0.05, cy + s * 0.22))
    p.end()
    return QIcon(pm)


def icon_run() -> QIcon:
    """运行：绿色圆底白色三角形。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setBrush(QBrush(QColor("#2D8C3C")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), s * 0.45, s * 0.45)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    path = QPainterPath()
    path.moveTo(cx - s * 0.13, cy - s * 0.2)
    path.lineTo(cx + s * 0.2,  cy)
    path.lineTo(cx - s * 0.13, cy + s * 0.2)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_stop() -> QIcon:
    """停止：红色圆底白色方形。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setBrush(QBrush(QColor("#C0392B")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(cx, cy), s * 0.45, s * 0.45)
    p.setBrush(QBrush(QColor("#FFFFFF")))
    r = s * 0.16
    p.drawRect(QRectF(cx - r, cy - r, r * 2, r * 2))
    p.end()
    return QIcon(pm)


def icon_refresh() -> QIcon:
    """刷新：灰色循环箭头。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setPen(_stroke_pen("#3C3C3C", s * 0.1))
    p.setBrush(Qt.NoBrush)

    # 3/4 圆弧
    r = s * 0.3
    rect = QRectF(cx - r, cy - r, r * 2, r * 2)
    p.drawArc(rect, 30 * 16, 300 * 16)

    # 箭头三角
    p.setBrush(QBrush(QColor("#3C3C3C")))
    p.setPen(Qt.NoPen)
    arrow = QPainterPath()
    arrow.moveTo(cx + s * 0.34, cy - s * 0.04)
    arrow.lineTo(cx + s * 0.14, cy - s * 0.3)
    arrow.lineTo(cx + s * 0.08, cy - s * 0.05)
    arrow.closeSubpath()
    p.drawPath(arrow)
    p.end()
    return QIcon(pm)


def icon_settings() -> QIcon:
    """设置：深灰齿轮。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setBrush(QBrush(QColor("#3C3C3C")))
    p.setPen(Qt.NoPen)

    # 8 齿齿轮（外圈凹凸交替）
    teeth = 8
    inner = s * 0.2
    outer = s * 0.4
    path = QPainterPath()
    for i in range(teeth * 2):
        r = outer if i % 2 == 0 else inner
        a = i * pi / teeth - pi / 2  # 起始角度置于正上方
        x = cx + r * cos(a)
        y = cy + r * sin(a)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)

    # 中心镂空圆
    p.setBrush(QBrush(QColor("#1E1E1E")))
    p.drawEllipse(QPointF(cx, cy), s * 0.1, s * 0.1)
    p.end()
    return QIcon(pm)


def icon_toggle() -> QIcon:
    """启用/禁用：电源开关（带 / 不带开角的圆弧 + 竖线）。"""
    pm, p, cx, cy, s = _begin_icon()
    p.setPen(_stroke_pen("#0455A4", s * 0.1))
    p.setBrush(Qt.NoBrush)

    # 顶部 3/4 圆弧（开口朝下）
    r = s * 0.3
    rect = QRectF(cx - r, cy - s * 0.05, r * 2, r * 2 + s * 0.05)
    p.drawArc(rect, 40 * 16, 280 * 16)

    # 竖线
    p.drawLine(QPointF(cx, cy + s * 0.05), QPointF(cx, cy - s * 0.22))
    p.end()
    return QIcon(pm)
