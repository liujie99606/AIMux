@echo off
setlocal
chcp 65001 >nul 2>&1

REM AIMux Windows 打包脚本：自动创建虚拟环境、安装依赖并打包为桌面应用。
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

echo [AIMux] 正在打包，首次构建需要下载依赖，请耐心等待 ...
".venv\Scripts\python.exe" scripts\build.py
if errorlevel 1 (
    echo [AIMux] 打包失败，请查看上方日志。
    pause
    exit /b 1
)

echo.
echo [AIMux] 打包完成！可执行文件位于：dist\AIMux\AIMux.exe
echo.
endlocal
