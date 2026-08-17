@echo off
chcp 65001 >nul
setlocal
title AIMux 稳定前端服务
cd /d "%~dp0..\.."

for /f %%P in ('node scripts\runtime-ports.mjs stable backend') do set "STABLE_BACKEND_PORT=%%P"
for /f %%P in ('node scripts\runtime-ports.mjs stable frontend') do set "STABLE_FRONTEND_PORT=%%P"
if not defined STABLE_BACKEND_PORT (
    echo 无法读取稳定后端端口配置。
    pause
    exit /b 1
)
if not defined STABLE_FRONTEND_PORT (
    echo 无法读取稳定前端端口配置。
    pause
    exit /b 1
)

set "AIMUX_RUNTIME_MODE=stable"
set "VITE_API_BASE=http://127.0.0.1:%STABLE_BACKEND_PORT%"
echo 正在启动稳定 Vite 前端，端口 %STABLE_FRONTEND_PORT%...
echo 当前连接 Rust 稳定后端，端口 %STABLE_BACKEND_PORT%...
echo 请先启动 scripts\windows\stable_start_rust_7789.bat 或稳定版网关。
call npm run dev

echo.
echo 稳定前端服务已停止，按任意键关闭窗口。
pause >nul
