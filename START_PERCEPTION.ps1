# Script de demarrage Agent Perception
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
cd D:\surveillance_project
& .\venv\Scripts\Activate.ps1
cd agents
python agent_perception.py
