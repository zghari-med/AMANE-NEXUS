# WIKI Technique — Système de Surveillance Intelligente
## PFE MSID-TAM | Documentation Complète

---

## Table des Matières

1. [Installation & Démarrage](#installation)
2. [Architecture du Code](#architecture)
3. [Worker d'Analyse](#worker)
4. [API REST](#api)
5. [Frontend React](#frontend)
6. [Analytics Engine](#analytics)
7. [Benchmarks](#benchmarks)
8. [Tests](#tests)
9. [CI/CD](#cicd)
10. [Docker](#docker)
11. [Dépannage](#debug)

---

## 1. Installation & Démarrage {#installation}

### Prérequis
- Python 3.10+ (3.12 recommandé)
- Node.js 18+
- MongoDB 6.0
- 8 Go RAM minimum

### Installation backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### Installation frontend
```bash
cd frontend
npm install
```

### Démarrage développement
```bash
# Terminal 1 — MongoDB
mongod --dbpath ./data/db

# Terminal 2 — Backend
cd backend && python app_simple.py

# Terminal 3 — Frontend
cd frontend && npm run dev
```

### Création du compte admin (première utilisation)
```python
from pymongo import MongoClient
import bcrypt
c = MongoClient()
db = c['surveillance_db']
db.user.insert_one({
    'email': 'admin@surveillance.com',
    'username': 'admin',
    'password': bcrypt.hashpw(b'admin123', bcrypt.gensalt()),
    'role': 'admin'
})
```

---

## 2. Architecture du Code {#architecture}

```
surveillance_project/
├── backend/
│   ├── app_simple.py          # API Flask principale
│   ├── worker_analysis.py     # Worker d'analyse (YOLO)
│   ├── data/
│   │   ├── analytics.py       # AnalyticsEngine (Pandas)
│   │   └── benchmark_results.json
│   ├── services/
│   │   └── analytics_service.py  # Façade + BenchmarkLoader
│   ├── tests/
│   │   ├── test_analytics.py
│   │   └── test_benchmarks.py
│   ├── captures/              # Images annotées des alertes
│   ├── uploads/               # Vidéos uploadées
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Routing React
│   │   ├── pages/
│   │   │   ├── DashboardAdminPage.jsx
│   │   │   ├── DashboardUserPage.jsx
│   │   │   ├── VideosPage.jsx
│   │   │   ├── StatisticsPage.jsx
│   │   │   ├── BenchmarksPage.jsx
│   │   │   ├── TrendsPage.jsx
│   │   │   └── UsersPage.jsx
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── MetricsCard.jsx
│   │   │   └── BenchmarkChart.jsx
│   │   └── context/
│   │       └── authStore.js   # Zustand auth store
├── docs/
│   ├── RAPPORT_PFE.md
│   ├── PFE_CONTEXT.md
│   ├── WIKI.md (ce fichier)
│   └── FAQ_SOUTENANCE.md
├── .github/
│   └── workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
└── nginx.conf
```

---

## 3. Worker d'Analyse {#worker}

### Paramètres calibrés

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| FALL_RATIO_THRESHOLD | 0.65 | h/w bbox < seuil → chute |
| CROWD_MIN_PERSONS | 5 | Nombre minimum pour attroupement |
| CROWD_PROXIMITY_PX | 200 | Distance max entre personnes (px) |
| ABANDONED_MOVE_PX | 50 | Mouvement max pour "immobile" |
| ABANDONED_MIN_FRAMES | 22 | Frames immobiles avant alerte |
| CONFIDENCE_MIN | 0.25 | Confiance minimum YOLO |
| FRAME_SKIP | 3 | Analyser 1 frame sur 3 |
| FALL_COOLDOWN | 300 | Frames entre 2 alertes chute |
| CROWD_COOLDOWN | 90 | Frames entre 2 alertes attroupement |
| ABANDONED_COOLDOWN | 900 | Frames entre 2 alertes objet |

### Classes d'objets détectés (portables uniquement)
```python
OBJECT_CLASSES = {
    24,  # backpack
    25,  # umbrella
    26,  # handbag
    28,  # suitcase
    36,  # skateboard
    39,  # bottle
    67,  # cell phone
}
```

### Format des captures
Chaque alerte génère une image JPEG annotée :
- Bannière colorée en haut (rouge=chute, orange=attroupement, vert=objet)
- Rectangles épais avec coins accentués autour des objets détectés
- Numéro de frame en haut à droite
- Fichier : `{analysis_id}_{frame_id}_{event_type}.jpg`

---

## 4. API REST {#api}

### Authentification
```http
POST /api/auth/login
Content-Type: application/json

{"email": "admin@surveillance.com", "password": "admin123"}
```

Réponse :
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {"id": "...", "email": "...", "role": "admin"}
}
```

### Upload vidéo
```http
POST /api/videos/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<video.mp4>&title=ma_video
```

### Lancer une analyse
```http
POST /api/analyses/create
Authorization: Bearer <token>
Content-Type: application/json

{"video_id": "6a1794e08320a9712f37462d"}
```

### Obtenir les benchmarks
```http
GET /api/analyses/benchmarks
```
(Endpoint public, pas d'auth requise)

### Export CSV
```http
GET /api/analyses/<id>/metrics-export
Authorization: Bearer <token>
```

---

## 5. Frontend React {#frontend}

### État global (Zustand)
```javascript
// authStore.js
{
  user: { id, email, username, role },
  token: "JWT...",
  login(email, password) → Promise<boolean>,
  logout()
}
```

### Pages disponibles

| Route | Composant | Accès |
|-------|-----------|-------|
| `/` | DashboardAdminPage / DashboardUserPage | Tous |
| `/videos` | VideosPage | Tous |
| `/statistics` | StatisticsPage | Tous |
| `/benchmarks` | BenchmarksPage | Tous |
| `/trends` | TrendsPage | Tous |
| `/users` | UsersPage | Admin |

### Polling d'analyse
```javascript
// Démarré lors du clic "Lancer l'analyse"
pollRef.current = setInterval(() => fetchAnalysisState(analysisId), 3000)
// Arrêté quand status = 'completed' ou 'failed'
```

---

## 6. Analytics Engine {#analytics}

### AnalyticsEngine

```python
from data.analytics import AnalyticsEngine

engine = AnalyticsEngine()

# Statistiques sur 7 jours
stats = engine.get_alerts_statistics(days=7)

# Précision/Rappel/F1
accuracy = engine.get_detection_accuracy()

# Tendances hebdomadaires
trends = engine.generate_trend_analysis(weeks=8)

# Export CSV
csv = engine.export_metrics_csv(analysis_id)
```

### BenchmarkLoader (lazy-loading)

```python
from services.analytics_service import BenchmarkLoader

data = BenchmarkLoader.get_or_load()
f1 = data['model_accuracy']['global']['f1_score']  # 0.627 (valide sur 11 datasets reels)
```

---

## 7. Benchmarks {#benchmarks}

### Résultats clés — Validation END-TO-END (11 datasets réels)

| Métrique | Valeur | Source |
|----------|--------|--------|
| F1-Score global | **0.627** | 11 datasets annotés Roboflow + URFD |
| Précision moyenne | 57.2% | IoU >= 0.5 |
| Rappel moyen | 76.4% | 1040 images + 70 vidéos |
| IoU moyen | 0.764 | Localisation bounding boxes |
| Inférence moy. (CPU) | 191 ms | YOLOv8n, 640x640 |
| FPS effectif | 5.2 FPS | Sans FRAME_SKIP |
| FPS avec SKIP×3 | 15.6 FPS | Mode production |

### Par comportement

| Comportement | Dataset | Précision | Rappel | F1 | IoU |
|---|---|---|---|---|---|
| Chute | URFD (70 vidéos) | 42.9% | **100%** | **0.600** | 0.429 |
| Attroupement | People Counting | **74.8%** | 64.6% | **0.693** | 0.691 |
| Objet abandonné | Person+Luggage | 54.0% | 64.5% | **0.588** | **0.849** |

---

## 8. Tests {#tests}

### Lancer les tests
```bash
cd backend
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Tests disponibles

**test_analytics.py** :
- `TestAnalyticsEngineInitialization` : init engine + connexion MongoDB
- `TestDetectionAccuracy` : F1>=0.50, P/R coherence formule
- `TestStatisticsComputation` : structure, comptages, avg_per_day
- `TestTrendAnalysis` : structure vide, direction, avg_per_day

**test_benchmarks.py** :
- `TestBenchmarkFileExists` : existence + JSON valide
- `TestBenchmarkStructure` : F1>=0.50, Precision>=40%, validation END-TO-END
- `TestBenchmarkLoader` : lazy-loading, cache, F1

---

## 9. CI/CD {#cicd}

Pipeline GitHub Actions (`.github/workflows/ci.yml`) :

1. **lint-backend** : flake8 --max-line-length=120
2. **test-backend** : pytest avec MongoDB service
3. **validate-benchmarks** : verification F1>=0.50 (valide sur 11 datasets reels)
4. **test-frontend** : npm lint + npm build
5. **docker-build** : build image Docker
6. **pipeline-report** : affiche le status final

---

## 10. Docker {#docker}

### Démarrage avec Docker Compose
```bash
docker-compose up -d
```

### Services
- MongoDB : `localhost:27017`
- Backend Flask : `localhost:5000`
- Frontend : `localhost:3000`

### Variables d'environnement
```env
MONGO_URI=mongodb://mongodb:27017/
REDIS_HOST=redis
SECRET_KEY=your_secret_key
ANALYTICS_CACHE_TTL=3600
```

---

## 11. Dépannage {#debug}

### Analyse bloquée en "processing"
```python
db.analysis.update_many(
    {'status': {'$in': ['pending', 'processing']}},
    {'$set': {'status': 'failed'}}
)
```

### Réinitialiser la base de données
```python
db.alert.delete_many({})
db.analysis.delete_many({})
```

### Vérifier que YOLO fonctionne
```bash
cd backend
python -c "from ultralytics import YOLO; m=YOLO('yolov8n.pt'); print('YOLO OK')"
```

### Vérifier l'API
```bash
curl http://localhost:5000/api/health
```
