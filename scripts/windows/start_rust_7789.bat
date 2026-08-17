@echo off
chcp 65001 >nul
setlocal
title AIMux 稳定 Rust 网关
cd /d "%~dp0..\..\src-tauri"

for /f %%P in ('node ..\scripts\runtime-ports.mjs stable backend') do set "STABLE_BACKEND_PORT=%%P"
if not defined STABLE_BACKEND_PORT (
    echo 无法读取稳定后端端口配置。
    pause
    exit /b 1
)
set "AIMUX_PORT=%STABLE_BACKEND_PORT%"
set "AIMUX_MONITORING_ENABLED="

if not exist "target\debug\aimux-gateway.exe" (
    echo 未找到稳定 Rust 网关程序。
    echo 请先执行：cargo build --bin aimux-gateway
    echo.
    pause
    exit /b 1
)

echo 正在启动稳定 Rust 网关，端口 %STABLE_BACKEND_PORT%...
target\debug\aimux-gateway.exe

echo.
echo 稳定 Rust 网关已停止，按任意键关闭窗口。
pause >nul
