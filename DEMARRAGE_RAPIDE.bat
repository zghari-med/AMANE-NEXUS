@echo off
REM Script de demarrage rapide de la plateforme de surveillance

setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║           PLATEFORME DE SURVEILLANCE INTELLIGENTE - DEMARRAGE           ║
echo ║                                                                          ║
echo ║              Suivez les instructions ci-dessous attentivement           ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM Vérifier les prérequis
echo [VERIFICATION DES PREREQUIS]
echo.

echo Vérification de MongoDB...
mongosh --version >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] MongoDB installé
) else (
    echo   [ERROR] MongoDB non trouvé - veuillez l'installer
    pause
    exit /b 1
)

echo Vérification de Redis...
redis-cli ping >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] Redis en cours d'exécution
) else (
    echo   [WARNING] Redis ne répond pas - assurez-vous qu'il est lancé
    echo            Commande: redis-server
)

echo Vérification de Python...
python --version >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] Python disponible
) else (
    echo   [ERROR] Python non trouvé
    pause
    exit /b 1
)

echo Vérification de Node.js...
node --version >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK] Node.js disponible
) else (
    echo   [ERROR] Node.js non trouvé
    pause
    exit /b 1
)

echo.
echo [INSTALLATION DES DEPENDANCES]
echo.

REM Backend
echo Installation des dependances Python...
cd backend
python -m venv venv >nul 2>&1
call venv\Scripts\activate.bat
pip install -q Flask flask-cors python-dotenv mongoengine redis bcrypt PyJWT requests 2>nul

echo   [OK] Dependances Python installees
cd ..

REM Frontend
echo Installation des dependances Node.js...
cd frontend
if not exist node_modules (
    call npm install -q 2>nul
    echo   [OK] Dependances Node.js installees
) else (
    echo   [OK] Dependances Node.js deja installees
)
cd ..

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                    INSTRUCTIONS DE DEMARRAGE                             ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

echo Ouvrez 6 terminaux PowerShell dans le dossier du projet:
echo.

echo [Terminal 1] Agent Perception (YOLOv8n)
echo   $ cd backend
echo   $ .\venv\Scripts\Activate.ps1
echo   $ python agents\agent_perception.py
echo.

echo [Terminal 2] Agent Tracking (DeepSORT)
echo   $ cd backend
echo   $ .\venv\Scripts\Activate.ps1
echo   $ python agents\agent_tracking.py
echo.

echo [Terminal 3] Agent Analyse
echo   $ cd backend
echo   $ .\venv\Scripts\Activate.ps1
echo   $ python agents\agent_analysis.py
echo.

echo [Terminal 4] Agent Décision
echo   $ cd backend
echo   $ .\venv\Scripts\Activate.ps1
echo   $ python agents\agent_decision.py
echo.

echo [Terminal 5] API Flask
echo   $ cd backend
echo   $ .\venv\Scripts\Activate.ps1
echo   $ python app.py
echo   Accessible sur: http://localhost:5000/api/health
echo.

echo [Terminal 6] Frontend React
echo   $ cd frontend
echo   $ npm run dev
echo   Accessible sur: http://localhost:3000
echo.

echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                  PREMIERE UTILISATION                                    ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

echo 1. Ouvrir http://localhost:3000 dans votre navigateur
echo 2. Créer un compte (Register)
echo 3. Se connecter avec vos identifiants
echo 4. Uploader une vidéo test
echo 5. Cliquer sur "Analyser"
echo 6. Consulter les résultats
echo.

echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                        DOCUMENTATION                                     ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

echo - Guide de demarrage detaille: GUIDE_DEMARRAGE.md
echo - Architecture système: ARCHITECTURE.md
echo - Checklist dépannage: CHECKLIST_DEPLOIEMENT.md
echo.

echo Prêt à démarrer ? Ouvrez les 6 terminaux et lancez les commandes ci-dessus !
echo.
pause
