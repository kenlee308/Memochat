@echo off
setlocal
title MemoChat Console

:: Set project root
cd /d "%~dp0"

echo.
echo  ==============================================================
echo     MEMOCHAT SYSTEM LAUNCHER
echo  ==============================================================
echo.

:: 0. First-Time Setup Check
if not exist ".setup_done" (
    echo [SYSTEM] First-time run detected. Triggering setup...
    call setup.bat
    if not exist ".setup_done" (
        echo [ERROR] Setup was not completed. Aborting launch.
        pause
        exit /b 1
    )
)

:: 1. Backend Start (Background Mode)
echo  [SYSTEM] Initializing Backend Neural Core (Background)...
echo  ----------
:: We start the backend in a hidden background process, redirecting logs to a file.
start /B cmd /c "call backend\venv\Scripts\activate.bat && python -m uvicorn app.main:app --app-dir backend --reload --port 8000 > backend_debug.log 2>&1"

:: Wait a moment for virtual environment to kick in
timeout /t 4 /nobreak >nul

:: 2. Frontend Start (Interactive Mode)
echo.
echo  [SYSTEM] Initializing Frontend Interface...
echo  ----------
echo   - The Backend is running silently in the background.
echo   - Use the UI Log Monitor to see backend activity.
echo   - This window is now your Vite Controller.
echo.
echo     Press 'q' + Enter inside this window to stop the frontend.
echo     This will automatically trigger a full system shutdown.
echo.
echo  ==============================================================

:: Change to frontend dir and run Vite directly in this window
cd frontend
call npm run dev

:: 3. Shutdown Sequence (Triggered when Vite exits)
echo.
echo  [SYSTEM] Frontend exited. Initiating Shutdown Sequence...
cd ..
call stop_all.bat

exit
