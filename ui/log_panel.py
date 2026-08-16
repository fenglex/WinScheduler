"""日志面板：实时日志 + 历史记录查询，支持搜索/过滤/着色。"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from config import LOG_COLORS, STATUS_LABELS


class RealtimeLogWidget(QPlainTextEdit):
    """实时日志显示区：深色背景、按级别着色、自动滚动。"""

    MAX_LINES = 5000  # 防止无限追加导致内存膨胀

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)
        self._auto_scroll = True
        self._filter_text = ""

    def set_auto_scroll(self, auto: bool):
        self._auto_scroll = auto

    def set_filter(self, text: str):
        self._filter_text = text.lower().strip()

    def append_log(self, task_id: int, task_name: str, level: str, formatted_line: str):
        """追加一行日志（带颜色）。

        通过 Signal 连接调用，始终在主线程执行。
        """
        # 过滤
        if self._filter_text:
            if self._filter_text not in formatted_line.lower():
                return

        color = LOG_COLORS.get(level, LOG_COLORS["INFO"])
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(formatted_line + "\n", fmt)

        if self._auto_scroll:
            self.scrollToBottom()

    def scrollToBottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


class HistoryLogWidget(QWidget):
    """历史日志查询面板。"""

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self._task_sig: str | None = None  # 上次同步的任务列表签名
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ── 筛选栏 ────────────────────────────────────────
        filter_bar = QHBoxLayout()

        filter_bar.addWidget(QLabel("任务:"))
        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(160)
        self.task_combo.currentIndexChanged.connect(self.refresh)
        filter_bar.addWidget(self.task_combo)

        filter_bar.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", "")
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, key)
        self.status_combo.currentIndexChanged.connect(self.refresh)
        filter_bar.addWidget(self.status_combo)

        filter_bar.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filter_bar.addWidget(refresh_btn)

        clear_btn = QPushButton("清空筛选")
        clear_btn.clicked.connect(self._clear_filter)
        filter_bar.addWidget(clear_btn)

        layout.addLayout(filter_bar)

        # ── 分割：表格 + 详情 ────────────────────────────
        splitter = QSplitter(Qt.Vertical)

        # 历史记录表格
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["任务ID", "开始时间", "结束时间", "状态", "退出码", "耗时(s)"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.table)

        # 日志详情
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("选择上方记录查看详细日志...")
        splitter.addWidget(self.detail)

        splitter.setSizes([300, 200])
        layout.addWidget(splitter)
        self._current_logs: list[dict] = []

    def update_task_list(self, tasks: list[dict]):
        """更新任务下拉框（列表无变化时跳过，避免每 5 秒重建打断用户操作）。"""
        sig = ";".join(f"{t['id']}:{t['name']}" for t in tasks)
        if sig == self._task_sig:
            return
        self._task_sig = sig
        current_id = self.task_combo.currentData()
        self.task_combo.clear()
        self.task_combo.addItem("全部", None)
        for t in tasks:
            self.task_combo.addItem(f"[{t['id']}] {t['name']}", t["id"])
        if current_id is not None:
            idx = self.task_combo.findData(current_id)
            if idx >= 0:
                self.task_combo.setCurrentIndex(idx)

    def refresh(self):
        """刷新历史记录表格。"""
        task_id = self.task_combo.currentData()
        status = self.status_combo.currentData()

        logs = self.db.get_run_logs(
            task_id=task_id if task_id else None,
            status=status if status else None,
            limit=500,
        )
        self._current_logs = logs

        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            values = [
                str(log["task_id"]),
                log["started_at"].strftime("%Y-%m-%d %H:%M:%S") if log["started_at"] else "",
                log["finished_at"].strftime("%Y-%m-%d %H:%M:%S") if log["finished_at"] else "",
                STATUS_LABELS.get(log["status"], log["status"]),
                str(log["exit_code"]) if log["exit_code"] is not None else "",
                f"{log['duration']:.1f}" if log["duration"] is not None else "",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col == 3:  # 状态列着色
                    status_val = log["status"]
                    if status_val == "success":
                        item.setForeground(QColor(LOG_COLORS["SUCCESS"]))
                    elif status_val in ("failed", "timeout", "killed"):
                        item.setForeground(QColor(LOG_COLORS["ERROR"]))
                    elif status_val == "running":
                        item.setForeground(QColor(LOG_COLORS["WARN"]))
                self.table.setItem(row, col, item)

    def _on_select(self):
        """选中一行，显示详细日志。"""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._current_logs):
            self.detail.setPlainText(self._current_logs[row]["log_content"])

    def _clear_filter(self):
        self.task_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)


class LogPanel(QTabWidget):
    """日志面板：实时日志 + 历史记录，带搜索栏。"""

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager

        # ── 实时日志 Tab ──────────────────────────────────
        realtime_widget = QWidget()
        rt_layout = QVBoxLayout(realtime_widget)
        rt_layout.setContentsMargins(0, 0, 0, 0)
        rt_layout.setSpacing(2)

        # 搜索/控制栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词过滤实时日志...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_edit)

        self.autoscroll_check = QCheckBox("自动滚动")
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.toggled.connect(self._on_autoscroll_toggled)
        toolbar.addWidget(self.autoscroll_check)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.realtime.clear())
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        rt_layout.addLayout(toolbar)

        self.realtime = RealtimeLogWidget()
        rt_layout.addWidget(self.realtime)

        self.addTab(realtime_widget, "实时日志")

        # ── 历史记录 Tab ──────────────────────────────────
        self.history = HistoryLogWidget(db_manager)
        self.addTab(self.history, "历史记录")

    def append_log(self, task_id: int, task_name: str, level: str, formatted_line: str):
        """接收实时日志信号。"""
        self.realtime.append_log(task_id, task_name, level, formatted_line)

    def update_task_list(self, tasks: list[dict]):
        """任务列表变更时同步到历史面板的下拉框。"""
        self.history.update_task_list(tasks)

    def refresh_history(self):
        """刷新历史记录（任务运行结束后调用）。"""
        self.history.refresh()

    def _on_search_changed(self, text: str):
        self.realtime.set_filter(text)

    def _on_autoscroll_toggled(self, checked: bool):
        self.realtime.set_auto_scroll(checked)
