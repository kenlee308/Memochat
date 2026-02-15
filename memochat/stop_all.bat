@echo off
setlocal
title MemoChat Terminator

echo.
echo  ==============================================================
echo     🛑 SHUTTING DOWN MEMOCHAT ECOSYSTEM 🛑
echo  ==============================================================
echo.

:: 1. Targeted Window Closure
echo  [1/3] Closing Neural Core and UI Windows...
taskkill /FI "WINDOWTITLE eq MemoChat Backend Core" /F /T 2>nul
taskkill /FI "WINDOWTITLE eq MemoChat Frontend UI" /F /T 2>nul
taskkill /FI "WINDOWTITLE eq MemoChat Controller" /F /T 2>nul
taskkill /FI "WINDOWTITLE eq MemoChat App Controller" /F /T 2>nul
echo  [OK] Console windows signaled.

:: 2. Process Cleanup
echo.
echo  [2/3] Terminating underlying sub-processes...
taskkill /F /IM python.exe /T 2>nul >nul
taskkill /F /IM node.exe /T 2>nul >nul
echo  [OK] Binary processes cleared.

:: 3. Port Cleanup (Defensive)
echo.
echo  [3/3] Reclaiming network ports (8000, 5173)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul >nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul >nul
echo  [OK] Ports reset.

echo.
echo  ==============================================================
echo     ✨ ALL SERVICES TERMINATED
echo  ==============================================================
echo.
:: Exit with /B to close the script, then the process
exit
