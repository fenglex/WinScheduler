"""全局配置：路径、常量、默认值。"""

import os
import sys

APP_NAME = "WinScheduler"
APP_VERSION = "1.0.0"

# ── 数据目录 ──────────────────────────────────────────────
# 优先使用 %APPDATA%，打包后数据不随 exe 移动而丢失。
_APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
DATA_DIR = os.path.join(_APPDATA, APP_NAME)

DB_PATH = os.path.join(DATA_DIR, "tasks.db")
DB_URL = f"sqlite:///{DB_PATH}"

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# ── 单实例锁端口 ──────────────────────────────────────────
SINGLE_INSTANCE_PORT = 47200

# ── 默认配置 ──────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "autostart": False,
    "theme": "dark",          # dark / light
    "log_retention_days": 30,
    "minimize_to_tray": True,
}

# ── 日志颜色（暗色主题）──────────────────────────────────
LOG_COLORS = {
    "INFO":    "#B4B2A9",
    "WARN":    "#FAC775",
    "ERROR":   "#E24B4A",
    "SUCCESS": "#639922",
    "DEBUG":   "#7A7A7A",
}

# ── QSS 暗色主题 ──────────────────────────────────────────
DARK_THEME_QSS = """
/* 全局基础：深色 + 清晰字体（Windows 优先 Microsoft YaHei UI，中文混排友好） */
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog, QWidget {
    background-color: #1E1E1E;
    color: #D4D4D4;
}

/* ── 菜单栏 ─────────────────────────────────────── */
QMenuBar {
    background-color: #252526;
    color: #D4D4D4;
    border-bottom: 1px solid #333333;
    padding: 2px 4px;
}
QMenuBar::item {
    padding: 5px 12px;
    background: transparent;
    border-radius: 3px;
}
QMenuBar::item:selected { background-color: #3C3C3C; }
QMenu {
    background-color: #252526;
    color: #D4D4D4;
    border: 1px solid #3C3C3C;
    padding: 4px 0;
}
QMenu::item {
    padding: 6px 28px 6px 24px;
    border-radius: 2px;
}
QMenu::item:selected { background-color: #0455A4; color: #FFFFFF; }
QMenu::separator {
    height: 1px;
    background: #3C3C3C;
    margin: 4px 8px;
}

/* ── 工具栏（按钮 + 文字 + 提示）───────────────────── */
QToolBar {
    background-color: #2A2A2A;
    border: none;
    border-bottom: 1px solid #333333;
    spacing: 4px;
    padding: 5px 8px;
    min-height: 36px;
}
QToolBar QToolButton {
    background-color: transparent;
    color: #D4D4D4;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    margin: 0;
    font-size: 13px;
    /* 图标与文字间距（Qt 6 默认 toolButtonStyle 在代码中控制） */
}
QToolBar QToolButton:hover {
    background-color: #3A3A3A;
    border-color: #4A4A4A;
}
QToolBar QToolButton:pressed,
QToolBar QToolButton:checked {
    background-color: #0455A4;
    color: #FFFFFF;
    border-color: #0455A4;
}
QToolBar QToolButton:disabled {
    color: #6A6A6A;
    background-color: transparent;
}
QToolBar::separator {
    background-color: #3C3C3C;
    width: 1px;
    margin: 6px 6px;
}

/* ── 表格 ──────────────────────────────────────── */
QTableWidget {
    background-color: #1E1E1E;
    alternate-background-color: #232323;
    color: #D4D4D4;
    gridline-color: #2F2F2F;
    border: none;
    selection-background-color: #0455A4;
    selection-color: #FFFFFF;
    outline: 0;
}
QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #252525;
}
QTableWidget::item:hover:!selected {
    background-color: #2A2A2A;
}
QTableCornerButton::section {
    background-color: #2D2D2D;
    border: none;
}
QHeaderView {
    background-color: #2D2D2D;
}
QHeaderView::section {
    background-color: #2D2D2D;
    color: #CCCCCC;
    border: none;
    border-right: 1px solid #1E1E1E;
    border-bottom: 2px solid #0455A4;
    padding: 8px 8px;
    font-weight: bold;
    font-size: 12px;
}
QHeaderView::section:hover {
    background-color: #353535;
    color: #FFFFFF;
}

/* ── 文本编辑框 ──────────────────────────────────── */
QPlainTextEdit, QTextEdit {
    background-color: #1A1A1A;
    color: #B4B2A9;
    border: 1px solid #333333;
    border-radius: 3px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #0455A4;
    selection-color: #FFFFFF;
}
QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #0455A4;
}

/* ── 输入控件 ────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox, QDateTimeEdit, QDateEdit, QTimeEdit {
    background-color: #2D2D2D;
    color: #D4D4D4;
    border: 1px solid #3C3C3C;
    border-radius: 3px;
    padding: 5px 8px;
    min-height: 18px;
    selection-background-color: #0455A4;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #0455A4;
    background-color: #333333;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    color: #6A6A6A;
    background-color: #252525;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #2D2D2D;
    color: #D4D4D4;
    border: 1px solid #3C3C3C;
    selection-background-color: #0455A4;
    selection-color: #FFFFFF;
    padding: 2px;
}

/* ── 按钮 ───────────────────────────────────────── */
QPushButton {
    background-color: #0455A4;
    color: #FFFFFF;
    border: none;
    border-radius: 3px;
    padding: 6px 16px;
    font-weight: bold;
    min-height: 18px;
}
QPushButton:hover { background-color: #0567C0; }
QPushButton:pressed { background-color: #034B8A; }
QPushButton:disabled { background-color: #3C3C3C; color: #777777; }

/* ── Tab 控件 ────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #333333;
    border-top: none;
    background-color: #1E1E1E;
    top: -1px;
}
QTabBar {
    background-color: transparent;
}
QTabBar::tab {
    background-color: #2D2D2D;
    color: #AAAAAA;
    border: 1px solid #333333;
    border-bottom: none;
    padding: 7px 18px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    min-width: 80px;
}
QTabBar::tab:hover:!selected {
    background-color: #353535;
    color: #D4D4D4;
}
QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #FFFFFF;
    border-bottom: 2px solid #0455A4;
}

/* ── 状态栏（蓝色条带 + 右侧分组）─────────────────── */
QStatusBar {
    background-color: #0455A4;
    color: #FFFFFF;
    border-top: 1px solid #034B8A;
    min-height: 26px;
}
QStatusBar QLabel {
    color: #FFFFFF;
    padding: 0 12px;
    border-right: 1px solid rgba(255, 255, 255, 0.25);
}
QStatusBar QLabel:last-child { border-right: none; }
QStatusBar::item { border: none; }

/* ── 复选框 ──────────────────────────────────────── */
QCheckBox { color: #D4D4D4; spacing: 6px; }
QCheckBox:disabled { color: #6A6A6A; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #555555;
    border-radius: 3px;
    background-color: #2D2D2D;
}
QCheckBox::indicator:hover { border: 1px solid #0455A4; }
QCheckBox::indicator:checked {
    background-color: #0455A4;
    border: 1px solid #0455A4;
    image: none;
}
QCheckBox::indicator:checked:hover { background-color: #0567C0; }

/* 单选按钮 */
QRadioButton { color: #D4D4D4; spacing: 6px; padding: 4px 0; }
QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 1px solid #555555;
    border-radius: 8px;
    background-color: #2D2D2D;
}
QRadioButton::indicator:checked {
    background-color: #2D2D2D;
    border: 1px solid #0455A4;
}
QRadioButton::indicator:checked:hover { border: 1px solid #0567C0; }

/* ── 分组框 ──────────────────────────────────────── */
QGroupBox {
    border: 1px solid #333333;
    border-radius: 4px;
    margin-top: 14px;
    padding: 12px 8px 8px 8px;
    color: #CCCCCC;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #1E1E1E;
}

/* ── 分割器 ──────────────────────────────────────── */
QSplitter::handle { background-color: #333333; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }
QSplitter::handle:hover { background-color: #0455A4; }

/* ── 滚动条 ──────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 12px;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover { background-color: #4F4F4F; }
QScrollBar::handle:vertical:pressed { background-color: #0455A4; }
QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; height: 0; }
QScrollBar:horizontal {
    background-color: #1E1E1E;
    height: 12px;
    border: none;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #424242;
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover { background-color: #4F4F4F; }
QScrollBar::handle:horizontal:pressed { background-color: #0455A4; }

/* ── 表单标签（更醒目）───────────────────────────── */
QLabel { color: #D4D4D4; }
QLabel#required { color: #E24B4A; font-weight: bold; }
QLabel#hint {
    color: #888888;
    font-size: 11px;
}

/* ── ToolTip ─────────────────────────────────────── */
QToolTip {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #0455A4;
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── 对话框按钮框 ────────────────────────────────── */
QDialogButtonBox QPushButton { min-width: 72px; }
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #F5F5F5;
    color: #333333;
}
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F0F0F0;
    color: #333333;
    gridline-color: #CCCCCC;
    selection-background-color: #CCE4F7;
    selection-color: #000000;
}
QPlainTextEdit, QTextEdit {
    background-color: #FFFFFF;
    color: #333333;
    border: 1px solid #CCCCCC;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QStatusBar {
    background-color: #E0E0E0;
    color: #333333;
}
"""

