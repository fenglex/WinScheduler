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
QMainWindow, QDialog, QWidget {
    background-color: #1E1E1E;
    color: #D4D4D4;
}
QMenuBar {
    background-color: #252526;
    color: #D4D4D4;
    border-bottom: 1px solid #333333;
}
QMenuBar::item:selected { background-color: #3C3C3C; }
QMenu {
    background-color: #252526;
    color: #D4D4D4;
    border: 1px solid #333333;
}
QMenu::item:selected { background-color: #0455A4; }
QToolBar {
    background-color: #2D2D2D;
    border: none;
    border-bottom: 1px solid #333333;
    spacing: 2px;
    padding: 3px;
}
QToolBar QToolButton {
    background-color: transparent;
    color: #D4D4D4;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 8px;
}
QToolBar QToolButton:hover { background-color: #3C3C3C; }
QToolBar QToolButton:pressed { background-color: #0455A4; }
QTableWidget {
    background-color: #1E1E1E;
    alternate-background-color: #252526;
    color: #D4D4D4;
    gridline-color: #333333;
    border: none;
    selection-background-color: #0455A4;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background-color: #2D2D2D;
    color: #D4D4D4;
    border: none;
    border-right: 1px solid #333333;
    border-bottom: 1px solid #333333;
    padding: 4px 8px;
    font-weight: bold;
}
QPlainTextEdit, QTextEdit {
    background-color: #1A1A1A;
    color: #B4B2A9;
    border: 1px solid #333333;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
    background-color: #2D2D2D;
    color: #D4D4D4;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 3px 6px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #0455A4;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #2D2D2D;
    color: #D4D4D4;
    selection-background-color: #0455A4;
}
QPushButton {
    background-color: #0455A4;
    color: #FFFFFF;
    border: none;
    border-radius: 3px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover { background-color: #0567C0; }
QPushButton:pressed { background-color: #034B8A; }
QPushButton:disabled { background-color: #3C3C3C; color: #777777; }
QTabWidget::pane {
    border: 1px solid #333333;
    background-color: #1E1E1E;
}
QTabBar::tab {
    background-color: #2D2D2D;
    color: #AAAAAA;
    border: 1px solid #333333;
    border-bottom: none;
    padding: 5px 14px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1E1E1E;
    color: #D4D4D4;
    border-bottom: 2px solid #0455A4;
}
QStatusBar {
    background-color: #0455A4;
    color: #FFFFFF;
}
QStatusBar QLabel { color: #FFFFFF; }
QCheckBox { color: #D4D4D4; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #555555;
    border-radius: 2px;
    background-color: #2D2D2D;
}
QCheckBox::indicator:checked {
    background-color: #0455A4;
    border: 1px solid #0455A4;
}
QGroupBox {
    border: 1px solid #333333;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    color: #CCCCCC;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QSplitter::handle { background-color: #333333; }
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }
QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #424242;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #4F4F4F; }
QScrollBar::add-line, QScrollBar::sub-line { border: none; background: none; }
QScrollBar:horizontal {
    background-color: #1E1E1E;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #424242;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background-color: #4F4F4F; }
QDateTimeEdit {
    background-color: #2D2D2D;
    color: #D4D4D4;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 3px 6px;
}
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
