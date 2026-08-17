@echo off
chcp 65001 >nul
setlocal EnableExtensions
title AIMux Rust Windows 打包
cd /d "%~dp0..\.."

where npm >nul 2>&1
if errorlevel 1 (
    echo [AIMux] 未找到 npm，请先安装 Node.js LTS。
    pause
    exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 (
    echo [AIMux] 未找到 cargo，请先安装 Rust stable 工具链。
    pause
    exit /b 1
)

if not exist "node_modules\@tauri-apps\cli\package.json" (
    echo [%time:~0,8%] [AIMux] 阶段 1/3：正在安装前端和 Tauri 依赖...
    call npm ci
    if errorlevel 1 (
        echo [AIMux] 依赖安装失败，请检查网络或 npm 配置。
        pause
        exit /b 1
    )
) else (
    echo [%time:~0,8%] [AIMux] 阶段 1/3：依赖已存在，跳过安装。
)

echo [%time:~0,8%] [AIMux] 阶段 2/3：正在构建 Vue、Rust 和 Windows 安装包...
call npm run tauri build -- --bundles nsis
if errorlevel 1 (
    echo [AIMux] 打包失败，请查看上方日志。
    pause
    exit /b 1
)

set "ARCH=x64"
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
set "BUNDLE_DIR=src-tauri\target\release\bundle\nsis"
set "INSTALLER="
if exist "%BUNDLE_DIR%\*.exe" (
    for %%F in ("%BUNDLE_DIR%\*.exe") do set "INSTALLER=%%~fF"
)
if not defined INSTALLER (
    echo [AIMux] 打包完成，但未找到 NSIS 安装包：%BUNDLE_DIR%
    pause
    exit /b 1
)

if not exist "release" mkdir "release"
set "OUTPUT=release\AIMux-Windows-%ARCH%.exe"
copy /Y "%INSTALLER%" "%OUTPUT%" >nul
if errorlevel 1 (
    echo [AIMux] 安装包复制失败：%OUTPUT%
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] 阶段 3/3：打包完成。
echo [AIMux] 安装包：%CD%\%OUTPUT%
echo.
pause
endlocal
