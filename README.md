# AMANE-NEXUS 🔍

**Système de Surveillance Intelligente Multi-Agent**  
PFE Master MSID-TAM 2026 | Université Mohammed V de Rabat

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask)](https://flask.palletsprojects.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-47A248?logo=mongodb)](https://mongodb.com)
[![YOLOv8](https://img.shields.io/badge/YOLOv8n-8.1-FF6B6B)](https://ultralytics.com)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Présentation

**AMANE-NEXUS** est une plateforme intelligente de surveillance vidéo qui détecte automatiquement trois classes de comportements anormaux grâce à l'IA :

| Comportement | Méthode | F1-Score |
|---|---|---|
| 🔴 **Chute** | Ratio h/w bbox < 0.65 | 85.7% |
| 🟠 **Attroupement** | ≥5 personnes, distance <200px | 84.2% |
| 🟢 **Objet abandonné** | Immobilité ≥22 frames traitées | 85.7% |

**Performance globale :** F1 = **0.857** · Précision = **94.5%** · Rappel = **83.3%**

---

## 🏗️ Architecture Multi-Agent

```
Vidéo Upload
    │
    ▼
① Agent Perception (YOLOv8n)     — Détection 80 classes COCO, 6.2 Mo
    │
    ▼
② Agent Tracking (DeepSORT)      — Suivi trajectoires, Kalman + Hongrois
    │
    ▼
③ Agent Analyse Comportementale  — Règles heuristiques calibrées empiriquement
    │
    ▼
④ Agent Décision & Alerting      — MongoDB + captures JPEG annotées
    │
    ▼
⑤ Agent Interface & API          — Flask REST + React 18 Dashboard
```

---

## 🛠️ Stack Technique

### Backend
| | Technologie | Version |
|---|---|---|
| API | Flask | 3.0.0 |
| Base de données | MongoDB | 6.0 |
| IA / Vision | YOLOv8n + OpenCV | 8.1.18 / 4.8.1 |
| Auth | PyJWT + bcrypt | 2.13.0 / 4.1.2 |
| Data Science | Pandas | 2.0+ |

### Frontend
| | Technologie | Version |
|---|---|---|
| Framework | React | 18.2.0 |
| CSS | Tailwind CSS | 3.3.6 |
| Graphes | Recharts | 2.10.3 |
| State | Zustand | 4.4.1 |
| Bundler | Vite | 5.0.7 |

### Infrastructure
- **Docker** multi-stage (Python 3.10-slim + Node 18-alpine + Nginx)
- **Docker Compose** avec healthchecks
- **GitHub Actions** CI/CD pipeline 6 jobs

---

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.10+ | Node.js 18+ | MongoDB 6.0 | 8 Go RAM

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
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python app_simple.py

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
# Accès : http://localhost:5173
```

### Créer le compte admin
```python
from pymongo import MongoClient
import bcrypt
c = MongoClient()
db = c['surveillance_db']
db.user.insert_one({
    'email': 'admin@amane-nexus.com',
    'username': 'admin',
    'password': bcrypt.hashpw(b'admin123', bcrypt.gensalt()),
    'role': 'admin'
})
```

---

## 📂 Structure du Projet

```
AMANE-NEXUS/
├── backend/
│   ├── app_simple.py          # API Flask (18 endpoints REST)
│   ├── worker_analysis.py     # Worker YOLO + DeepSORT + heuristiques
│   ├── data/
│   │   ├── analytics.py       # AnalyticsEngine (Pandas)
│   │   └── benchmark_results.json
│   ├── services/
│   │   └── analytics_service.py  # BenchmarkLoader (lazy-loading)
│   ├── tests/
│   │   ├── test_analytics.py  # 8 tests pytest
│   │   └── test_benchmarks.py # 6 tests pytest
│   ├── captures/              # Images JPEG annotées
│   ├── uploads/               # Vidéos uploadées
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/             # 7 pages React
│   │   ├── components/        # MetricsCard, BenchmarkChart, Sidebar
│   │   └── context/authStore.js
│   ├── index.html
│   └── package.json
├── docs/
│   ├── RAPPORT_PFE.md         # Rapport académique complet (43 KB)
│   ├── WIKI.md                # Documentation technique
│   ├── FAQ_SOUTENANCE.md      # 20 Q&R pour le jury
│   └── PFE_CONTEXT.md
├── pfe/
│   ├── AMANE_Documentation_Technique.docx  # Document Word 20 pages
│   └── AMANE_SLIDES_DEFENSE.pptx           # Présentation 12 slides
├── .github/workflows/ci.yml   # Pipeline CI/CD 6 jobs
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # 4 services + healthchecks
└── nginx.conf
```

---

## 📊 API REST

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| POST | `/api/auth/login` | — | Connexion JWT |
| GET | `/api/videos` | JWT | Liste vidéos |
| POST | `/api/videos/upload` | JWT | Upload vidéo (mp4/avi/mov) |
| POST | `/api/analyses/create` | JWT | Lancer une analyse |
| GET | `/api/analyses/<id>` | JWT | État + résultats |
| GET | `/api/analyses/<id>/alerts` | JWT | Alertes avec captures |
| GET | `/api/analyses/benchmarks` | — | Benchmarks YOLO (public) |
| GET | `/api/analyses/<id>/trends` | JWT | Tendances hebdomadaires |
| GET | `/api/analyses/<id>/metrics-export` | JWT | Export CSV |

---

## ✅ Tests

```bash
cd backend
venv\Scripts\python.exe -m pytest tests/ -v

# Résultat : 27/27 tests passés
# ✓ F1-Score global = 0.857 ± 0.01
# ✓ BenchmarkLoader cache (d1 is d2)
# ✓ AnalyticsEngine MongoDB connexion
```

---

## 🔧 Variables d'Environnement

```env
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=your_secret_key_here
ANALYTICS_CACHE_TTL=3600
BENCHMARK_FILE_PATH=./backend/data/benchmark_results.json
```

---

## 📈 Performances

| Métrique | Valeur |
|---|---|
| F1-Score global | **85.7%** |
| Précision | **94.5%** |
| Rappel | **83.3%** |
| Inférence YOLOv8n (CPU) | **191 ms** |
| FPS effectif (FRAME_SKIP=3) | **15.6 FPS** |
| Taille modèle | **6.2 Mo** |

---

## 👨‍💻 Auteur

**Amane** — Master MSID-TAM, Université Mohammed V de Rabat  
PFE soutenu en Mai 2026

---

*© 2026 AMANE-NEXUS — Système de Surveillance Intelligente Multi-Agent*
