@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  FloatingClock 一键打包（目录式 / onedir）
echo ============================================
echo.

echo [1/4] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo.
    echo [错误] 未找到 python 命令。
    echo 请先安装 Python 3.11 或更高版本，安装时勾选 "Add Python to PATH"。
    goto :fail
)

echo.
echo [2/4] 安装 / 校验依赖（PySide6、PyInstaller）...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败，请检查网络或更换 pip 镜像源：
    echo   python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    goto :fail
)

echo.
echo [3/4] 生成图标资源...
python tools\make_icon.py

echo.
echo [4/4] 开始打包（--clean --noconfirm）...
python -m PyInstaller --clean --noconfirm FloatingClock.spec
if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请查看上方日志。
    goto :fail
)

echo.
echo ============================================
echo  打包完成
echo  输出目录：dist\FloatingClock\
echo  可执行文件：dist\FloatingClock\FloatingClock.exe
echo ============================================
echo.
echo 分发方式：把整个 dist\FloatingClock 文件夹压缩后发给用户，
echo 对方解压后直接双击 FloatingClock.exe 即可运行（无需安装 Python）。
goto :eof

:fail
echo.
pause
exit /b 1
