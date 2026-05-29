@echo off
title AMANE-NEXUS — Démarrage
color 0A

echo.
echo  ============================================================
echo   AMANE-NEXUS — Système de Surveillance Intelligente
echo   PFE Master MSID-TAM 2026
echo  ============================================================
echo.

:: ── 1. MongoDB ────────────────────────────────────────────────
echo  [1/3] Démarrage de MongoDB...
net start MongoDB >nul 2>&1
if errorlevel 1 (
    echo       MongoDB service absent — tentative directe...
    start "MongoDB" /min mongod --dbpath "C:\data\db" --quiet
    timeout /t 2 /nobreak >nul
)
echo       OK

:: ── 2. Backend Flask ──────────────────────────────────────────
echo  [2/3] Démarrage du backend Flask (port 5000)...
start "AMANE Backend" /min cmd /c ^
    "cd /d D:\surveillance_project\backend && ^
     venv\Scripts\python.exe app_simple.py"
timeout /t 3 /nobreak >nul
echo       OK

:: ── 3. Frontend Vite ─────────────────────────────────────────
echo  [3/3] Démarrage du frontend Vite (port 3000)...
start "AMANE Frontend" /min cmd /c ^
    "cd /d D:\surveillance_project\frontend && ^
     npm run dev"
timeout /t 5 /nobreak >nul
echo       OK

echo.
echo  ============================================================
echo   Application prête !
echo   Ouvrir :  http://localhost:3000
echo   API     :  http://localhost:5000/api/health
echo  ============================================================
echo.

:: Ouvrir automatiquement le navigateur
start "" "http://localhost:3000"

echo  Appuyez sur une touche pour fermer ce terminal...
echo  (Les serveurs continuent de tourner en arrière-plan)
pause >nul
