@echo off
chcp 65001 >nul
setlocal
title AIMux Rust 开发后端
cd /d "%~dp0..\.."

for /f %%P in ('node scripts\runtime-ports.mjs development backend') do set "DEV_BACKEND_PORT=%%P"
if not defined DEV_BACKEND_PORT (
    echo 无法读取开发后端端口配置。
    pause
    exit /b 1
)

echo 正在启动 Rust 开发后端，端口 %DEV_BACKEND_PORT%...
call npm run dev:gateway

echo.
echo Rust 开发后端已停止，按任意键关闭窗口。
pause >nul
