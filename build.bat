@echo off
REM ============================================================
REM  WinScheduler 一键打包脚本（cmd.exe 专用）
REM
REM  推荐在 PowerShell 中使用 build.ps1（避免 cmd 编码问题）。
REM  本 .bat 保留给 cmd.exe 用户，使用 ASCII 输出 + chcp 65001
REM  切换 UTF-8 代码页。
REM
REM  用法：
REM    build.bat                  正常打包
REM    build.bat --clean          先清理旧产物
REM    build.bat --skip-icon      跳过图标生成
REM ============================================================

REM 切换 UTF-8 代码页（解决中文/特殊字符乱码）
chcp 65001 >nul 2>&1

setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
set "PROJECT_DIR=%CD%"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYINSTALLER=%VENV_DIR%\Scripts\pyinstaller.exe"
set "ICON_PATH=%PROJECT_DIR%\app.ico"

set "CLEAN=0"
set "SKIP_ICON=0"
for %%a in (%*) do (
    if /i "%%a"=="--clean"      set "CLEAN=1"
    if /i "%%a"=="--skip-icon"  set "SKIP_ICON=1"
)

REM 步骤 0: 清理
if "%CLEAN%"=="1" (
    echo [0/5] Clean old build artifacts ...
    if exist dist  rmdir /s /q dist
    if exist build rmdir /s /q build
    if exist "%ICON_PATH%" del /f /q "%ICON_PATH%"
    for /f "delims=" %%d in ('dir /s /b /ad "%PROJECT_DIR%" 2^>nul ^| findstr /i "\\__pycache__$"') do (
        rmdir /s /q "%%d" 2>nul
    )
)

REM 步骤 1: 检查 uv
where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install from: https://docs.astral.sh/uv/
    exit /b 1
)

REM 步骤 2: venv
if not exist "%VENV_PY%" (
    echo [1/5] Creating venv ...
    uv venv "%VENV_DIR%"
    if errorlevel 1 exit /b 1
) else (
    echo [1/5] Reusing venv ...
)

REM 步骤 3: 依赖
echo [2/5] Installing deps ...
uv pip install -r requirements.txt --python "%VENV_PY%"
if errorlevel 1 (
    echo [ERROR] Install failed
    exit /b 1
)

REM 步骤 4: 图标
if "%SKIP_ICON%"=="1" (
    if exist "%ICON_PATH%" (
        echo [3/5] Skip icon generation
    ) else (
        set "SKIP_ICON=0"
    )
)
if "%SKIP_ICON%"=="0" (
    echo [3/5] Generating app.ico ...
    "%VENV_PY%" "%PROJECT_DIR%\tools\build_icon.py" "%ICON_PATH%"
    if errorlevel 1 (
        echo [ERROR] Icon generation failed
        exit /b 1
    )
)

REM 步骤 5: PyInstaller
echo [4/5] Running PyInstaller ...
"%VENV_PYINSTALLER%" "%PROJECT_DIR%\build.spec" --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    exit /b 1
)

REM 步骤 6: 清理
echo [5/5] Cleanup ...
if exist "%PROJECT_DIR%\build" rmdir /s /q "%PROJECT_DIR%\build"

echo.
echo ============================================================
echo  Build complete!
echo  Output: %PROJECT_DIR%\dist\WinScheduler\WinScheduler.exe
echo ============================================================
echo.

popd
endlocal
exit /b 0
