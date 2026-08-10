# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec - 任务调度器单文件打包配置。

输出：dist/WinScheduler.exe（单文件，无需附带 _internal 目录）

与 build.spec（目录模式）的区别：
- exclude_binaries=False，所有二进制/资源嵌入 exe
- 不使用 COLLECT 块
- 无后处理 _post_strip()：单文件模式下文件已嵌入 exe，无法在打包后删除
  因此体积控制完全依赖 excludes + hiddenimports 精确收集
"""

from PyInstaller.utils.hooks import collect_submodules

# ── PySide6 精确收集：仅 QtCore / QtGui / QtWidgets ────────
ps6_used = {
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
}
ps6_all = set(collect_submodules("PySide6"))
ps6_kept = [m for m in ps6_all if any(m == u or m.startswith(u + ".") for u in ps6_used)]

# ── 排除不用的 PySide6 子模块（首层 + 递归）────────────
ps6_excluded_submodules = [
    # 网络 / 数据库 / 多媒体
    "PySide6.QtNetwork", "PySide6.QtNetworkAuth",
    "PySide6.QtSql",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtMultimediaQuick",
    # WebEngine 是体积大头（~200MB）- 本应用完全不用
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel", "PySide6.QtWebView",
    "PySide6.QtWebSockets",
    # 定位 / 蓝牙 / NFC / 串口
    "PySide6.QtPositioning", "PySide6.QtNfc", "PySide6.QtBluetooth",
    "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    # PDF / 打印
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPrintSupport",
    # 3D / QML / Quick / Charts
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
    "PySide6.Qt3DLogic", "PySide6.Qt3DInput", "PySide6.Qt3DAnimation",
    "PySide6.Qt3DQuick", "PySide6.Qt3DQuickExtras", "PySide6.Qt3DQuickScene2D",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    # 其它
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtConcurrent", "PySide6.QtDBus",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtLocation",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtRemoteObjects", "PySide6.QtScript", "PySide6.QtScriptTools",
    "PySide6.QtSensors",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtUiTools",
    "PySide6.QtXml", "PySide6.QtXmlPatterns",
    "PySide6.QtScxml", "PySide6.QtStateMachine",
]

# ── 隐式 import：APScheduler 触发器 / JobStore ─────────
apscheduler_hidden = [
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
    "apscheduler.triggers.date",
    "apscheduler.jobstores.memory",
    "apscheduler.jobstores.sqlalchemy",
    "apscheduler.executors.pool",
    "apscheduler.executors.asyncio",
    "tzlocal",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=apscheduler_hidden + ps6_kept,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "test", "unittest",
    ] + ps6_excluded_submodules,
    noarchive=False,
)

pyz = PYZ(a.pure)

# 单文件模式：a.binaries / a.datas / a.zipfiles 全部嵌入 exe
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    a.zipfiles,
    exclude_binaries=False,
    name="WinScheduler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="app.ico",
)
