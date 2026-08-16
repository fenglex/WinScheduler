"""主窗口：任务列表表格、工具栏、菜单栏、状态栏。

整合 SchedulerManager / TaskExecutor / LogPanel / TrayIcon。
"""

from datetime import datetime

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMenu,
    QMessageBox, QSplitter, QStackedWidget, QSystemTrayIcon, QTableWidget,
    QTableWidgetItem, QToolBar, QVBoxLayout, QWidget,
)

from config import STATUS_LABELS, TRIGGER_LABELS


class NumericTableItem(QTableWidgetItem):
    """按数值排序的表格项（用于 ID 列，避免 1, 10, 2 的字典序问题）。"""

    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except (ValueError, TypeError):
            return super().__lt__(other)

from core.log_collector import LogCollector
from core.scheduler_manager import SchedulerManager
from core.task_executor import TaskExecutor
from database.manager import DatabaseManager
from ui.icons import (
    icon_add, icon_delete, icon_edit, icon_refresh, icon_run,
    icon_settings, icon_stop, icon_toggle,
)
from ui.log_panel import LogPanel
from ui.settings_dialog import SettingsDialog
from ui.task_edit_dialog import TaskEditDialog


class MainWindow(QMainWindow):
    """主窗口。"""

    def __init__(self, db: DatabaseManager, scheduler: SchedulerManager,
                 executor: TaskExecutor, tray=None):
        super().__init__()
        self.db = db
        self.scheduler = scheduler
        self.executor = executor
        self.tray = tray

        self.setWindowTitle("任务调度器")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        self._running_tasks: set[int] = set()
        self._recently_finished: bool = False

        self._init_ui()
        self._connect_signals()
        self._init_timers()
        self.refresh_tasks()

    # ── 初始化 ────────────────────────────────────────────

    def _init_ui(self):
        # ── 菜单栏 ────────────────────────────────────────
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        act_settings = QAction("设置...", self)
        act_settings.triggered.connect(self._open_settings)
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_app)
        file_menu.addAction(act_quit)

        task_menu = menubar.addMenu("任务(&T)")
        act_new = QAction("新建任务", self)
        act_new.triggered.connect(self._new_task)
        task_menu.addAction(act_new)
        act_edit = QAction("编辑任务", self)
        act_edit.triggered.connect(self._edit_task)
        task_menu.addAction(act_edit)
        act_delete = QAction("删除任务", self)
        act_delete.triggered.connect(self._delete_task)
        task_menu.addAction(act_delete)

        help_menu = menubar.addMenu("帮助(&H)")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        # ── 工具栏 ────────────────────────────────────────
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        # 图标 + 文字 横向排列，确保一眼看出功能
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 统一图标尺寸，避免大图标挤掉文字
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # 第一组：任务管理（新建 / 编辑 / 删除）
        self.tb_new = toolbar.addAction(icon_add(), "新建任务")
        self.tb_new.setToolTip("新建一个调度任务 (Ctrl+N)")
        self.tb_new.setShortcut("Ctrl+N")
        self.tb_new.triggered.connect(self._new_task)

        self.tb_edit = toolbar.addAction(icon_edit(), "编辑任务")
        self.tb_edit.setToolTip("编辑选中的任务")
        self.tb_edit.triggered.connect(self._edit_task)

        self.tb_delete = toolbar.addAction(icon_delete(), "删除任务")
        self.tb_delete.setToolTip("删除选中的任务及其历史日志")
        self.tb_delete.triggered.connect(self._delete_task)

        toolbar.addSeparator()

        # 第二组：执行控制（运行 / 停止 / 启停切换）
        self.tb_run = toolbar.addAction(icon_run(), "立即运行")
        self.tb_run.setToolTip("立即手动触发选中的任务")
        self.tb_run.triggered.connect(self._run_selected)

        self.tb_stop = toolbar.addAction(icon_stop(), "停止")
        self.tb_stop.setToolTip("终止正在运行的选中任务")
        self.tb_stop.triggered.connect(self._stop_selected)

        self.tb_enable = toolbar.addAction(icon_toggle(), "启用/禁用")
        self.tb_enable.setToolTip("切换选中任务的启用状态")
        self.tb_enable.triggered.connect(self._toggle_enabled)

        toolbar.addSeparator()

        # 第三组：通用（刷新 / 设置）
        self.tb_refresh = toolbar.addAction(icon_refresh(), "刷新列表")
        self.tb_refresh.setToolTip("从数据库重新加载任务列表")
        self.tb_refresh.triggered.connect(self.refresh_tasks)

        self.tb_settings = toolbar.addAction(icon_settings(), "设置")
        self.tb_settings.setToolTip("打开设置（自启、托盘、日志保留等）")
        self.tb_settings.triggered.connect(self._open_settings)

        # ── 中央布局 ──────────────────────────────────────
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Vertical)

        # 任务表格
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "任务名称", "触发方式", "调度表达式", "状态", "上次运行", "下次运行"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        # 任务名称列自适应
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # 其余列固定宽度（按功能预留足够空间）
        self.table.setColumnWidth(0, 50)   # ID
        self.table.setColumnWidth(2, 100)  # 触发方式
        self.table.setColumnWidth(3, 180)  # 调度表达式
        self.table.setColumnWidth(4, 80)   # 状态
        self.table.setColumnWidth(5, 150)  # 上次运行
        self.table.setColumnWidth(6, 150)  # 下次运行
        # 行高更舒展
        self.table.verticalHeader().setDefaultSectionSize(32)
        # 表头可点击排序（视觉提示）
        self.table.setSortingEnabled(True)

        self.table.doubleClicked.connect(self._edit_task)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # 空表占位：用 StackedWidget 在表格上方叠加居中提示
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.table)

        self.empty_placeholder = QLabel(
            "📭  暂无任务\n\n点击工具栏「新建任务」创建第一个定时任务"
        )
        self.empty_placeholder.setAlignment(Qt.AlignCenter)
        self.empty_placeholder.setStyleSheet(
            "color: #888888; font-size: 14px; line-height: 1.6;"
        )
        self.table_stack.addWidget(self.empty_placeholder)
        splitter.addWidget(self.table_stack)

        # 日志面板
        self.log_panel = LogPanel(self.db)
        splitter.addWidget(self.log_panel)

        splitter.setSizes([300, 250])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
        self.setCentralWidget(central)

        # ── 状态栏 ────────────────────────────────────────
        # 左侧：主状态（调度器运行/暂停）
        self.status_label = self._make_status_label("● 调度器启动中...", name="main")
        self.statusBar().addWidget(self.status_label, 1)

        # 右侧永久区：任务统计、运行中、自启
        self.lbl_task_count = self._make_status_label("任务: 0", name="metric")
        self.lbl_running = self._make_status_label("运行中: 0", name="metric")
        self.lbl_autostart = self._make_status_label("自启: 未知", name="metric")
        self.statusBar().addPermanentWidget(self.lbl_task_count)
        self.statusBar().addPermanentWidget(self.lbl_running)
        self.statusBar().addPermanentWidget(self.lbl_autostart)

    @staticmethod
    def _make_status_label(text: str, name: str = "") -> QLabel:
        """构造状态栏标签：name 用于 QSS 区分主状态 / 指标。"""
        lbl = QLabel(text)
        if name:
            lbl.setObjectName(f"status_{name}")
        lbl.setTextFormat(Qt.PlainText)
        return lbl

    def _connect_signals(self):
        self.executor.task_started.connect(self._on_task_started)
        self.executor.task_finished.connect(self._on_task_finished)

    def _init_timers(self):
        """定时刷新 UI。"""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._periodic_refresh)
        self._refresh_timer.start(5000)  # 每 5 秒刷新一次

    # ── 任务列表 ──────────────────────────────────────────

    def refresh_tasks(self):
        """刷新任务列表表格。"""
        tasks = self.db.get_all_tasks()
        self.log_panel.update_task_list(tasks)

        # 空表/有表切换：占位提示 vs 实际表格
        if tasks:
            self.table_stack.setCurrentWidget(self.table)
        else:
            self.table_stack.setCurrentWidget(self.empty_placeholder)

        # 填充期间必须禁用排序：否则逐行 setItem 会触发实时重排，
        # 导致行内容错乱（Qt 推荐做法）
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(tasks))

        for row, t in enumerate(tasks):
            trigger_label = TRIGGER_LABELS.get(t["trigger_type"], t["trigger_type"])
            schedule_text = SchedulerManager.describe_trigger(
                t["trigger_type"], t.get("trigger_config", "{}")
            )

            # 状态文本
            task_id = t["id"]
            if task_id in self._running_tasks:
                status_text = STATUS_LABELS.get("running", "运行中")
                status_color = "#FAC775"
            elif not t["enabled"]:
                status_text = "已禁用"
                status_color = "#777777"
            elif t.get("last_status") == "success":
                status_text = STATUS_LABELS.get("success", "成功")
                status_color = "#639922"
            elif t.get("last_status") in ("failed", "timeout", "killed"):
                status_text = STATUS_LABELS.get(t["last_status"], "失败")
                status_color = "#E24B4A"
            else:
                status_text = "空闲"
                status_color = "#B4B2A9"

            last_run = t.get("last_run_at")
            last_run_text = last_run.strftime("%Y-%m-%d %H:%M:%S") if last_run else "—"

            next_run = t.get("next_run_at")
            next_run_text = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "—"

            row_data = [
                str(t["id"]),
                t["name"],
                trigger_label,
                schedule_text,
                status_text,
                last_run_text,
                next_run_text,
            ]
            for col, val in enumerate(row_data):
                if col == 0:
                    item = NumericTableItem(val)
                else:
                    item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, t["id"])
                # 居中对齐：ID / 触发方式 / 状态
                if col in (0, 2, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    item.setForeground(QColor(status_color))
                # 时间列使用等宽字体，避免时间宽度变化导致抖动
                if col in (5, 6):
                    f = item.font()
                    f.setFamily("Cascadia Code")
                    f.setStyleHint(QFont.Monospace)
                    item.setFont(f)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)
        self._update_status_bar(len(tasks))

    def _update_status_bar(self, task_count: int):
        """更新状态栏。"""
        running_count = self.executor.get_running_count()
        enabled_count = len([t for t in self.db.get_all_tasks() if t["enabled"]])

        if self.scheduler.running:
            scheduler_text = "● 调度器运行中"
        else:
            scheduler_text = "○ 调度器已暂停"

        self.status_label.setText(scheduler_text)
        self.lbl_task_count.setText(f"任务: {task_count}个({enabled_count}启用)")
        self.lbl_running.setText(f"运行中: {running_count}")

        from system.autostart import AutoStart
        autostart_text = "自启: 已启用" if AutoStart.is_enabled() else "自启: 未启用"
        self.lbl_autostart.setText(autostart_text)

    def _periodic_refresh(self):
        """定时刷新：同步 next_run_time，刷新表格和状态栏。"""
        try:
            self.scheduler.sync_next_run_times()
            self.refresh_tasks()
            if self._recently_finished:
                self.log_panel.refresh_history()
                self._recently_finished = False
        except Exception:
            pass  # 程序退出时可能出错，忽略

    # ── 任务操作 ──────────────────────────────────────────

    def _get_selected_task_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return item.data(Qt.UserRole) if item else None

    def _new_task(self):
        dialog = TaskEditDialog(self)
        if dialog.exec():
            data = dialog.get_task_data()
            task_id = self.db.create_task(data)
            self.scheduler.add_or_update(self.db.get_task(task_id))
            self.refresh_tasks()
            self._log_to_panel(f"已创建任务: {data['name']}")

    def _edit_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return
        task = self.db.get_task(task_id)
        if not task:
            return
        dialog = TaskEditDialog(self, task)
        if dialog.exec():
            data = dialog.get_task_data()
            self.db.update_task(task_id, data)
            self.scheduler.add_or_update(self.db.get_task(task_id))
            self.refresh_tasks()
            self._log_to_panel(f"已更新任务: {data['name']}")

    def _delete_task(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return
        task = self.db.get_task(task_id)
        name = task["name"] if task else str(task_id)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除任务「{name}」吗？\n该任务的历史日志也会被删除。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.scheduler.remove_job(task_id)
            self.db.delete_task(task_id)
            self.refresh_tasks()
            self._log_to_panel(f"已删除任务: {name}")

    def _run_selected(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return
        self.scheduler.run_now(task_id)

    def _stop_selected(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return
        if not self.executor.is_running(task_id):
            QMessageBox.information(self, "提示", "该任务当前未在运行")
            return
        self.executor.stop_task(task_id)

    def _toggle_enabled(self):
        task_id = self._get_selected_task_id()
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择一个任务")
            return
        task = self.db.get_task(task_id)
        if not task:
            return
        new_enabled = not task["enabled"]
        self.db.set_task_enabled(task_id, new_enabled)
        task["enabled"] = new_enabled
        self.scheduler.add_or_update(task)
        self.refresh_tasks()

    # ── 右键菜单 ──────────────────────────────────────────

    def _show_context_menu(self, pos):
        task_id = self._get_selected_task_id()
        if task_id is None:
            return

        menu = QMenu(self)

        if self.executor.is_running(task_id):
            act = menu.addAction("■ 停止")
            act.triggered.connect(self._stop_selected)
        else:
            act = menu.addAction("▶ 运行")
            act.triggered.connect(self._run_selected)

        menu.addSeparator()

        act_edit = menu.addAction("✎ 编辑")
        act_edit.triggered.connect(self._edit_task)

        task = self.db.get_task(task_id)
        if task:
            if task["enabled"]:
                act = menu.addAction("禁用")
            else:
                act = menu.addAction("启用")
            act.triggered.connect(self._toggle_enabled)

        menu.addSeparator()

        act_copy = menu.addAction("复制命令")
        act_copy.triggered.connect(lambda: self._copy_command(task_id))

        act_delete = menu.addAction("✕ 删除")
        act_delete.triggered.connect(self._delete_task)

        menu.addSeparator()

        act_log = menu.addAction("查看历史日志")
        act_log.triggered.connect(lambda: self._show_history(task_id))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_command(self, task_id: int):
        task = self.db.get_task(task_id)
        if task:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(task["command"])
            self._log_to_panel(f"已复制命令: {task['command']}")

    def _show_history(self, task_id: int):
        """切换到历史日志 Tab 并筛选该任务。"""
        self.log_panel.setCurrentIndex(1)
        combo = self.log_panel.history.task_combo
        idx = combo.findData(task_id)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        self.log_panel.refresh_history()

    # ── 信号处理 ──────────────────────────────────────────

    def _on_task_started(self, task_id: int, task_name: str):
        self._running_tasks.add(task_id)
        self.refresh_tasks()

    def _on_task_finished(self, task_id: int, exit_code: int,
                          status: str, duration: float):
        self._running_tasks.discard(task_id)
        self._recently_finished = True
        self.refresh_tasks()

    # ── 其他 ──────────────────────────────────────────────

    def _open_settings(self):
        dialog = SettingsDialog(self, self.db)
        dialog.exec()
        self.refresh_tasks()
        if self.tray:
            self.tray.update_pause_label()

    def _show_about(self):
        from config import APP_VERSION
        QMessageBox.about(
            self, "关于",
            f"<h3>任务调度器</h3>"
            f"<p>版本: {APP_VERSION}</p>"
            f"<p>Windows 定时任务调度系统</p>"
            f"<p>支持 Cron 表达式 / 固定间隔 / 一次性定时</p>"
        )

    def _log_to_panel(self, message: str):
        """向实时日志面板追加一条系统消息。"""
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = LogCollector.format_line(ts, "系统", "INFO", message)
        self.log_panel.append_log(0, "系统", "INFO", formatted)

    def refresh(self):
        """外部刷新入口。"""
        self.refresh_tasks()

    # ── 窗口事件 ──────────────────────────────────────────

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘（如果设置允许）。"""
        minimize_to_tray = self.db.get_config("minimize_to_tray", True)
        if minimize_to_tray:
            event.ignore()
            self.hide()
            if self.tray:
                self.tray.showMessage(
                    "任务调度器",
                    "程序已最小化到系统托盘，调度器继续运行",
                    QSystemTrayIcon.Information,
                    3000,
                )
        else:
            self.quit_app()
            event.accept()

    def quit_app(self):
        """退出程序（由托盘退出菜单调用）。"""
        self.executor.stop_all(timeout=3)
        self.scheduler.shutdown(wait=False)
        QApplication.quit()

    def show_window(self):
        """显示窗口（由托盘双击调用）。"""
        self.show()
        self.showNormal()
        self.activateWindow()
        self.raise_()
