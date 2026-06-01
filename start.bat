@echo off
setlocal enabledelayedexpansion
title AMANE-NEXUS Demarrage
color 0A

echo.
echo  ============================================================
echo   AMANE-NEXUS - Systeme de Surveillance Intelligente
echo   PFE Master MSID-TAM 2026
echo  ============================================================
echo.

:: Create MongoDB directory
if not exist "D:\surveillance_project\backend\data\db" (
    mkdir "D:\surveillance_project\backend\data\db"
    echo  [SETUP] MongoDB directory created
)

:: Install Python dependencies
echo  [1/5] Installing Python dependencies...
D:\surveillance_project\venv\Scripts\pip.exe install -q -r D:\surveillance_project\backend\requirements.txt >nul 2>&1
if errorlevel 1 (
    echo       WARNING: Could not install Python dependencies
) else (
    echo       OK
)

:: Install Node dependencies
echo  [2/5] Installing Node.js dependencies...
if not exist "D:\surveillance_project\frontend\node_modules" (
    cd /d D:\surveillance_project\frontend
    call npm install --silent >nul 2>&1
    if errorlevel 1 (
        echo       WARNING: npm install failed
    ) else (
        echo       OK
    )
) else (
    echo       OK (already installed)
)

:: Start MongoDB
echo  [3/5] Starting MongoDB...
start "MongoDB" /min cmd /k "mongod --dbpath D:\surveillance_project\backend\data\db --quiet"
timeout /t 3 /nobreak >nul
echo       OK

:: Start Flask Backend
echo  [4/5] Starting Flask Backend...
start "AMANE-Backend" /min cmd /k "cd /d D:\surveillance_project\backend && D:\surveillance_project\venv\Scripts\python.exe app_simple.py"
timeout /t 4 /nobreak >nul
echo       OK

:: Start React Frontend
echo  [5/5] Starting React Frontend...
start "AMANE-Frontend" /min cmd /k "cd /d D:\surveillance_project\frontend && npm run dev"
timeout /t 5 /nobreak >nul
echo       OK

echo.
echo  ============================================================
echo   Application running!
echo.
echo   Frontend    : http://localhost:3000
echo   API         : http://localhost:5000/api/health
echo   MongoDB     : localhost:27017
echo.
echo   Default Login:
echo   Email       : admin@surveillance.com
echo   Password    : admin123
echo  ============================================================
echo.

start "" "http://localhost:3000"

pause
