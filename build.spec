# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 任务调度器打包配置。

用法：
    .venv\\Scripts\\pyinstaller build.spec --noconfirm

输出目录：dist/WinScheduler/
"""

from PyInstaller.utils.hooks import collect_all

# 收集 PySide6 全部依赖（插件、翻译、Qt 资源）
ps6_datas, ps6_binaries, ps6_hiddenimports = collect_all("PySide6")

# APScheduler 隐式导入：触发器和 JobStore 模块
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
    binaries=ps6_binaries,
    datas=ps6_datas,
    hiddenimports=apscheduler_hidden + ps6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
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
    console=False,          # --noconsole：无控制台黑框
    icon=None,              # 无外部图标（程序运行时自动生成）
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
