@echo off
chcp 65001 >nul
setlocal
title AIMux 桌面端开发
cd /d "%~dp0..\.."

echo 正在启动 Tauri 桌面端...
echo Vite 前端端口：1420
echo Rust 开发后端端口：7790
echo 稳定 Rust 后端端口：7789（本次不会占用）
call npm run dev:desktop

echo.
echo 桌面端开发进程已停止，按任意键关闭窗口。
pause >nul
