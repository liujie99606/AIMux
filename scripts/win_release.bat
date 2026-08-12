@echo off
setlocal EnableExtensions

REM AIMux Windows release entry: build onedir, then create one setup EXE.

cd /d "%~dp0\.."

echo [%time:~0,8%] [AIMux] Checking Inno Setup ...
".venv\Scripts\python.exe" scripts\release_installer.py --check-only
if errorlevel 1 (
    echo [AIMux] Release stopped: install Inno Setup 6 first.
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] Stage 1/3: building Windows app ...
call "%~dp0win_build.bat" --clean
if errorlevel 1 (
    echo [AIMux] Release stopped: application build failed.
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] Stage 2/3: creating setup EXE ...
".venv\Scripts\python.exe" scripts\release_installer.py
if errorlevel 1 (
    echo [AIMux] Release stopped: setup creation failed. See the log above.
    pause
    exit /b 1
)

echo [%time:~0,8%] [AIMux] Stage 3/3: release completed.
echo [AIMux] User data remains in %%APPDATA%%\aimux during upgrades.
echo.
pause
endlocal
