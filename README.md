# AMANE-NEXUS

**Système de Surveillance Intelligente Multi-Agent**  
Mohamed Z'GHARI

[![CI/CD GitHub](https://github.com/zghari-med/AMANE-NEXUS/actions/workflows/ci.yml/badge.svg)](https://github.com/zghari-med/AMANE-NEXUS/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-47A248?logo=mongodb)](https://mongodb.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-CPU-FF6B6B)](https://ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://docker.com)
[![OWASP](https://img.shields.io/badge/OWASP%20Top%2010-10%2F10%20couvert-16a34a)](scripts/generate_owasp_report.py)
[![Tests](https://img.shields.io/badge/Tests-60%2F60%20passed-brightgreen)](backend/tests/)

---

## Présentation

AMANE-NEXUS est une plateforme intelligente de surveillance vidéo urbaine qui détecte automatiquement trois classes de comportements anormaux en temps réel grâce à YOLOv8n et des algorithmes heuristiques calibrés sur des datasets réels annotés.

### Performances validées END-TO-END

| Comportement | Algorithme | Précision | Rappel | F1 | Accuracy | AP@0.5 | Dataset |
|---|---|---|---|---|---|---|---|
| Chute | Ratio h/w < 0.65 + filtres bbox | 42.9% | **100%** | 0.600 | 60.0% | 0.393 | URFD (70 vidéos) |
| Attroupement | ≥8 personnes, dist <200px | **98.4%** | 60.4% | 0.748 | 65.0% | 0.892 | People Counting (135 img) |
| Objet abandonné | Immobilité ≥22 frames, grille 100px | 74.5% | 61.9% | 0.676 | 51.3% | 0.586 | Abandoned Bag + P&L (200 img) |
| **Global** | YOLOv8n CPU, IoU ≥ 0.5 | **72.2%** | **64.7%** | **0.682** | **56.3%** | **mAP=0.624** | 517 images + 70 vidéos |

> **Note :** Recall 100% sur les chutes — aucune chute réelle manquée sur 70 vidéos URFD. Précision 98.4% attroupements — seuil 8 personnes calibré empiriquement. Logique anti-duplication : alerte uniquement sur **apparition** de la foule (pas pendant sa persistance).

---

## Architecture Multi-Agent

```
Vidéo Upload / Flux Caméra
        │
        ▼
① Agent Perception    — YOLOv8n (détection 80 classes COCO, 6.2 Mo)
        │                 156.6 ms/frame CPU → 6.4 FPS brut (15.6 FPS effectif)
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
| `FALL_MIN_HEIGHT` | 50 px | Hauteur minimale bbox — exclut têtes partielles |
| `FALL_MIN_WIDTH` | 80 px | Largeur minimale bbox — exclut détections fragmentées |
| `FALL_MIN_AREA` | 5000 px² | Aire minimale bbox — exclut personnes hors champ |
| `FALL_EDGE_MARGIN` | 20 px | Marge bord frame — ignore entrées/sorties du champ |
| `FALL_COOLDOWN` | 300 frames | Anti-doublon chute (~10s à 30fps) |
| `CROWD_MIN` | **8 personnes** | Seuil déclenchement attroupement |
| `CROWD_PROXIMITY` | 200 px | Distance max entre personnes |
| `CROWD_COOLDOWN` | 90 frames | Anti-doublon attroupement |
| `CROWD_GRACE_FRAMES` | 5 frames | Délai avant reset — absorbe fluctuations YOLO |
| `STATIONARY_THR` | 22 frames | Immobilité pour objet abandonné |
| `MOVE_THRESHOLD` | 50 px | Déplacement max considéré comme immobile |
| `ABANDON_COOLDOWN` | 900 frames | Anti-doublon objet (~30s à 30fps) |
| `GRID_SZ` | 100 px | Résolution grille spatiale |
| `FRAME_SKIP` | 3 | Traitement 1 frame/4 (optimisation CPU) |
| `CONFIDENCE` | 0.25 | Seuil confiance YOLO |
| `IOU_THRESHOLD` | 0.5 | Seuil IoU pour validation détection |

---

## Stack Technique

### Backend

| Technologie | Version | Rôle |
|---|---|---|
| Flask | 3.1.3 | API REST — 18 endpoints |
| MongoDB | 6.0 | Stockage analyses, alertes, utilisateurs |
| Redis | 7 | Cache analytics |
| YOLOv8n | 8.3.0 | Détection objets (CPU-only) |
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

### ⚡ Option 0 — Scripts Windows (le plus simple)

Double-clic sur les fichiers à la racine du projet :

| Fichier | Action |
|---|---|
| `start.bat` | Lance tous les services + ouvre le navigateur |
| `stop.bat` | Arrête tous les services proprement |

> **Prérequis** : Docker Desktop ouvert (icône 🐳 verte dans la barre des tâches)

### Option 1 — Docker Compose (recommandé)

```bash
git clone https://github.com/zghari-med/AMANE-NEXUS.git
cd AMANE-NEXUS
docker-compose up -d
```

L'application sera disponible sur **http://localhost:3000**

**Identifiants par défaut :** `admin@surveillance.com` / `admin123`

```bash
# Arrêter
docker-compose down

# Vérifier les services
docker ps
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

Le projet utilise **deux pipelines CI/CD** : GitHub Actions et GitLab CI/CD.

### GitHub Actions (`.github/workflows/ci.yml`)

```
lint-backend → test-backend → validate-benchmarks → test-frontend → docker-build
```

| Job | Description | Outil |
|---|---|---|
| `lint-backend` | Vérification style Python | flake8 --max-line-length=120 |
| `test-backend` | Tests unitaires + intégration | pytest + MongoDB service |
| `validate-benchmarks` | F1 ≥ 0.50, Précision ≥ 40% | Python assertions |
| `test-frontend` | Build production React | Vite build |
| `docker-build` | Build image multi-stage | docker/build-push-action |

### GitLab CI/CD (`.gitlab-ci.yml`) — 5 stages

```
lint ──► test ──► docker ──► deploy ──► report
  │                                       │
  ├─ lint-backend (flake8)                ├─ owasp-report  (HTML 30j)
  ├─ audit-python (pip-audit + CVE scan)  ├─ benchmark-report (HTML 30j)
  └─ audit-frontend (npm audit)           └─ pipeline-report (résumé)
```

| Stage | Job | Description |
|---|---|---|
| lint | `audit-python` | pip-audit OWASP A06 — CVE scan Python deps |
| lint | `audit-frontend` | npm audit — CVE scan Node deps |
| test | `test-backend` | pytest 60 tests + coverage |
| test | `validate-benchmarks` | validation benchmark_results.json |
| docker | `docker-build` | Build image Docker |
| deploy | `deploy` | Push GitLab Container Registry (main only) |
| report | `owasp-report` | Génère `owasp-report.html` (artifact 30 jours) |
| report | `benchmark-report` | Génère `benchmark-report.html` (artifact 30 jours) |

> Les rapports HTML sont disponibles dans **GitLab → CI/CD → Pipelines → Artifacts** après chaque push.

---

## Sécurité — OWASP Top 10

| # | Catégorie | Statut | Implémentation |
|---|---|---|---|
| A01 | Broken Access Control | ✅ Couvert | JWT stateless + RBAC (admin / operator / viewer) |
| A02 | Cryptographic Failures | ✅ Couvert | bcrypt cost=12 + JWT HS256 + SECRET_KEY auto-généré |
| A03 | Injection | ✅ Couvert | ObjectId typé MongoDB — injection NoSQL impossible |
| A04 | Insecure Design | ✅ Couvert | Architecture multi-agent isolée, uploads restreints |
| A05 | Security Misconfiguration | ✅ Couvert | .env exclu, CORS limité, variables Docker Compose |
| A06 | Vulnerable & Outdated Components | ✅ Couvert | pip-audit en CI/CD — 25 CVE corrigées |
| A07 | Identification & Auth Failures | ✅ Couvert | Flask-Limiter : 10 req/min + 50 req/hr sur /login |
| A08 | Software & Data Integrity | ✅ Couvert | 6 headers HTTP (CSP, X-Frame-Options…) via @after_request |
| A09 | Security Logging & Monitoring | ✅ Couvert | log_activity() — chaque action tracée dans MongoDB |
| A10 | SSRF | ✅ Couvert | _is_ssrf_safe() bloque loopback et link-local |

> Rapport détaillé généré automatiquement : `scripts/generate_owasp_report.py`

---

## Auteur

**Mohamed Z'GHARI**

---

*AMANE-NEXUS © 2026 — Système de Surveillance Intelligente Multi-Agent*
