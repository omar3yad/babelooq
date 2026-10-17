@echo off
setlocal
title Garage4U POS Server
cd /d "%~dp0"

echo ========================================================
echo   Starting Garage4U Parking System
echo ========================================================

echo [1/3] Checking and freeing port 8000...
powershell -NoProfile -Command "Get-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1

echo [2/3] Setting environment variables...
set "PYTHONPATH=%CD%;%CD%\venv\Lib\site-packages"

echo [3/3] Launching server on http://localhost:8000 ...
echo ========================================================
echo   System is READY at: http://localhost:8000/ui/login
echo   DO NOT close this window while using the application.
echo ========================================================

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe server.py
) else (
    python server.py
)

pause


