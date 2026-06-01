@echo off
title AMANE-NEXUS Arret
color 0C

echo.
echo  ============================================================
echo   AMANE-NEXUS - Arret des services
echo  ============================================================
echo.

:: Verifier si Docker est disponible
docker info >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Docker non disponible - arret mode local...
    taskkill /IM python.exe /F >nul 2>&1
    taskkill /IM node.exe /F >nul 2>&1
    taskkill /IM mongod.exe /F >nul 2>&1
    echo  OK - Processus locaux arretes.
    goto :fin
)

:: Arret Docker Compose
echo  [DOCKER] Arret des containers...
cd /d D:\surveillance_project
docker-compose down

if errorlevel 1 (
    echo  [ERREUR] Probleme lors de l'arret. Essai force...
    docker stop amane_nexus_backend amane_nexus_frontend amane_nexus_mongodb amane_nexus_redis >nul 2>&1
)

echo.
echo  Statut final :
docker ps --format "  {{.Names}} -> {{.Status}}"

:fin
echo.
echo  ============================================================
echo   Tous les services AMANE-NEXUS sont arretes.
echo  ============================================================
echo.
timeout /t 2 /nobreak >nul
