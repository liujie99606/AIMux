@echo off
chcp 65001 >nul
setlocal
title AIMux 前端开发服务
cd /d "%~dp0..\.."

set "VITE_API_BASE="
echo 正在启动 Vite 前端，端口 1420...
echo 当前连接 Rust 稳定后端，端口 7789...
call npm run dev

echo.
echo 前端开发服务已停止，按任意键关闭窗口。
pause >nul
