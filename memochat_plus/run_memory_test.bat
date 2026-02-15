@echo off
title MemoChat+ Memory Integration Test
setlocal enabledelayedexpansion

:: Set project root
cd /d "%~dp0"

echo.
echo   ==============================================================
echo      MEMOCHAT + MEMORY INTEGRATION TEST (v3.1)
echo   ==============================================================
echo.

:: Check if backend is running
curl -s http://127.0.0.1:8000/health > nul
if %errorlevel% neq 0 (
    echo   [!] Backend not detected. Attempting to start...
    echo   [!] Please wait while the neural core initializes...
    echo.
    :: We try to start the backend if it's not running, but it's safer
    :: to ask the user to use start_all.bat if this fails.
    start /B cmd /c "call backend\venv\Scripts\activate.bat && python -m uvicorn app.main:app --app-dir backend > backend_test.log 2>&1"
    timeout /t 10 /nobreak >nul
)

:: Run the test
if exist "backend\venv\Scripts\python.exe" (
    "backend\venv\Scripts\python.exe" tests/test_memory_integration.py
) else (
    python tests/test_memory_integration.py
)

echo.
echo   ==============================================================
echo      TEST COMPLETE
echo   ==============================================================
echo.
pause
