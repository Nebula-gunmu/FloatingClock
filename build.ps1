# FloatingClock 打包脚本（PowerShell 版，等价于 build.bat）
# 用法：右键“使用 PowerShell 运行”，或在终端执行
#   powershell -ExecutionPolicy Bypass -File .\build.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -LiteralPath $root

function Write-Step([string]$text) {
    Write-Host ''
    Write-Host "==> $text" -ForegroundColor Cyan
}

function Fail([string]$text) {
    Write-Host ''
    Write-Host "[错误] $text" -ForegroundColor Red
    exit 1
}

Write-Host '============================================' -ForegroundColor Yellow
Write-Host ' FloatingClock 一键打包（目录式 / onedir）' -ForegroundColor Yellow
Write-Host '============================================' -ForegroundColor Yellow

Write-Step '检查 Python 环境'
try {
    python --version
} catch {
    Fail '未找到 python 命令，请安装 Python 3.11+ 并勾选 Add Python to PATH。'
}

Write-Step '安装 / 校验依赖（PySide6、PyInstaller）'
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail 'pip 升级失败。' }
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Fail '依赖安装失败，可尝试：python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple'
}

Write-Step '生成图标资源'
python tools\make_icon.py

Write-Step '开始打包（--clean --noconfirm）'
python -m PyInstaller --clean --noconfirm FloatingClock.spec
if ($LASTEXITCODE -ne 0) { Fail '打包失败，请查看上方日志。' }

Write-Host ''
Write-Host '============================================' -ForegroundColor Green
Write-Host ' 打包完成' -ForegroundColor Green
Write-Host ' 输出目录：dist\FloatingClock\' -ForegroundColor Green
Write-Host ' 可执行文件：dist\FloatingClock\FloatingClock.exe' -ForegroundColor Green
Write-Host '============================================' -ForegroundColor Green
Write-Host ''
Write-Host '分发方式：压缩整个 dist\FloatingClock 文件夹，对方解压后双击 exe 即可运行。'