# ── 触发器类型 ────────────────────────────────────────────
TRIGGER_CRON = "cron"
TRIGGER_INTERVAL = "interval"
TRIGGER_DATE = "date"

TRIGGER_TYPES = [TRIGGER_CRON, TRIGGER_INTERVAL, TRIGGER_DATE]
TRIGGER_LABELS = {
    TRIGGER_CRON: "Cron 表达式",
    TRIGGER_INTERVAL: "固定间隔",
    TRIGGER_DATE: "一次性定时",
}

# ── 命令执行方式 ──────────────────────────────────────────
COMMAND_SHELL = "shell"
COMMAND_POWERSHELL = "powershell"

COMMAND_TYPES = [COMMAND_SHELL, COMMAND_POWERSHELL]
COMMAND_LABELS = {
    COMMAND_SHELL: "Shell (cmd / bat)",
    COMMAND_POWERSHELL: "PowerShell 脚本",
}

# ── 任务状态 ──────────────────────────────────────────────
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"
STATUS_KILLED = "killed"

STATUS_LABELS = {
    STATUS_RUNNING: "运行中",
    STATUS_SUCCESS: "成功",
    STATUS_FAILED: "失败",
    STATUS_TIMEOUT: "超时",
    STATUS_KILLED: "已终止",
}

# ── 工具函数 ──────────────────────────────────────────────
def ensure_data_dir():
    """确保数据目录存在。"""
    os.makedirs(DATA_DIR, exist_ok=True)


def is_frozen():
    """是否运行在 PyInstaller 打包环境中。"""
    return getattr(sys, "frozen", False)


def resource_path(relative: str) -> str:
    """获取资源文件的绝对路径（兼容 PyInstaller 打包）。"""
    if is_frozen():
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)
