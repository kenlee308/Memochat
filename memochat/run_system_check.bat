@echo off
title MemoChat Diagnostics
cd /d "%~dp0"

echo.
echo  ==============================================================
echo     MEMOCHAT SYSTEM DIAGNOSTICS
echo  ==============================================================
echo.

echo  [DISK CHECK] Verifying project structure...
set "HEALTHY=1"
if not exist "data" (echo  [FAIL] 'data' directory missing! && set "HEALTHY=0")
if not exist "memory_snapshots" (echo  [FAIL] 'memory_snapshots' directory missing! && set "HEALTHY=0")
if not exist "backend\config.yaml" (echo  [FAIL] Configuration file missing! && set "HEALTHY=0")

if "%HEALTHY%"=="0" (
    echo.
    echo  [ERROR] Critical folders are missing. Please ensure you are running this from the Project Root.
    pause
    exit /b 1
)
echo  [OK] Project structure intact.
echo.

:: Check if backend/venv exists to use correct python environment
if exist "backend\venv\Scripts\python.exe" (
    echo  [SYSTEM] Using Backend Virtual Environment...
    "backend\venv\Scripts\python.exe" system_health_check.py
) else (
    echo  [SYSTEM] Virtual Environment not found. 
    echo  [TIP] Run start_all.bat first to initialize and start the system!
    echo.
    python system_health_check.py
)

echo.
echo  ==============================================================
echo     DIAGNOSTICS COMPLETE
echo  ==============================================================
echo.
pause
