@echo off
setlocal enabledelayedexpansion
title AMANE-NEXUS Demarrage
color 0A

echo.
echo  ============================================================
echo   AMANE-NEXUS - Systeme de Surveillance Intelligente
echo   Mohamed Z'GHARI - 2026
echo  ============================================================
echo.

:: Verifier si Docker Desktop est disponible
docker info >nul 2>&1
if errorlevel 1 (
    echo  [DOCKER] Docker Desktop non disponible.
    echo  [DOCKER] Lance Docker Desktop et reessaie.
    echo  [DOCKER] Ou utilise start_local.bat pour le mode local.
    echo.
    pause
    exit /b 1
)

echo  [DOCKER] Docker Desktop detecte.
echo.

:: Lancer avec Docker Compose
echo  [1/2] Demarrage des services Docker...
cd /d D:\surveillance_project
docker-compose up -d

if errorlevel 1 (
    echo.
    echo  [ERREUR] docker-compose up a echoue.
    echo  Verifie les logs : docker-compose logs
    pause
    exit /b 1
)

echo.
echo  [2/2] Verification des services...
timeout /t 10 /nobreak >nul

:: Verifier backend
curl -s -o nul -w "%%{http_code}" http://localhost:5000/api/health 2>nul | findstr "200" >nul
if errorlevel 1 (
    echo  [ATTENTE] Backend demarre... patience 15s
    timeout /t 15 /nobreak >nul
)

echo.
echo  ============================================================
echo   Application AMANE-NEXUS en cours d'execution !
echo.
echo   Frontend    : http://localhost:3000
echo   API         : http://localhost:5000/api/health
echo   MongoDB     : localhost:27017
echo   Redis       : localhost:6379
echo.
echo   Login par defaut :
echo   Email       : admin@surveillance.com
echo   Mot de passe: admin123
echo.
echo   Pour arreter : stop.bat  ou  docker-compose down
echo  ============================================================
echo.

:: Ouvrir navigateur
start "" "http://localhost:3000"

echo  Appuie sur une touche pour fermer cette fenetre...
pause >nul
