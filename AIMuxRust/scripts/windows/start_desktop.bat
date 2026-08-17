@echo off
chcp 65001 >nul
setlocal
title AIMux 桌面端开发
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

echo 正在启动 Tauri 桌面端...
echo Vite 前端端口：%DEV_FRONTEND_PORT%
echo Rust 开发后端端口：%DEV_BACKEND_PORT%
echo 稳定 Rust 后端端口：不占用
call npm run dev:desktop

echo.
echo 桌面端开发进程已停止，按任意键关闭窗口。
pause >nul
