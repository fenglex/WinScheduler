"""系统托盘图标：右键菜单，最小化到托盘。"""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ui.icons import get_tray_icon


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标。

    - 双击托盘 → 显示主窗口
    - 右键菜单 → 显示主窗口 / 暂停调度 / 退出
    """

    def __init__(self, main_window, scheduler_manager):
        super().__init__()
        self.main_window = main_window
        self.scheduler = scheduler_manager

        self.setIcon(get_tray_icon())
        self.setToolTip("任务调度器")
        self._build_menu()

        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        self.show_action = QAction("显示主窗口", menu)
        self.show_action.triggered.connect(self._show_window)
        menu.addAction(self.show_action)

        menu.addSeparator()

        self.pause_action = QAction("暂停调度", menu)
        self.pause_action.triggered.connect(self._toggle_pause)
        menu.addAction(self.pause_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        """双击托盘图标显示主窗口。"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _toggle_pause(self):
        if self.scheduler.running:
            self.scheduler.pause_all()
            self.pause_action.setText("恢复调度")
            self.showMessage("任务调度器", "调度已暂停", QSystemTrayIcon.Information, 2000)
        else:
            self.scheduler.resume_all()
            self.pause_action.setText("暂停调度")
            self.showMessage("任务调度器", "调度已恢复", QSystemTrayIcon.Information, 2000)

    def _quit(self):
        """退出程序。"""
        self.main_window.quit_app()

    def update_pause_label(self):
        """更新暂停/恢复菜单文本。"""
        if self.scheduler.running:
            self.pause_action.setText("暂停调度")
        else:
            self.pause_action.setText("恢复调度")
