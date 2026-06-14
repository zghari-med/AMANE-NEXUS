# AMANE-NEXUS — Backend

API REST Flask + moteur de surveillance multi-agent YOLOv8n.

## Stack

| Composant | Version | Rôle |
|---|---|---|
| Python | 3.10+ | Runtime |
| Flask | 3.1.3 | API REST — 18 endpoints |
| MongoDB / MongoEngine | 6.0 / 0.28.1 | Persistance analyses, alertes, utilisateurs |
| Redis | 7 | Cache analytics |
| YOLOv8n (Ultralytics) | 8.3.0 | Détection objets CPU-only |
| DeepSORT | 1.3.2 | Suivi de trajectoires (Kalman + Hongrois) |
| OpenCV | 4.8.1 | Vision par ordinateur |
| PyJWT | 2.13.0 | Tokens JWT (HS256) |
| bcrypt | 4.1.2 | Hachage mots de passe (cost 12) |
| Flask-Limiter | 3.5.0 | Rate-limiting (Redis backend) |
| Flask-CORS | 6.0.0 | CORS |
| Pandas | 2.0+ | Analytics et export CSV |

## Structure

```
backend/
├── app_simple.py          # Point d'entrée Flask — 18 endpoints REST
├── worker_analysis.py     # Worker YOLOv8n + DeepSORT + heuristiques
├── requirements.txt       # Dépendances (pip-audit vérifié en CI)
├── routes/
│   ├── auth_routes.py     # /api/auth/* — login, logout, me
│   ├── video_routes.py    # /api/videos/*, /api/cameras/*
│   └── analysis_routes.py # /api/analyses/*, /api/alerts/*
├── services/
│   └── analytics_service.py  # BenchmarkLoader, cache Redis
├── models/                # Documents MongoEngine
├── config/                # Configuration Flask
├── data/
│   └── benchmark_results.json  # Métriques END-TO-END validées
├── uploads/               # Vidéos uploadées (volume Docker)
├── captures/              # Captures JPEG annotées (volume Docker)
└── tests/
    ├── test_agents.py     # 30 tests — algorithmes heuristiques
    ├── test_api.py        # 12 tests — intégration REST
    ├── test_analytics.py  # 5 tests  — analytics et tendances
    ├── test_benchmarks.py # 10 tests — validation benchmark_results.json
    └── test_falls.py      # 1 test   — URFD recall = 100%
```

## Démarrage local

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python app_simple.py
# API disponible sur http://localhost:5000
```

Variables d'environnement (fichier `.env` à la racine du projet) :

```env
SECRET_KEY=votre_cle_secrete_forte_32_chars_minimum
MONGO_URI=mongodb://localhost:27017/
ANALYTICS_CACHE_TTL=3600
```

## Tests

```bash
python -m pytest tests/ -v --cov=.
```

**60/60 tests passés.** Couverture par fichier :

| Fichier | Tests | Description |
|---|---|---|
| `test_agents.py` | 30 | Algorithmes chute, attroupement, objet abandonné |
| `test_api.py` | 12 | Endpoints REST auth, caméras, statistiques |
| `test_analytics.py` | 5 | Cache Redis, tendances temporelles |
| `test_benchmarks.py` | 10 | Structure et seuils de benchmark_results.json |
| `test_falls.py` | 1 | Recall chute = 100% sur URFD (70 vidéos) |

## Agents de surveillance

### Agent Perception
- YOLOv8n, 80 classes COCO, confiance ≥ 0.25
- 156.6 ms/frame CPU → 6.4 FPS brut (15.6 FPS effectif avec `FRAME_SKIP=3`)

### Agent Tracking
- DeepSORT : Filtre de Kalman + assignation Hongrois
- IoU ≥ 0.5 pour validation des tracks

### Agent Analyse — Paramètres calibrés

| Comportement | Paramètre clé | Valeur | Résultat |
|---|---|---|---|
| Chute | Ratio h/w | < 0.65 | Recall 100% sur URFD |
| Attroupement | Seuil personnes | ≥ 8 | Précision 98.4% |
| Objet abandonné | Immobilité | ≥ 22 frames | F1 = 0.676 |

## Sécurité

- `@token_required` : JWT vérifié sur tous les endpoints — accepte `?token=` pour les flux `<video>` navigateur
- `@limiter.limit("10/minute;50/hour")` sur `/api/auth/login`
- 6 headers HTTP ajoutés via `@after_request` : CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, Strict-Transport-Security
- `_is_ssrf_safe()` : bloque loopback (127.x, ::1) et link-local (169.254.x.x) avant tout fetch d'URL caméra
- Mots de passe hachés bcrypt cost=12 ; SECRET_KEY auto-généré si absent ou faible
- RBAC : rôles `admin` / `operator` / `viewer` vérifiés par endpoint

## API REST — Référence rapide

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | — | Connexion → JWT |
| GET | `/api/videos` | JWT | Liste des vidéos |
| POST | `/api/videos/upload` | JWT | Upload (mp4/avi/mov) |
| POST | `/api/analyses/create` | JWT | Lancer analyse YOLOv8 |
| GET | `/api/analyses/<id>` | JWT | Statut + résultats |
| GET | `/api/analyses/<id>/alerts` | JWT | Alertes + captures |
| GET | `/api/analyses/benchmarks` | JWT | Métriques validées |
| GET | `/api/health` | — | Statut système |

Voir [README racine](../README.md) pour la liste complète des 18 endpoints.
