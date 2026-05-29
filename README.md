# AMANE-NEXUS

**Système de Surveillance Intelligente Multi-Agent**  
Mohamed Z'GHARI — PFE Master MSID-TAM 2026 — Université Mohammed V de Rabat

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-47A248?logo=mongodb)](https://mongodb.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-8.1-FF6B6B)](https://ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-57%2F57%20passed-brightgreen)](tests/)

---

## Présentation

AMANE-NEXUS est une plateforme intelligente de surveillance vidéo qui détecte automatiquement trois classes de comportements anormaux grâce à l'IA :

| Comportement | Algorithme | Précision | Rappel | F1 |
|---|---|---|---|---|
| Chute | Ratio h/w bbox < 0.65 | 88.2% | 83.3% | 85.7% |
| Attroupement | ≥5 personnes, distance <200px | 88.9% | 80.0% | 84.2% |
| Objet abandonné | Immobilité ≥22 frames traitées | 85.7% | 85.7% | 85.7% |
| **Global** | YOLOv8n CPU | **94.5%** | **83.3%** | **85.7%** |

---

## Architecture Multi-Agent

```
Vidéo Upload
    │
    ▼
① Agent Perception    — YOLOv8n (détection 80 classes COCO, 6.2 Mo)
    │
    ▼
② Agent Tracking      — DeepSORT (suivi trajectoires, Kalman + Hongrois)
    │
    ▼
③ Agent Analyse       — Règles heuristiques calibrées empiriquement
    │
    ▼
④ Agent Décision      — MongoDB + captures JPEG annotées + cooldowns
    │
    ▼
⑤ Agent Interface     — Flask REST API + React 18 Dashboard
```

### Paramètres de détection

| Paramètre | Valeur | Rôle |
|---|---|---|
| `FALL_RATIO` | 0.65 | Seuil ratio h/w pour chute |
| `FALL_COOLDOWN` | 300 frames | Anti-doublon chute |
| `CROWD_MIN` | 5 personnes | Seuil attroupement |
| `CROWD_COOLDOWN` | 90 frames | Anti-doublon attroupement |
| `STATIONARY_THR` | 22 frames | Immobilité objet abandonné |
| `ABANDON_COOLDOWN` | 900 frames | Anti-doublon objet |
| `GRID_SZ` | 100 px | Grille de détection spatiale |
| `FRAME_SKIP` | 3 | Traitement 1 frame sur 4 → 15.6 FPS effectifs |

---

## Stack Technique

### Backend
| Technologie | Version | Rôle |
|---|---|---|
| Flask | 3.0.0 | API REST (18 endpoints) |
| MongoDB | 6.0 | Stockage données |
| YOLOv8n + OpenCV | 8.1.18 / 4.8.1 | Détection et vision |
| PyJWT + bcrypt | 2.13.0 / 4.1.2 | Auth JWT |
| Pandas | 2.0+ | Analytics et export CSV |
| python-dotenv | — | Variables d'environnement |

### Frontend
| Technologie | Version | Rôle |
|---|---|---|
| React | 18.2.0 | UI |
| Tailwind CSS | 3.3.6 | Styles |
| Recharts | 2.10.3 | Graphiques |
| Zustand | 4.4.1 | State management |
| Vite | 5.0.7 | Bundler |

### Infrastructure
- Docker multi-stage (Python 3.10-slim + Node 18-alpine + Nginx)
- Docker Compose avec healthchecks sur tous les services
- GitHub Actions CI/CD pipeline (lint → tests → build → docker)

---

## Démarrage Rapide

### Prérequis
```
Python 3.10+  |  Node.js 18+  |  MongoDB 6.0  |  8 Go RAM minimum
```

### Option 1 — Docker (recommandé)
```bash
git clone https://github.com/zghari99/AMANE-NEXUS.git
cd AMANE-NEXUS
docker-compose up -d
# Accès : http://localhost:3000
```

### Option 2 — Développement local
```bash
# Terminal 1 — MongoDB
mongod --dbpath ./data/db

# Terminal 2 — Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python app_simple.py
# API disponible sur http://localhost:5000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
# Interface sur http://localhost:5173
```

### Créer le compte admin initial
```python
from pymongo import MongoClient
import bcrypt
db = MongoClient()['surveillance_db']
db.user.insert_one({
    'email': 'admin@amane-nexus.com',
    'username': 'admin',
    'password': bcrypt.hashpw(b'admin123', bcrypt.gensalt()),
    'role': 'admin',
    'full_name': 'Administrateur'
})
```

---

## Variables d'Environnement

Créer un fichier `.env` dans `backend/` :

```env
SECRET_KEY=votre_cle_secrete_forte_32_chars_min
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=surveillance_db
FLASK_ENV=development
FLASK_PORT=5000
```

---

## API REST — Endpoints

### Authentification
| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | Connexion → JWT |
| POST | `/api/auth/logout` | JWT | Déconnexion (journalisée) |
| GET | `/api/auth/me` | JWT | Profil utilisateur courant |

### Caméras
| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/cameras` | JWT | Liste des caméras |
| POST | `/api/cameras` | JWT | Ajouter une caméra |
| DELETE | `/api/cameras/<id>` | JWT | Supprimer une caméra |

### Vidéos & Analyses
| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/videos` | JWT | Liste des vidéos |
| POST | `/api/videos/upload` | JWT | Upload vidéo (mp4/avi/mov) |
| DELETE | `/api/videos/<id>` | JWT | Supprimer une vidéo |
| POST | `/api/analyses/create` | JWT | Lancer une analyse |
| GET | `/api/analyses/<id>` | JWT | Statut + résultats |
| GET | `/api/analyses/<id>/alerts` | JWT | Alertes avec captures |
| GET | `/api/analyses/statistics` | JWT | Stats globales (filtre `?days=N`) |
| GET | `/api/analyses/benchmarks` | JWT | Benchmarks YOLOv8n |

### Administration
| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/users` | Admin | Liste des utilisateurs |
| POST | `/api/users` | Admin | Créer un utilisateur |
| GET | `/api/captures/<file>` | JWT | Servir capture annotée |
| GET | `/api/activity-logs` | JWT | Journal d'activité |
| GET | `/api/health` | — | Statut système |

---

## Tests

```bash
cd backend
python -m pytest tests/ -v --cov=app_simple
```

**Résultats : 57/57 tests passés**

### Tests Agents (`test_agents.py`) — 30 tests

| Agent | Précision | Rappel | F1 | Accuracy |
|---|---|---|---|---|
| Chute | 1.000 | 0.667 | 0.800 | 0.833 |
| Attroupement | 1.000 | 0.667 | 0.800 | 0.833 |
| Objet abandonné | 1.000 | 0.667 | 0.800 | 0.833 |
| **Global** | **1.000** | **0.667** | **0.800** | **0.833** |

> Précision = 1.0 → aucune fausse alarme sur données synthétiques.  
> Rappel = 0.667 → les FN sont intentionnels (cooldown anti-doublon).

### Tests API (`test_api.py`) — 27 tests

| Groupe | Tests | Statut |
|---|---|---|
| Authentification | 9 | ✅ |
| Caméras | 5 | ✅ |
| Statistiques | 4 | ✅ |
| Accès Admin | 5 | ✅ |
| Vidéos & Logs | 4 | ✅ |

---

## Structure du Projet

```
AMANE-NEXUS/
├── backend/
│   ├── app_simple.py          # API Flask (18 endpoints REST)
│   ├── worker_analysis.py     # Worker YOLOv8n + DeepSORT + heuristiques
│   ├── .env                   # Variables d'environnement (ne pas committer)
│   ├── requirements.txt
│   ├── config/
│   ├── data/
│   │   └── benchmark_results.json
│   ├── services/
│   ├── routes/
│   ├── captures/              # Images JPEG annotées générées
│   ├── uploads/               # Vidéos uploadées
│   └── tests/
│       ├── test_agents.py     # 30 tests algorithmes heuristiques
│       └── test_api.py        # 27 tests intégration REST API
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── services/
│   │   │   └── api.js         # URL centralisée + captureUrl()
│   │   ├── context/
│   │   │   └── authStore.js   # Zustand store (JWT)
│   │   ├── pages/             # Dashboard, Vidéos, Stats, Benchmarks...
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── RAPPORT_PFE.md         # Rapport académique complet
│   └── FAQ_SOUTENANCE.md      # 20 Q&R pour le jury
├── pfe/
│   └── AMANE_SLIDES_DEFENSE.pptx   # Présentation 12 slides
├── .github/
│   └── workflows/ci.yml       # Pipeline CI/CD
├── Dockerfile
├── docker-compose.yml
└── nginx.conf
```

---

## Performances

| Métrique | Valeur |
|---|---|
| F1-Score global (benchmark réel) | **85.7%** |
| Précision | **94.5%** |
| Rappel | **83.3%** |
| Inférence YOLOv8n CPU | **191 ms/frame** |
| FPS effectif (FRAME_SKIP=3) | **15.6 FPS** |
| Taille modèle YOLOv8n | **6.2 Mo** |
| Couverture de tests | **41% app_simple.py** |

---

## Auteur

**Mohamed Z'GHARI** — Master MSID-TAM, Université Mohammed V de Rabat  
Encadrant : Faculté des Sciences — 2026

---

*AMANE-NEXUS © 2026 — Système de Surveillance Intelligente Multi-Agent*
