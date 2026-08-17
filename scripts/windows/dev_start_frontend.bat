@echo off
chcp 65001 >nul
setlocal
title AIMux 前端开发服务
cd /d "%~dp0..\.."

for /f %%P in ('node scripts\runtime-ports.mjs development backend') do set "DEV_BACKEND_PORT=%%P"
for /f %%P in ('node scripts\runtime-ports.mjs development frontend') do set "DEV_FRONTEND_PORT=%%P"
if not defined DEV_BACKEND_PORT (
    echo 无法读取开发后端端口配置。
    pause
    exit /b 1
)
if not defined DEV_FRONTEND_PORT (
    echo 无法读取开发前端端口配置。
    pause
    exit /b 1
)

set "AIMUX_RUNTIME_MODE=development"
set "VITE_API_BASE=http://127.0.0.1:%DEV_BACKEND_PORT%"
echo 正在启动开发 Vite 前端，端口 %DEV_FRONTEND_PORT%...
echo 当前连接 Rust 开发后端，端口 %DEV_BACKEND_PORT%...
call npm run dev

echo.
echo 前端开发服务已停止，按任意键关闭窗口。
pause >nul
