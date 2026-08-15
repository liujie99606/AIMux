@echo off
chcp 65001 >nul
setlocal
title AIMux 编译并启动稳定 Rust 网关
cd /d "%~dp0..\..\src-tauri"

set "AIMUX_PORT=7789"
set "AIMUX_MONITORING_ENABLED="
set "CARGO_INCREMENTAL=1"
set "CARGO_BUILD_JOBS=%NUMBER_OF_PROCESSORS%"
if "%CARGO_BUILD_JOBS%"=="" set "CARGO_BUILD_JOBS=1"

echo 正在编译最新 Rust 代码...
echo 使用 %CARGO_BUILD_JOBS% 个并行编译任务，启用增量编译...
call cargo build --bin aimux-gateway --jobs %CARGO_BUILD_JOBS%
if errorlevel 1 (
    echo.
    echo 编译失败，请查看上方 Cargo 错误信息。
    echo 如果提示拒绝访问或 exe 被占用，请先关闭正在运行的 7789 网关后再重试。
    pause
    exit /b 1
)

echo.
echo 编译完成，启动稳定 Rust 网关，端口 7789...
target\debug\aimux-gateway.exe

echo.
echo 稳定 Rust 网关已停止，按任意键关闭窗口。
pause >nul
