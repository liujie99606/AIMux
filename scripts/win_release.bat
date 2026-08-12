@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1

REM AIMux Windows 发布入口：全量构建 onedir，再封装为单个 Inno Setup 安装包。

cd /d "%~dp0\.."

echo [%time:~0,8%] [AIMux] 阶段 1/3：全量构建 Windows 应用 ...
call "%~dp0win_build.bat" --clean
if errorlevel 1 (
    echo [AIMux] 发布已停止：应用构建失败。
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] 阶段 2/3：生成单文件安装包 ...
".venv\Scripts\python.exe" scripts\release_installer.py
if errorlevel 1 (
    echo [AIMux] 发布已停止：安装包生成失败，请查看上方日志。
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] 阶段 3/3：发布完成。
echo [AIMux] 用户数据库和配置仍保存在 %%APPDATA%%\aimux，覆盖安装不会删除。
echo.
pause
endlocal
