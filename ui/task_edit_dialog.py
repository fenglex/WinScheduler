"""任务编辑对话框：表单输入任务参数，支持 cron/interval/date 配置。"""

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget,
)

from config import (
    COMMAND_LABELS, COMMAND_POWERSHELL, COMMAND_SHELL, COMMAND_TYPES,
    TRIGGER_CRON, TRIGGER_DATE, TRIGGER_INTERVAL, TRIGGER_LABELS,
)


class CronConfigWidget(QWidget):
    """Cron 触发器配置：标准 5 字段（分/时/日/月/周）。"""

    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        self.fields = {}
        defaults = {
            "minute": "*",
            "hour": "*",
            "day": "*",
            "month": "*",
            "day_of_week": "*",
        }
        labels = {
            "minute": "分钟",
            "hour": "小时",
            "day": "日",
            "month": "月",
            "day_of_week": "星期",
        }
        for key in ("minute", "hour", "day", "month", "day_of_week"):
            edit = QLineEdit(defaults[key])
            edit.setPlaceholderText("如 * / 0-59 / , / - (默认 *)")
            self.fields[key] = edit
            form.addRow(labels[key], edit)

        hint = QLabel(
            "提示：* = 任意值 | */5 = 每5 | 1,3,5 = 列举 | 1-5 = 范围\n"
            "星期: mon-sun 或 0-6 (0=周一)"
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow(hint)

    def get_config(self) -> dict:
        result = {}
        for key, edit in self.fields.items():
            val = edit.text().strip()
            if val and val != "*":
                result[key] = val
        return result or {"minute": "*"}

    def set_config(self, config: dict):
        for key, edit in self.fields.items():
            edit.setText(str(config.get(key, "*")))


class IntervalConfigWidget(QWidget):
    """Interval 触发器配置：天/时/分/秒。"""

    def __init__(self):
        super().__init__()
        form = QFormLayout(self)

        self.minutes = QSpinBox()
        self.minutes.setRange(0, 999999)
        self.minutes.setValue(10)

        self.seconds = QSpinBox()
        self.seconds.setRange(0, 59)

        self.hours = QSpinBox()
        self.hours.setRange(0, 999)

        self.days = QSpinBox()
        self.days.setRange(0, 365)

        form.addRow("天", self.days)
        form.addRow("小时", self.hours)
        form.addRow("分钟", self.minutes)
        form.addRow("秒", self.seconds)

    def get_config(self) -> dict:
        result = {}
        if self.days.value():
            result["days"] = self.days.value()
        if self.hours.value():
            result["hours"] = self.hours.value()
        if self.minutes.value():
            result["minutes"] = self.minutes.value()
        if self.seconds.value():
            result["seconds"] = self.seconds.value()
        return result or {"minutes": 10}

    def set_config(self, config: dict):
        self.days.setValue(config.get("days", 0))
        self.hours.setValue(config.get("hours", 0))
        self.minutes.setValue(config.get("minutes", 0))
        self.seconds.setValue(config.get("seconds", 0))


class DateConfigWidget(QWidget):
    """Date 一次性触发配置：日期时间选择。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.dt_edit = QDateTimeEdit()
        self.dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_edit.setCalendarPopup(True)
        self.dt_edit.setMinimumDateTime(
            self.dt_edit.dateTime()  # 默认当前时间
        )
        layout.addWidget(QLabel("运行时间:"))
        layout.addWidget(self.dt_edit)

    def get_config(self) -> dict:
        dt = self.dt_edit.dateTime().toPython()
        return {"run_date": dt.isoformat()}

    def set_config(self, config: dict):
        if "run_date" in config:
            from datetime import datetime
            dt = datetime.fromisoformat(config["run_date"])
            self.dt_edit.setDateTime(dt)


class TaskEditDialog(QDialog):
    """任务编辑/创建对话框。"""

    def __init__(self, parent=None, task: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("编辑任务" if task else "新建任务")
        self.setMinimumWidth(500)
        self._init_ui()
        if task:
            self._load_task(task)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────
        info_group = QGroupBox("基本信息")
        info_form = QFormLayout(info_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("必填，如：数据库备份")
        info_form.addRow("任务名称 *", self.name_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("可选描述")
        info_form.addRow("描述", self.desc_edit)

        # ── 执行方式 ──────────────────────────────────────
        self.command_type_combo = QComboBox()
        for ct in COMMAND_TYPES:
            self.command_type_combo.addItem(COMMAND_LABELS[ct], ct)
        self.command_type_combo.currentIndexChanged.connect(self._on_command_type_changed)
        info_form.addRow("执行方式", self.command_type_combo)

        # ── 执行命令（多行文本）──────────────────────────
        self.command_edit = QPlainTextEdit()
        self.command_edit.setPlaceholderText(
            "必填。可直接输入命令或多行脚本内容。\n"
            "Shell 模式: echo hello && dir\n"
            "PowerShell 模式: Write-Host 'Hello' ; Get-Process"
        )
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.command_edit.setFont(mono)
        self.command_edit.setMinimumHeight(120)
        self.command_edit.setMaximumHeight(200)
        info_form.addRow("执行命令 *", self.command_edit)

        # 工作目录 + 浏览按钮
        cwd_layout = QHBoxLayout()
        self.cwd_edit = QLineEdit()
        self.cwd_edit.setPlaceholderText("可选，留空则使用程序当前目录")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_dir)
        cwd_layout.addWidget(self.cwd_edit)
        cwd_layout.addWidget(browse_btn)
        info_form.addRow("工作目录", cwd_layout)

        layout.addWidget(info_group)

        # ── 触发配置 ──────────────────────────────────────
        trigger_group = QGroupBox("触发方式")
        trigger_layout = QVBoxLayout(trigger_group)

        # 单选按钮
        radio_layout = QHBoxLayout()
        self.radio_cron = QRadioButton(TRIGGER_LABELS[TRIGGER_CRON])
        self.radio_interval = QRadioButton(TRIGGER_LABELS[TRIGGER_INTERVAL])
        self.radio_date = QRadioButton(TRIGGER_LABELS[TRIGGER_DATE])
        self.radio_cron.setChecked(True)

        self.radios = {
            TRIGGER_CRON: self.radio_cron,
            TRIGGER_INTERVAL: self.radio_interval,
            TRIGGER_DATE: self.radio_date,
        }

        for radio in self.radios.values():
            radio.toggled.connect(self._on_trigger_changed)
            radio_layout.addWidget(radio)
        radio_layout.addStretch()
        trigger_layout.addLayout(radio_layout)

        # 堆叠配置面板
        self.config_stack = QStackedWidget()
        self.cron_config = CronConfigWidget()
        self.interval_config = IntervalConfigWidget()
        self.date_config = DateConfigWidget()
        self.config_stack.addWidget(self.cron_config)
        self.config_stack.addWidget(self.interval_config)
        self.config_stack.addWidget(self.date_config)
        trigger_layout.addWidget(self.config_stack)

        layout.addWidget(trigger_group)

        # ── 高级选项 ──────────────────────────────────────
        adv_group = QGroupBox("高级选项")
        adv_form = QFormLayout(adv_group)

        self.enabled_check = QCheckBox("启用此任务")
        self.enabled_check.setChecked(True)
        adv_form.addRow("", self.enabled_check)

        self.max_instances = QSpinBox()
        self.max_instances.setRange(1, 100)
        self.max_instances.setValue(1)
        adv_form.addRow("最大并发实例", self.max_instances)

        self.misfire_grace = QSpinBox()
        self.misfire_grace.setRange(1, 86400)
        self.misfire_grace.setValue(60)
        self.misfire_grace.setSuffix(" 秒")
        adv_form.addRow("错过执行宽限期", self.misfire_grace)

        self.timeout = QSpinBox()
        self.timeout.setRange(0, 86400)
        self.timeout.setValue(0)
        self.timeout.setSuffix(" 秒")
        self.timeout.setSpecialValueText("不限")
        adv_form.addRow("超时时间", self.timeout)

        layout.addWidget(adv_group)

        # ── 按钮 ──────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_trigger_changed(self):
        """切换触发类型时更新堆叠面板。"""
        if self.radio_cron.isChecked():
            self.config_stack.setCurrentWidget(self.cron_config)
        elif self.radio_interval.isChecked():
            self.config_stack.setCurrentWidget(self.interval_config)
        elif self.radio_date.isChecked():
            self.config_stack.setCurrentWidget(self.date_config)

    def _on_command_type_changed(self):
        """切换执行方式时更新提示文本。"""
        ct = self.command_type_combo.currentData()
        if ct == COMMAND_POWERSHELL:
            self.command_edit.setPlaceholderText(
                "输入 PowerShell 脚本，支持多行：\n"
                "Write-Host 'Hello'\n"
                "Get-Service | Where-Object {$_.Status -eq 'Running'}\n"
                "$files = Get-ChildItem -Path . -Filter *.log"
            )
        else:
            self.command_edit.setPlaceholderText(
                "输入 Shell 命令，如：\n"
                "echo hello && dir\n"
                "python backup.py\n"
                "mysqldump -u root mydb > backup.sql"
            )

    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if path:
            self.cwd_edit.setText(path)

    def _validate_and_accept(self):
        """校验必填字段。"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "任务名称不能为空")
            return
        if not self.command_edit.toPlainText().strip():
            QMessageBox.warning(self, "提示", "执行命令不能为空")
            return
        self.accept()

    def _load_task(self, task: dict):
        """从现有任务加载数据。"""
        self.name_edit.setText(task.get("name", ""))
        self.desc_edit.setText(task.get("description", ""))
        self.command_edit.setPlainText(task.get("command", ""))
        self.cwd_edit.setText(task.get("work_dir", ""))

        # 执行方式
        cmd_type = task.get("command_type", COMMAND_SHELL)
        idx = self.command_type_combo.findData(cmd_type)
        self.command_type_combo.setCurrentIndex(max(idx, 0))
        self._on_command_type_changed()

        self.enabled_check.setChecked(task.get("enabled", True))
        self.max_instances.setValue(task.get("max_instances", 1))
        self.misfire_grace.setValue(task.get("misfire_grace", 60))
        self.timeout.setValue(task.get("timeout", 0))

        trigger_type = task.get("trigger_type", TRIGGER_CRON)
        try:
            config = json.loads(task.get("trigger_config", "{}"))
        except json.JSONDecodeError:
            config = {}

        radio = self.radios.get(trigger_type, self.radio_cron)
        radio.setChecked(True)

        if trigger_type == TRIGGER_CRON:
            self.cron_config.set_config(config)
        elif trigger_type == TRIGGER_INTERVAL:
            self.interval_config.set_config(config)
        elif trigger_type == TRIGGER_DATE:
            self.date_config.set_config(config)

        self._on_trigger_changed()

    def get_task_data(self) -> dict:
        """收集表单数据，返回任务字典。"""
        trigger_type = TRIGGER_CRON
        if self.radio_cron.isChecked():
            trigger_type = TRIGGER_CRON
            config = self.cron_config.get_config()
        elif self.radio_interval.isChecked():
            trigger_type = TRIGGER_INTERVAL
            config = self.interval_config.get_config()
        elif self.radio_date.isChecked():
            trigger_type = TRIGGER_DATE
            config = self.date_config.get_config()

        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "command": self.command_edit.toPlainText().strip(),
            "command_type": self.command_type_combo.currentData(),
            "work_dir": self.cwd_edit.text().strip(),
            "trigger_type": trigger_type,
            "trigger_config": json.dumps(config),
            "enabled": self.enabled_check.isChecked(),
            "max_instances": self.max_instances.value(),
            "misfire_grace": self.misfire_grace.value(),
            "timeout": self.timeout.value(),
        }
