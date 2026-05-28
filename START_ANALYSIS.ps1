# Script de demarrage Agent Analyse
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
cd D:\surveillance_project
& .\venv\Scripts\Activate.ps1
cd agents
python agent_analysis.py
