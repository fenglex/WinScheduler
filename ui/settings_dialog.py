"""设置对话框：开机自启、主题、日志保留天数等。"""

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QMessageBox, QSpinBox, QVBoxLayout,
)

from system.autostart import AutoStart


class SettingsDialog(QDialog):
    """设置对话框。"""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("设置")
        self.setMinimumWidth(420)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ── 启动设置 ──────────────────────────────────────
        startup_group = QGroupBox("启动")
        startup_layout = QVBoxLayout(startup_group)

        self.autostart_check = QCheckBox("开机自动启动")
        startup_layout.addWidget(self.autostart_check)

        self.minimize_check = QCheckBox("关闭窗口时最小化到系统托盘")
        startup_layout.addWidget(self.minimize_check)

        layout.addWidget(startup_group)

        # ── 日志设置 ──────────────────────────────────────
        log_group = QGroupBox("日志")
        log_form = QFormLayout(log_group)

        self.retention_spin = QSpinBox()
        self.retention_spin.setRange(1, 3650)
        self.retention_spin.setSuffix(" 天")
        log_form.addRow("日志保留天数", self.retention_spin)

        hint = QLabel("超过保留天数的运行日志将被自动清理")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        log_form.addRow("", hint)

        layout.addWidget(log_group)

        # ── 按钮 ──────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        """从数据库加载当前设置。"""
        self.autostart_check.setChecked(self.db.get_config("autostart", False))
        self.minimize_check.setChecked(self.db.get_config("minimize_to_tray", True))
        self.retention_spin.setValue(self.db.get_config("log_retention_days", 30))

    def _save_and_accept(self):
        """保存设置。"""
        autostart = self.autostart_check.isChecked()

        # 处理注册表自启
        try:
            if autostart:
                AutoStart.enable()
            else:
                AutoStart.disable()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"设置开机自启失败：{e}\n配置仍会保存。")

        self.db.set_config("autostart", autostart)
        self.db.set_config("minimize_to_tray", self.minimize_check.isChecked())
        self.db.set_config("log_retention_days", self.retention_spin.value())

        # 清理旧日志
        self.db.cleanup_old_logs(self.retention_spin.value())

        self.accept()
