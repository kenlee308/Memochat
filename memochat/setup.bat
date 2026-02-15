@echo off
setlocal
title MemoChat Setup

echo.
echo  ==============================================================
2: echo     MEMOCHAT FIRST-TIME SETUP
3: echo  ==============================================================
echo.

:: 1. Check Python
echo [1/4] Verifying Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)
echo [OK] Python found.

:: 2. Backend Setup
echo [2/4] Setting up Backend Virtual Environment...
if not exist "backend\venv" (
    python -m venv backend\venv
    echo [OK] Virtual environment created.
) else (
    echo [SKIP] Virtual environment already exists.
)

echo [DEBUG] Installing backend dependencies...
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)
echo [OK] Backend dependencies installed.

:: 3. Frontend Setup
echo [3/4] Installing Frontend dependencies (Node.js)...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js and npm.
    pause
    exit /b 1
)

cd frontend
echo [DEBUG] Running npm install...
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed.
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Frontend dependencies installed.

:: 4. Marker Creation
echo [4/4] Finalizing setup...
echo SETUP_COMPLETED_ON_%DATE%_%TIME% > .setup_done
echo [OK] Setup marker created.

echo.
echo  ==============================================================
echo     SETUP COMPLETE! You can now run start_all.bat
echo  ==============================================================
echo.
pause
exit /b 0
