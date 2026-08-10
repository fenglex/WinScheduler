# ============================================================
#  WinScheduler 一键打包脚本（PowerShell 原生）
#
#  为什么是 .ps1 而非 .bat：
#    PowerShell 5.1 控制台默认代码页是 GBK，.bat 文件中 UTF-8
#    编码的中文字符和 box-drawing 分隔线会乱码，导致条件判断、
#    路径拼接全部失败。.ps1 由 PowerShell 自身解析 UTF-8 源文件，
#    不受控制台代码页影响。
#
#  用法（在 PowerShell 中）：
#    .\build.ps1                 运行后选择打包模式
#    .\build.ps1 -Clean          先清理旧产物
#    .\build.ps1 -SkipIcon       跳过图标生成
#
#  两种模式对比：
#    dir     → 启动快、体积小，但需附带 _internal 目录
#    onefile → 单 exe 分发方便，但启动稍慢、体积略大
# ============================================================

param(
    [switch]$Clean,
    [switch]$SkipIcon
)

# 让中文输出在控制台不乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir
$ProjectDir = (Get-Location).Path
$VenvDir = Join-Path $ProjectDir '.venv'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'
$VenvPyInstaller = Join-Path $VenvDir 'Scripts\pyinstaller.exe'
$IconPath = Join-Path $ProjectDir 'app.ico'

# ── 选择打包模式 ──────────────────────────────────────────
Write-Host '请选择打包模式：' -ForegroundColor Cyan
Write-Host '  [1] 目录模式 (dir)       — 启动快、体积小，需附带 _internal'
Write-Host '  [2] 单文件模式 (onefile)   — 单 exe 分发方便，启动稍慢'
$choice = Read-Host '请输入 1 或 2（默认 1）'
$Mode = switch ($choice.Trim()) {
    '2' { 'onefile' }
    default { 'dir' }
}

# 根据模式确定 spec 文件和产物信息
$SpecFile = if ($Mode -eq 'onefile') { 'build_onefile.spec' } else { 'build.spec' }
$ModeLabel = if ($Mode -eq 'onefile') { '单文件模式' } else { '目录模式' }

Write-Host ''
Write-Host "打包模式: $ModeLabel ($Mode)" -ForegroundColor Yellow
Write-Host ''

function Step($n, $total, $msg) {
    Write-Host "[$n/$total] $msg" -ForegroundColor Cyan
}

# 步骤 0：清理旧产物
if ($Clean) {
    Step 0 5 '清理旧产物 ...'
    foreach ($p in @('dist', 'build')) {
        $full = Join-Path $ProjectDir $p
        if (Test-Path $full) { Remove-Item -Recurse -Force $full }
    }
    if (Test-Path $IconPath) { Remove-Item -Force $IconPath }
    Get-ChildItem -Path $ProjectDir -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ProjectDir -Recurse -File -Filter '*.pyc' -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

# 步骤 1：检查 uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host '[错误] 未检测到 uv' -ForegroundColor Red
    Write-Host '       请先安装: https://docs.astral.sh/uv/getting-started/installation/' -ForegroundColor Red
    exit 1
}

# 步骤 2：创建/复用 venv
if (-not (Test-Path $VenvPy)) {
    Step 1 5 '创建虚拟环境 .venv ...'
    uv venv $VenvDir
    if ($LASTEXITCODE -ne 0) { exit 1 }
} else {
    Step 1 5 '复用现有虚拟环境 .venv'
}

# 步骤 3：安装依赖
Step 2 5 '安装依赖（首次较慢）...'
uv pip install -r requirements.txt --python $VenvPy
if ($LASTEXITCODE -ne 0) {
    Write-Host '[错误] 安装依赖失败' -ForegroundColor Red
    exit 1
}

# 步骤 4：生成图标
if ($SkipIcon -and (Test-Path $IconPath)) {
    Step 3 5 '跳过图标生成（沿用现有 app.ico）'
} else {
    Step 3 5 '生成应用图标 app.ico ...'
    & $VenvPy (Join-Path $ProjectDir 'tools\build_icon.py') $IconPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[错误] 生成图标失败' -ForegroundColor Red
        exit 1
    }
}

# 步骤 5：PyInstaller
Step 4 5 "PyInstaller 打包 - $ModeLabel（耗时约 2-8 分钟）..."
& $VenvPyInstaller (Join-Path $ProjectDir $SpecFile) --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host '[错误] PyInstaller 打包失败' -ForegroundColor Red
    exit 1
}

# 步骤 6：清理中间文件
Step 5 5 '清理中间文件 ...'
$buildDir = Join-Path $ProjectDir 'build'
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
Get-ChildItem -Path $ProjectDir -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $ProjectDir -Recurse -File -Filter '*.pyc' -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

# 报告产物
Write-Host ''
Write-Host '============================================================' -ForegroundColor Green
Write-Host ' 打包完成' -ForegroundColor Green
Write-Host " 模式: $ModeLabel"
if ($Mode -eq 'onefile') {
    $exePath = Join-Path $ProjectDir 'dist\WinScheduler.exe'
    if (Test-Path $exePath) {
        $sizeMB = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
        Write-Host " 产物: $exePath"
        Write-Host " 体积: $sizeMB MB"
    }
} else {
    $dirPath = Join-Path $ProjectDir 'dist\WinScheduler'
    if (Test-Path $dirPath) {
        $totalBytes = (Get-ChildItem -Path $dirPath -Recurse -File |
            Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($totalBytes / 1MB, 1)
        Write-Host " 产物: $dirPath"
        Write-Host " 体积: $sizeMB MB"
    }
}
Write-Host '============================================================' -ForegroundColor Green
Write-Host ''
