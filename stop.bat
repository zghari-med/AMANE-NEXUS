@echo off
title AMANE-NEXUS — Arrêt
color 0C

echo.
echo  ============================================================
echo   AMANE-NEXUS — Arrêt des serveurs
echo  ============================================================
echo.

echo  Arrêt du backend Flask...
taskkill /FI "WINDOWTITLE eq AMANE Backend*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
echo  OK

echo  Arrêt du frontend Vite...
taskkill /FI "WINDOWTITLE eq AMANE Frontend*" /F >nul 2>&1
echo  OK

echo.
echo  Tous les serveurs sont arrêtés.
timeout /t 2 /nobreak >nul
