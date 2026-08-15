@echo off
chcp 65001 >nul
setlocal
title AIMux Rust 开发后端
cd /d "%~dp0..\.."

echo 正在启动 Rust 开发后端，端口 7790...
call npm run dev:gateway

echo.
echo Rust 开发后端已停止，按任意键关闭窗口。
pause >nul
