#!/usr/bin/env bash
# ============================================================
#  WinScheduler 一键打包脚本（Git Bash / WSL）
#
#  流程与 build.bat 完全一致，参数：
#    --clean       先清理旧产物
#    --skip-icon   跳过图标生成
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PY="$VENV_DIR/Scripts/python.exe"
VENV_PYINSTALLER="$VENV_DIR/Scripts/pyinstaller.exe"

CLEAN=0
SKIP_ICON=0
for arg in "$@"; do
    case "$arg" in
        --clean)      CLEAN=1 ;;
        --skip-icon)  SKIP_ICON=1 ;;
        *) echo "[警告] 忽略未知参数: $arg" ;;
    esac
done

# ── 步骤 0: 清理 ─────────────────────────────
if [ "$CLEAN" = "1" ]; then
    echo "[0/5] 清理旧产物 ..."
    rm -rf dist build app.ico
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
fi

# ── 步骤 1: 检查 uv ──────────────────────────
if ! command -v uv >/dev/null 2>&1; then
    echo "[错误] 未检测到 uv。请先安装："
    echo "       https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# ── 步骤 2: venv ────────────────────────────
if [ ! -f "$VENV_PY" ]; then
    echo "[1/5] 创建虚拟环境 .venv ..."
    uv venv "$VENV_DIR"
else
    echo "[1/5] 复用现有虚拟环境 .venv"
fi

# ── 步骤 3: 依赖 ────────────────────────────
echo "[2/5] 安装依赖（首次较慢）..."
uv pip install -r requirements.txt --python "$VENV_PY"

# ── 步骤 4: 图标 ────────────────────────────
if [ "$SKIP_ICON" = "1" ] && [ -f "$PROJECT_DIR/app.ico" ]; then
    echo "[3/5] 跳过图标生成（沿用现有 app.ico）"
else
    echo "[3/5] 生成应用图标 app.ico ..."
    "$VENV_PY" "$PROJECT_DIR/tools/build_icon.py" "$PROJECT_DIR/app.ico"
fi

# ── 步骤 5: PyInstaller ─────────────────────
echo "[4/5] PyInstaller 打包（耗时约 2-5 分钟）..."
"$VENV_PYINSTALLER" "$PROJECT_DIR/build.spec" --noconfirm

# ── 步骤 6: 清理 ────────────────────────────
echo "[5/5] 清理中间文件 ..."
rm -rf "$PROJECT_DIR/build"
find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo
echo "============================================================"
echo " 打包完成！"
echo " 产物: $PROJECT_DIR/dist/WinScheduler/WinScheduler.exe"
echo "============================================================"
