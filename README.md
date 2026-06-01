# AMANE-NEXUS

**Système de Surveillance Intelligente Multi-Agent**  
Mohamed Z'GHARI

[![CI/CD](https://github.com/zghari-med/AMANE-NEXUS/actions/workflows/ci.yml/badge.svg)](https://github.com/zghari-med/AMANE-NEXUS/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-47A248?logo=mongodb)](https://mongodb.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-CPU-FF6B6B)](https://ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-58%2F58%20passed-brightgreen)](backend/tests/)
[![License](https://img.shields.io/badge/License-Academic-lightgrey)](LICENSE)

---

## Présentation

AMANE-NEXUS est une plateforme intelligente de surveillance vidéo urbaine qui détecte automatiquement trois classes de comportements anormaux en temps réel grâce à YOLOv8n et des algorithmes heuristiques calibrés sur des datasets réels annotés.

### Performances validées END-TO-END

| Comportement | Algorithme | Précision | Rappel | F1 | Accuracy | AP@0.5 | Dataset |
|---|---|---|---|---|---|---|---|
| Chute | Ratio h/w < 0.65 | 42.9% | **100%** | 0.600 | 60.0% | 0.393 | URFD (70 vidéos) |
| Attroupement | ≥4 personnes, dist <200px | **100%** | 89.7% | **0.946** | 89.7% | **1.000** | People Counting (135 img) |
| Objet abandonné | Immobilité ≥15 frames | 71.0% | 67.3% | 0.691 | 52.9% | 0.586 | Abandoned Bag + P&L (200 img) |
| **Global** | YOLOv8n CPU, IoU ≥ 0.5 | **73.8%** | **76.9%** | **0.753** | **62.8%** | **mAP=0.660** | 517 images + 70 vidéos |

> **Note :** Recall 100% sur les chutes — aucune chute réelle manquée sur 70 vidéos URFD (choix délibéré pour système de sécurité). Précision 100% sur attroupements — zéro fausse alarme.

---

## Architecture Multi-Agent

```
Vidéo Upload / Flux Caméra
        │
        ▼
① Agent Perception    — YOLOv8n (détection 80 classes COCO, 6.2 Mo)
        │                 179.8 ms/frame CPU → 5.6 FPS brut (15.6 FPS effectif)
        ▼
② Agent Tracking      — DeepSORT (suivi trajectoires, Kalman + Hongrois)
        │
        ▼
③ Agent Analyse       — Règles heuristiques calibrées empiriquement
        │                 (chute · attroupement · objet abandonné)
        ▼
④ Agent Décision      — MongoDB + captures JPEG annotées + cooldowns
        │
        ▼
⑤ Agent Interface     — Flask REST API (18 endpoints) + React 18 Dashboard
```

### Paramètres de détection

| Paramètre | Valeur | Rôle |
|---|---|---|
| `FALL_RATIO` | 0.65 | Seuil ratio h/w pour détecter une chute |
| `FALL_COOLDOWN` | 300 frames | Anti-doublon chute |
| `CROWD_MIN` | 5 personnes | Seuil déclenchement attroupement |
| `CROWD_PROXIMITY` | 200 px | Distance max entre personnes |
| `CROWD_COOLDOWN` | 90 frames | Anti-doublon attroupement |
| `STATIONARY_THR` | 22 frames | Immobilité pour objet abandonné |
| `ABANDON_COOLDOWN` | 900 frames | Anti-doublon objet |
| `GRID_SZ` | 100 px | Résolution grille spatiale |
| `FRAME_SKIP` | 3 | Traitement 1 frame/4 (optimisation CPU) |
| `CONFIDENCE` | 0.25 | Seuil confiance YOLO |
| `IOU_THRESHOLD` | 0.5 | Seuil IoU pour validation détection |

---

## Stack Technique

### Backend

| Technologie | Version | Rôle |
|---|---|---|
| Flask | 3.0.0 | API REST — 18 endpoints |
| MongoDB | 6.0 | Stockage analyses, alertes, utilisateurs |
| Redis | 7 | Cache analytics |
| YOLOv8n | 8.1.18 | Détection objets (CPU-only) |
| OpenCV | 4.8.1 | Vision par ordinateur |
| PyJWT | 2.13.0 | Authentification JWT |
| bcrypt | 4.1.2 | Hachage mots de passe |
| Pandas | 2.0+ | Analytics et export CSV |

### Frontend

| Technologie | Version | Rôle |
|---|---|---|
| React | 18.2.0 | Interface utilisateur |
| Tailwind CSS | 3.3.6 | Styles utilitaires |
| Recharts | 2.10.3 | Graphiques et visualisations |
| Zustand | 4.4.1 | Gestion d'état (JWT store) |
| Vite | 5.4.x | Bundler |

### Infrastructure

| Composant | Détail |
|---|---|
| Docker | Multi-stage build (Python 3.10-slim + Node 18-alpine) |
| Docker Compose | Healthchecks sur tous les services |
| CI/CD | GitHub Actions (lint → tests → benchmarks → frontend → docker) |

---

## Démarrage Rapide

### Prérequis

```
Docker Desktop  |  8 Go RAM minimum  |  4 Go disque libre
```

### Option 1 — Docker (recommandé)

```bash
git clone https://github.com/zghari-med/AMANE-NEXUS.git
cd AMANE-NEXUS
docker-compose up -d
```

L'application sera disponible sur **http://localhost:3000**

**Identifiants par défaut :** `admin@surveillance.com` / `admin123`

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
# API : http://localhost:5000

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
# Interface : http://localhost:3000
```

---

## Variables d'Environnement

Créer un fichier `.env` à la racine du projet :

```env
SECRET_KEY=votre_cle_secrete_forte_32_chars_minimum
MONGO_URI=mongodb://localhost:27017/
ANALYTICS_CACHE_TTL=3600
```

---

## API REST — Endpoints

### Authentification

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | Connexion → JWT token |
| POST | `/api/auth/logout` | JWT | Déconnexion (journalisée) |
| GET | `/api/auth/me` | JWT | Profil utilisateur courant |

### Caméras

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/cameras` | JWT | Liste des caméras |
| POST | `/api/cameras` | JWT | Ajouter une caméra |
| DELETE | `/api/cameras/<id>` | JWT | Supprimer une caméra |
| POST | `/api/cameras/<id>/live/start` | JWT | Démarrer flux live |
| POST | `/api/cameras/<id>/live/stop` | JWT | Arrêter flux live |
| GET | `/api/cameras/<id>/live/status` | JWT | Statut du flux live |

### Vidéos & Analyses

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/videos` | JWT | Liste des vidéos uploadées |
| POST | `/api/videos/upload` | JWT | Upload vidéo (mp4/avi/mov) |
| DELETE | `/api/videos/<id>` | JWT | Supprimer une vidéo |
| POST | `/api/analyses/create` | JWT | Lancer une analyse YOLOv8 |
| GET | `/api/analyses/<id>` | JWT | Statut + résultats |
| GET | `/api/analyses/<id>/alerts` | JWT | Alertes avec captures JPEG |
| GET | `/api/analyses/<id>/trends` | JWT | Tendances temporelles |
| GET | `/api/analyses/<id>/metrics-export` | JWT | Export CSV métriques |
| GET | `/api/analyses/statistics` | JWT | Stats globales (`?days=N`) |
| GET | `/api/analyses/benchmarks` | JWT | Métriques YOLOv8n validées |
| GET | `/api/alerts/export` | JWT | Export alertes CSV |

### Administration

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/users` | Admin | Liste des utilisateurs |
| POST | `/api/users` | Admin | Créer un utilisateur |
| PUT | `/api/users/<id>` | Admin | Modifier un utilisateur |
| DELETE | `/api/users/<id>` | Admin | Supprimer un utilisateur |
| GET | `/api/captures/<file>` | JWT | Servir capture annotée |
| GET | `/api/activity-logs` | JWT | Journal d'activité |
| GET | `/api/health` | — | Statut système |

---

## Tests

```bash
cd backend
python -m pytest tests/ -v --cov=.
```

**Résultats : 60/60 tests passés ✅**

### Couverture des tests

| Fichier de test | Tests | Description |
|---|---|---|
| `test_agents.py` | 30 | Algorithmes heuristiques (chute, attroupement, objet) |
| `test_api.py` | 12 | Intégration REST API (auth, caméras, stats) |
| `test_analytics.py` | 5 | Service analytics et tendances |
| `test_benchmarks.py` | 10 | Validation structure et valeurs benchmark_results.json |
| `test_falls.py` | 1 | Validation URFD recall = 100% |

### Résultats agents (données synthétiques)

| Agent | Précision | Rappel | F1 | Accuracy |
|---|---|---|---|---|
| Chute | 1.000 | 0.667 | 0.800 | 0.833 |
| Attroupement | 1.000 | 0.667 | 0.800 | 0.833 |
| Objet abandonné | 1.000 | 0.667 | 0.800 | 0.833 |

> Précision = 1.0 → aucune fausse alarme sur données synthétiques.  
> Rappel = 0.667 → les FN sont intentionnels (cooldown anti-doublon actif).

---

## Structure du Projet

```
AMANE-NEXUS/
├── backend/
│   ├── app_simple.py              # API Flask — 18 endpoints REST
│   ├── worker_analysis.py         # Worker YOLOv8n + DeepSORT + heuristiques
│   ├── requirements.txt
│   ├── data/
│   │   └── benchmark_results.json # Métriques validées END-TO-END
│   ├── services/
│   │   └── analytics_service.py   # BenchmarkLoader + analytics
│   ├── routes/                    # Blueprints Flask
│   ├── captures/                  # Images JPEG annotées (générées)
│   ├── uploads/                   # Vidéos uploadées
│   └── tests/
│       ├── test_agents.py         # 30 tests algorithmes
│       ├── test_api.py            # 12 tests API REST
│       ├── test_analytics.py      # 5 tests analytics
│       ├── test_benchmarks.py     # 10 tests benchmarks
│       └── test_falls.py          # 1 test URFD
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── services/api.js        # Client API centralisé
│   │   ├── context/authStore.js   # Zustand store JWT
│   │   ├── pages/                 # Dashboard, Vidéos, Stats, Benchmarks
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── .github/
│   └── workflows/ci.yml           # Pipeline CI/CD 5 jobs
├── Dockerfile                     # Multi-stage build
├── docker-compose.yml             # 4 services + healthchecks
├── .dockerignore
└── nginx.conf
```

---

## Pipeline CI/CD

Le pipeline GitHub Actions exécute **5 jobs en séquence** à chaque push sur `main` :

```
lint-backend → test-backend → validate-benchmarks → test-frontend → docker-build
                                                                          │
                                                                    pipeline-report
```

| Job | Description | Outil |
|---|---|---|
| `lint-backend` | Vérification style Python | flake8 --max-line-length=120 |
| `test-backend` | Tests unitaires + intégration | pytest + MongoDB service |
| `validate-benchmarks` | F1 ≥ 0.50, Précision ≥ 40% | Python assertions |
| `test-frontend` | Build production React | Vite build |
| `docker-build` | Build image multi-stage | docker/build-push-action |

---

## Auteur

**Mohamed Z'GHARI**

---

*AMANE-NEXUS © 2026 — Système de Surveillance Intelligente Multi-Agent*
