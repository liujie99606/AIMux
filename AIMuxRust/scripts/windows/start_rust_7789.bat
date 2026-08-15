@echo off
chcp 65001 >nul
setlocal
title AIMux 稳定 Rust 网关
cd /d "%~dp0..\..\src-tauri"

set "AIMUX_PORT=7789"
set "AIMUX_MONITORING_ENABLED="

if not exist "target\debug\aimux-gateway.exe" (
    echo 未找到稳定 Rust 网关程序。
    echo 请先执行：cargo build --bin aimux-gateway
    echo.
    pause
    exit /b 1
)

echo 正在启动稳定 Rust 网关，端口 7789...
target\debug\aimux-gateway.exe

echo.
echo 稳定 Rust 网关已停止，按任意键关闭窗口。
pause >nul
