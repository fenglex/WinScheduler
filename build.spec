# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec - 任务调度器打包配置（精简版）。

输出目录：dist/WinScheduler/

体积控制策略：
- 用 collect_submodules 精确收集 PySide6 子模块（仅 QtCore/Gui/Widgets）
- excludes 显式排除所有不用的 Qt 子模块
- COLLECT 后用 Python 清理 translations/qml/qtwebengine 等大文件
"""

import os

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
    # WebEngine 是体积大头（~200MB）— 本应用完全不用
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WinScheduler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WinScheduler",
)


# ── 后处理：删除 PyInstaller 没排除干净的大文件 ─────────
def _post_strip():
    """去掉 QtWebEngine / QML / 多余翻译等大文件。"""
    base = os.path.join(DISTPATH, "WinScheduler", "_internal", "PySide6")
    if not os.path.isdir(base):
        return

    # 完全删除的目录
    drop_dirs = [
        "translations",                       # ~60MB
        "qml",                                # ~30MB
        "QtNetwork", "QtSql", "QtMultimedia", # 没用到但 PyInstaller 仍可能拉进来
    ]
    for d in drop_dirs:
        p = os.path.join(base, d)
        if os.path.isdir(p):
            import shutil
            shutil.rmtree(p, ignore_errors=True)

    # 删除不需要的 Qt DLL（即使 excludes 命中，仍可能有遗留）
    drop_dlls = [
        "Qt6WebEngineCore.dll",
        "Qt6WebEngineWidgets.dll",
        "Qt6WebEngineQuick.dll",
        "Qt6WebChannel.dll",
        "Qt6Pdf.dll", "Qt6PdfWidgets.dll",
        "Qt6Multimedia.dll", "Qt6MultimediaWidgets.dll",
        "Qt6MultimediaQuick.dll",
        "Qt63DCore.dll", "Qt63DRender.dll", "Qt63DExtras.dll",
        "Qt63DQuick.dll", "Qt63DQuickExtras.dll", "Qt63DLogic.dll",
        "Qt6Charts.dll", "Qt6DataVisualization.dll", "Qt6Graphs.dll",
        "Qt6Svg.dll", "Qt6SvgWidgets.dll",
        "Qt6Qml.dll", "Qt6Quick.dll", "Qt6QuickWidgets.dll",
        "Qt6Bluetooth.dll", "Qt6Nfc.dll", "Qt6Positioning.dll",
        "Qt6SerialPort.dll", "Qt6SerialBus.dll",
        "Qt6RemoteObjects.dll", "Qt6Sensors.dll",
        "Qt6TextToSpeech.dll", "Qt6Xml.dll", "Qt6XmlPatterns.dll",
        "Qt6Scxml.dll", "Qt6StateMachine.dll",
        "Qt6Test.dll", "Qt6Help.dll", "Qt6Location.dll",
        "Qt6Designer.dll", "Qt6UiTools.dll",
        "Qt6PrintSupport.dll", "Qt6Concurrent.dll", "Qt6DBus.dll",
        "Qt6OpenGL.dll", "Qt6OpenGLWidgets.dll",
        "Qt6Sql.dll", "Qt6Network.dll", "Qt6NetworkAuth.dll",
        "Qt6WebSockets.dll", "Qt6WebView.dll", "Qt6WebEngine.dll",
        # 以下为本应用不用但 PyInstaller 仍拉进来的：
        "opengl32sw.dll",           # 5.3MB 软件渲染 OpenGL 后备
        "Qt6QmlModels.dll",         # 976KB QML 模型
        "Qt6QmlMeta.dll",           # 160KB QML 元对象
        "Qt6QmlWorkerScript.dll",   # QML WorkerScript
        "Qt6VirtualKeyboard.dll",   # 436KB 虚拟键盘（桌面不用）
        "d3dcompiler_47.dll",       # DirectX 编译器（QtGui 可能带入）
    ]
    for dll in drop_dlls:
        p = os.path.join(base, dll)
        if os.path.isfile(p):
            try:
                os.unlink(p)
            except OSError:
                pass

    # 删除 qtwebengine 资源（即使 DLL 被删，资源仍可能残留）
    res_dir = os.path.join(base, "resources")
    if os.path.isdir(res_dir):
        for f in os.listdir(res_dir):
            if any(k in f.lower() for k in ("webengine", "icudtl.dat", "v8_context")):
                try:
                    os.unlink(os.path.join(res_dir, f))
                except OSError:
                    pass

    # ── 精简 plugins/ ────────────────────────────────
    # imageformats：只保留 qico（Windows 图标）和 qsvg（SVG 矢量）
    # 本应用图标用 QPainter 程序化绘制，理论上不需要任何 imageformat
    img_dir = os.path.join(base, "plugins", "imageformats")
    if os.path.isdir(img_dir):
        for f in os.listdir(img_dir):
            if not f.lower().startswith(("qico", "qsvg")):
                try:
                    os.unlink(os.path.join(img_dir, f))
                except OSError:
                    pass

    # platforms：只保留 qwindows.dll
    # 删除 qdirect2d（与 qwindows 重复）、qminimal、qoffscreen
    plat_dir = os.path.join(base, "plugins", "platforms")
    if os.path.isdir(plat_dir):
        for f in os.listdir(plat_dir):
            if not f.lower().startswith("qwindows"):
                try:
                    os.unlink(os.path.join(plat_dir, f))
                except OSError:
                    pass

    # generic：删除触屏插件（桌面不用）
    gen_dir = os.path.join(base, "plugins", "generic")
    if os.path.isdir(gen_dir):
        import shutil
        shutil.rmtree(gen_dir, ignore_errors=True)

    # 报告最终体积
    total = 0
    for root, _, files in os.walk(os.path.join(DISTPATH, "WinScheduler")):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    print(f"[build.spec] 打包后体积: {total / 1024 / 1024:.1f} MB")


_post_strip()
