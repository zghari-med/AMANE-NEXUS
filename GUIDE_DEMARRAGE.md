# 🚀 Guide de Démarrage Rapide

Ce guide vous permettra de démarrer la plateforme de surveillance en quelques minutes.

## ⚡ Prérequis Installés

Assurez-vous d'avoir les éléments suivants installés :

- **Python 3.10+** 
- **Node.js 18+** (npm)
- **MongoDB 6+** (en cours d'exécution)
- **Redis 6+** (en cours d'exécution)

### Vérification

```bash
# Python
python --version

# Node.js
node --version
npm --version

# MongoDB
mongosh --version

# Redis
redis-cli --version
```

## 📋 Étapes d'Installation

### 1️⃣ Configuration de l'Environnement

Vérifiez que le fichier `.env` existe avec :

```env
SECRET_KEY=pfe_surveillance_2026
MONGO_URI=mongodb://localhost:27017/surveillance_db
REDIS_HOST=localhost
REDIS_PORT=6379
FLASK_ENV=development
```

### 2️⃣ Installation Backend

```bash
# Se placer dans le dossier backend
cd backend

# Créer et activer l'environnement virtuel
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3️⃣ Installation Frontend

```bash
# Se placer dans le dossier frontend
cd frontend

# Installer les dépendances
npm install
```

## 🎬 Démarrage de la Plateforme

### Ouvrir 6 Terminaux

#### Terminal 1 : Agent Perception (YOLOv8n)
```bash
cd backend
source venv/Scripts/activate  # Windows: venv\Scripts\activate
python agents/agent_perception.py
```

**Sortie attendue :**
```
2026-05-28 10:00:00 [AgentPerception] INFO — Chargement YOLOv8n (CPU, imgsz=640)…
2026-05-28 10:00:05 [AgentPerception] INFO — Modèle YOLOv8n prêt (device=cpu).
2026-05-28 10:00:05 [AgentPerception] INFO — Connecté à Redis ✓
2026-05-28 10:00:05 [AgentPerception] INFO — Agent Perception en écoute sur channel:detections
```

#### Terminal 2 : Agent Tracking (DeepSORT)
```bash
cd backend
source venv/Scripts/activate
python agents/agent_tracking.py
```

**Sortie attendue :**
```
2026-05-28 10:00:00 [AgentTracking] INFO — Connecté à Redis ✓
2026-05-28 10:00:00 [AgentTracking] INFO — Initialisation DeepSORT…
2026-05-28 10:00:01 [AgentTracking] INFO — DeepSORT prêt.
2026-05-28 10:00:01 [AgentTracking] INFO — Agent Tracking en écoute sur channel:detections
```

#### Terminal 3 : Agent Analyse
```bash
cd backend
source venv/Scripts/activate
python agents/agent_analysis.py
```

**Sortie attendue :**
```
2026-05-28 10:00:00 [AgentAnalysis] INFO — Connecté à Redis ✓
2026-05-28 10:00:01 [AgentAnalysis] INFO — Agent Analyse en écoute sur channel:tracks
```

#### Terminal 4 : Agent Décision
```bash
cd backend
source venv/Scripts/activate
python agents/agent_decision.py
```

**Sortie attendue :**
```
2026-05-28 10:00:00 [AgentDecision] INFO — Connecté à Redis ✓
2026-05-28 10:00:01 [AgentDecision] INFO — Agent Décision en écoute sur channel:analysis
```

#### Terminal 5 : API Flask
```bash
cd backend
source venv/Scripts/activate
python app.py
```

**Sortie attendue :**
```
2026-05-28 10:00:00 [app] INFO — ✓ MongoDB connecté
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

#### Terminal 6 : Frontend React
```bash
cd frontend
npm run dev
```

**Sortie attendue :**
```
  VITE v5.0.7  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  press h to show help
```

## ✅ Vérification du Démarrage

### Santé de l'Application

1. **Frontend** : Ouvrir http://localhost:3000
2. **API** : Ouvrir http://localhost:5000/api/health
3. **Agents** : Vérifier les logs dans chaque terminal

### Vérifier la Connexion Redis

```bash
redis-cli
> PING
PONG  ✓

> SUBSCRIBE channel:detections
# Devrait afficher les messages en direct
```

## 🔐 Premier Login

### Credentials par Défaut

Créer un premier utilisateur via l'API :

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@surveillance.com",
    "password": "admin123",
    "username": "admin",
    "full_name": "Administrateur"
  }'
```

Ensuite, se connecter à http://localhost:3000 avec :
- Email: `admin@surveillance.com`
- Mot de passe: `admin123`

## 📹 Test Rapide

### 1. Uploader une Vidéo

1. Aller à http://localhost:3000/
2. Cliquer sur "Upload Vidéo"
3. Sélectionner un fichier vidéo (.mp4, .avi, etc.)

### 2. Lancer une Analyse

1. Cliquer sur la vidéo uploadée
2. Cliquer sur le bouton "Analyser"
3. L'analyse commencera et vous verrez la progression

### 3. Consulter les Résultats

1. Attendre la fin de l'analyse
2. Cliquer sur "Voir les résultats"
3. Consulter les événements détectés (chutes, attroupements, objets abandonnés)

### 4. Exporter les Données

1. Sur la page d'analyse, cliquer sur "Export"
2. Choisir le format (CSV, JSON, PDF)
3. Le fichier sera téléchargé

## 🛠️ Dépannage

### Agent Perception échoue

```bash
# Vérifier que yolov8n.pt existe
ls -la backend/yolov8n.pt

# Sinon, il sera téléchargé automatiquement (première exécution)
# Vérifier qu'on a assez d'espace disque (~200 MB)
```

### Erreur de connexion MongoDB

```bash
# Vérifier que MongoDB est en cours d'exécution
mongosh

# Si erreur de connexion
# Ouvrir un terminal séparé et démarrer MongoDB
mongod

# Vérifier MONGO_URI dans .env
MONGO_URI=mongodb://localhost:27017/surveillance_db
```

### Erreur de connexion Redis

```bash
# Vérifier que Redis est en cours d'exécution
redis-cli ping
# Doit retourner: PONG

# Si erreur, démarrer Redis
redis-server
```

### Le frontend ne se connecte pas

```bash
# Vérifier que Flask tourne sur http://localhost:5000
curl http://localhost:5000/api/health

# Vérifier les logs Flask pour les erreurs CORS
# Vérifier que le token JWT est valide
```

## 📊 Accès aux Dashboards

- **Admin** : http://localhost:3000/ (si rôle = admin)
- **User** : http://localhost:3000/ (si rôle = user)
- **API Docs** : http://localhost:5000/api

## 🎯 Prochaines Étapes

1. **Tester avec des vidéos réelles** - Uploader vos propres vidéos
2. **Configurer les seuils** - Modifier les paramètres d'analyse dans `agents/agent_analysis.py`
3. **Intégrer les caméras IP** - Connecter à des flux RTSP en direct
4. **Déployer en production** - Voir les instructions de déploiement
5. **Intégrer des notifications** - Email, SMS, Webhooks

## 📞 Support

Pour toute question :
1. Vérifier les logs de chaque agent
2. Consulter le README.md principal
3. Vérifier les variables d'environnement dans .env

---

**🎉 Vous êtes prêt ! Lancez les 6 terminaux et commencez à analyser des vidéos !**

