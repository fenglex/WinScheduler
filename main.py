"""任务调度器 — 程序入口。

启动流程：
  1. 解析命令行参数（--minimized）
  2. 单实例检查
  3. 初始化数据库
  4. 创建核心服务（Executor / Scheduler）和 UI
  5. 连接信号 → 启动调度器 → 显示窗口或最小化到托盘
  6. 运行事件循环
"""

import argparse
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, APP_VERSION, DARK_THEME_QSS, ensure_data_dir
from core.scheduler_manager import SchedulerManager
from core.task_executor import TaskExecutor
from database.manager import DatabaseManager
from system.autostart import AutoStart
from system.single_instance import SingleInstance
from ui.icons import get_app_icon
from ui.main_window import MainWindow
from ui.tray_icon import TrayIcon


def main():
    parser = argparse.ArgumentParser(description="Windows 定时任务调度系统")
    parser.add_argument("--minimized", action="store_true",
                        help="启动后最小化到系统托盘")
    args = parser.parse_args()

    # ── 单实例检查 ──────────────────────────────────────
    singleton = SingleInstance()
    if not singleton.acquire():
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.warning(None, APP_NAME,
                            "程序已在运行，请检查系统托盘。")
        return

    # ── 创建 QApplication ───────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("任务调度器")
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(get_app_icon())
    app.setStyleSheet(DARK_THEME_QSS)

    # 防止最后一个窗口关闭时自动退出（我们需要最小化到托盘）
    app.setQuitOnLastWindowClosed(False)

    # ── 初始化数据库 ────────────────────────────────────
    ensure_data_dir()
    db = DatabaseManager()
    db.init_db()

    # ── 创建核心服务 ────────────────────────────────────
    executor = TaskExecutor(db)
    scheduler = SchedulerManager(db, executor)

    # ── 创建 UI ─────────────────────────────────────────
    window = MainWindow(db, scheduler, executor)
    tray = TrayIcon(window, scheduler)
    window.tray = tray

    # ── 连接信号 ────────────────────────────────────────
    executor.log_line.connect(window.log_panel.append_log)

    # ── 启动调度器 ──────────────────────────────────────
    scheduler.start()
    window.refresh()

    # ── 显示窗口或最小化 ────────────────────────────────
    tray.show()
    if args.minimized:
        # 不显示主窗口，仅显示托盘
        pass
    else:
        window.show()

    # ── 运行事件循环 ────────────────────────────────────
    exit_code = app.exec()

    # ── 清理 ────────────────────────────────────────────
    executor.stop_all(timeout=3)
    scheduler.shutdown(wait=False)
    singleton.release()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
