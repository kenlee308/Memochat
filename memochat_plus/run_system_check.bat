@echo off
title MemoChat+ Diagnostics
setlocal enabledelayedexpansion

:: Set project root
cd /d "%~dp0"

echo.
echo  [94m==============================================================[0m
echo  [94m   MEMOCHAT + SYSTEM DIAGNOSTICS (v3.1)[0m
echo  [94m==============================================================[0m
echo.

:: 1. Environment Check
echo  [1/2] Checking Local Environment...

set "MISSING_DEPS=0"

:: Check for Ollama
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo  [91m[FAIL] Ollama not found in PATH![0m
    set "MISSING_DEPS=1"
) else (
    echo  [92m[OK] Ollama is installed.[0m
)

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  [91m[FAIL] Python not found in PATH![0m
    set "MISSING_DEPS=1"
) else (
    echo  [92m[OK] Python is installed.[0m
)

:: Check for Node
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo  [91m[FAIL] Node.js/NPM not found in PATH![0m
    set "MISSING_DEPS=1"
) else (
    echo  [92m[OK] Node.js is installed.[0m
)

if "!MISSING_DEPS!"=="1" (
    echo.
    echo  [91m[ERROR] Missing core dependencies. Please install Ollama, Python, and Node.js.[0m
    pause
    exit /b 1
)

echo.
:: 2. Neural & Memory Check (Python Logic)
echo  [2/2] Running Deep System Probe...

if exist "backend\venv\Scripts\python.exe" (
    "backend\venv\Scripts\python.exe" system_health_check.py
) else (
    echo  [!] Virtual environment missing. Falling back to system Python...
    python system_health_check.py
)

echo.
echo  [94m==============================================================[0m
echo     DIAGNOSTICS COMPLETE
echo  [94m==============================================================[0m
echo.
pause
