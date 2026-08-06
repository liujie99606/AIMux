@echo off
setlocal
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo STEP1 cd_done
if exist ".venv\Scripts\python.exe" (
    echo STEP2 venv_found
) else (
    echo STEP2 venv_missing
)
echo STEP3 before_app
".venv\Scripts\python.exe" -c "print('PYTHON_OK')"
echo STEP4 after_app
endlocal