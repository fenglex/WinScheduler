"""表格行选中样式：整行高亮 + 左侧强调条（QStyledItemDelegate）。

问题背景：
  - QSS 的 selection-background-color (#0455A4) 在暗色主题下行背景
    (#1E1E1E/#232323) 上对比度不足，选中行不明显；
  - 窗口失焦时 Qt 淡化选中色，几乎不可见。

解决：代理自绘选中态，不依赖焦点状态：
  - 整行填充高亮蓝（比 QSS 版更亮），悬停时再提亮
  - 首列左侧 3px 浅蓝强调条（类似 VS Code 选中行）
  - 选中文字白色 + 加粗
"""

from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

SEL_BG = QColor("#0E6CC0")        # 选中行背景
SEL_BG_HOVER = QColor("#1583DE")  # 选中且悬停时的更亮背景
ACCENT = QColor("#5AB0F2")        # 左侧强调条颜色
SEL_TEXT = QColor("#FFFFFF")      # 选中行文字颜色
ACCENT_WIDTH = 3                  # 强调条宽度（px）


class RowSelectionDelegate(QStyledItemDelegate):
    """绘制明显的整行选中效果（任务列表与历史记录表格共用）。"""

    def paint(self, painter: QPainter, option, index):
        if not (option.state & QStyle.State_Selected):
            super().paint(painter, option, index)
            return

        # 1) 自绘选中背景：整行色块 + 首列左侧强调条
        painter.save()
        bg = SEL_BG_HOVER if (option.state & QStyle.State_MouseOver) else SEL_BG
        painter.fillRect(option.rect, bg)
        if index.column() == 0:
            r = option.rect
            painter.fillRect(r.x(), r.y(), ACCENT_WIDTH, r.height(), ACCENT)
        painter.restore()

        # 2) 交给默认绘制文字，但清除 Selected/Hot 状态避免 QSS 再画
        #    自己的选中背景/悬停背景覆盖我们的色块；
        #    同时改写画笔为白色加粗，增强可读性。
        opt = QStyleOptionViewItem(option)
        opt.state = opt.state & ~QStyle.State_Selected
        opt.state = opt.state & ~QStyle.State_MouseOver
        opt.font.setBold(True)
        opt.palette.setColor(QPalette.Text, SEL_TEXT)
        opt.palette.setColor(QPalette.WindowText, SEL_TEXT)
        super().paint(painter, opt, index)
