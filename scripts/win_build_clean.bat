@echo off
setlocal
chcp 65001 >nul 2>&1

REM AIMux Windows 全量打包入口：适合双击运行，实际流程复用 win_build.bat。

call "%~dp0win_build.bat" --clean
set "AIMUX_BUILD_EXIT_CODE=%errorlevel%"
endlocal & exit /b %AIMUX_BUILD_EXIT_CODE%
