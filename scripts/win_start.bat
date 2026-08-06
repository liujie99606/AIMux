@echo off
setlocal
chcp 65001 >nul 2>&1

REM AIMux Windows 启动脚本：自动创建虚拟环境、安装依赖并启动桌面端。
REM 脚本位于 scripts/ 下，需切到项目根目录运行。

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [AIMux] 未检测到虚拟环境，正在创建 .venv ...
    py -3.13 -m venv .venv
    if errorlevel 1 (
        echo [AIMux] 虚拟环境创建失败，请确认已安装 Python 3.13。
        pause
        exit /b 1
    )
    echo [AIMux] 正在安装依赖 ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
    if errorlevel 1 (
        echo [AIMux] 依赖安装失败，请检查网络或手动执行 pip install。
        pause
        exit /b 1
    )
)

echo [AIMux] 正在启动 ...
".venv\Scripts\python.exe" -m app
endlocal