"""自定义控件样式：为 QRadioButton/QCheckBox 选中状态绘制蓝色背景 + 白色打勾。

QSS 的 image 属性在 ::indicator 上渲染不稳定，
改用 QProxyStyle 直接控制 QPainter 绘制，确保打勾可见。
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle


class CheckIndicatorStyle(QProxyStyle):
    """在暗色主题下自定义 QRadioButton/QCheckBox 指示器。"""

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_IndicatorRadioButton:
            self._draw_indicator(option, painter)
            return
        if element == QStyle.PE_IndicatorCheckBox:
            self._draw_indicator(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    @staticmethod
    def _draw_indicator(option, painter):
        """绘制指示器：未选中=暗色边框，选中=蓝色背景+白色打勾。"""
        rect = QRectF(option.rect)
        if rect.width() < 2:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        is_on = bool(option.state & QStyle.State_On)
        is_hover = bool(option.state & QStyle.State_MouseOver)
        is_disabled = not bool(option.state & QStyle.State_Enabled)

        r = rect.adjusted(0.5, 0.5, -0.5, -0.5)

        if is_on:
            # 选中：蓝色背景
            color = QColor("#0567C0") if is_hover else QColor("#0455A4")
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 1))
        elif is_disabled:
            painter.setBrush(QBrush(QColor("#2D2D2D")))
            painter.setPen(QPen(QColor("#444444"), 1))
        else:
            border = QColor("#0455A4") if is_hover else QColor("#555555")
            painter.setBrush(QBrush(QColor("#2D2D2D")))
            painter.setPen(QPen(border, 1))

        painter.drawRoundedRect(r, 3.0, 3.0)

        if is_on:
            # 白色打勾
            pen = QPen(QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)

            cx = r.center().x()
            cy = r.center().y()
            w = r.width()
            # 打勾三个点：左下 -> 中下 -> 右上
            p1 = QPointF(cx - w * 0.28, cy + w * 0.02)
            p2 = QPointF(cx - w * 0.05, cy + w * 0.25)
            p3 = QPointF(cx + w * 0.30, cy - w * 0.20)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)

        painter.restore()
