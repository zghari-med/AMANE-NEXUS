# 🏗️ Architecture Détaillée du Système

## Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND REACT                              │
│   (Dashboard Admin/User, Upload Vidéo, Visualisation)           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ HTTP/REST (JWT Auth)
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                      FLASK API                                   │
│   Routes: /auth, /videos, /analyses, /export                    │
│   MongoDB: Persistence (Users, Videos, Analyses, Alerts)        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
        ┌─────────┴──────────────┐
        │                        │
        ▼                        ▼
    REDIS PUBSUB          MongoDB Storage
    (Real-time Events)    (Persistent Data)
        │
    ┌───┴──────────────────────────────────┐
    │  AGENT PIPELINE                      │
    │  (Multi-Agents Communication)        │
    │                                      │
    │  1. Perception Agent                 │
    │     └─> channel:detections           │
    │                                      │
    │  2. Tracking Agent                   │
    │     └─> channel:tracks               │
    │                                      │
    │  3. Analysis Agent                   │
    │     └─> channel:analysis             │
    │                                      │
    │  4. Decision Agent                   │
    │     └─> channel:alerts               │
    │        └─> MongoDB (Alerts)          │
    └──────────────────────────────────────┘
```

## 1️⃣ Couche Frontend (React)

### Architecture Composants

```
App.jsx (Routeur Principal)
├── LoginPage
│   └── useAuthStore (Zustand)
├── RegisterPage
├── DashboardAdminPage
│   ├── Sidebar
│   ├── StatCard (x5)
│   ├── LineChart (Détections)
│   └── AlertsList
├── DashboardUserPage
│   ├── Sidebar
│   ├── StatCard (x4)
│   ├── VideoGrid
│   └── AnalysisTable
└── AnalysisPage
    ├── VideoPlayer
    ├── AnalysisStats
    ├── ExportButtons
    └── AlertsTimeline
```

### State Management (Zustand)

```javascript
useAuthStore
├── user (object)
├── token (string)
├── isLoading (boolean)
├── login() → fetch JWT
├── register() → create account
└── logout() → clear state
```

### Communication API

```
Frontend <--HTTP--> Flask API
├── GET /api/auth/me
├── POST /api/auth/login
├── POST /api/auth/register
├── GET /api/videos
├── POST /api/videos/upload
├── POST /api/analyses/create
├── GET /api/analyses
├── GET /api/analyses/<id>/alerts
└── GET /api/analyses/<id>/export/{csv,json,pdf}
```

### Design System

**Palette de Couleurs :**
```
Primary Blue: #1e40af, #2563eb, #3b82f6
Gray Scale: #111827 → #f9fafb
Alerts: Red #ef4444, Orange #f59e0b, Yellow #fbbf24
```

**Composants Réutilisables :**
- `StatCard` : Cartes statistiques avec icons
- `ProtectedRoute` : Vérification JWT
- `Sidebar` : Navigation principale
- Badge, Button, Input, Card, Modal

## 2️⃣ Couche Backend (Flask)

### Architecture API

```
Flask App (app.py)
├── config/ (Configuration)
│   └── config.py
│       ├── DevelopmentConfig
│       ├── ProductionConfig
│       └── TestingConfig
│
├── models/ (MongoDB)
│   ├── user.py
│   ├── video.py
│   ├── analysis.py
│   └── alert.py
│
├── services/ (Business Logic)
│   ├── auth_service.py (JWT, Hashing)
│   ├── video_service.py (Upload, Metadata)
│   ├── analysis_service.py (CRUD)
│   └── export_service.py (CSV, JSON, PDF)
│
├── routes/ (HTTP Endpoints)
│   ├── auth_routes.py (/api/auth)
│   ├── video_routes.py (/api/videos)
│   └── analysis_routes.py (/api/analyses)
│
└── uploads/ (Stockage vidéos)
└── exports/ (Rapports générés)
```

### Modèles de Données

#### User
```python
{
  "_id": ObjectId,
  "email": string (unique),
  "username": string (unique),
  "password": string (bcrypt hash),
  "role": "admin" | "user",
  "is_active": boolean,
  "created_at": datetime,
  "can_manage_users": boolean,
  "can_view_all_analyses": boolean
}
```

#### Video
```python
{
  "_id": ObjectId,
  "title": string,
  "filename": string (unique),
  "filepath": string,
  "uploaded_by": ObjectId (User ref),
  "status": "uploaded" | "processing" | "completed" | "failed",
  "duration": float (seconds),
  "fps": int,
  "resolution": string ("1920x1080"),
  "file_size": int (bytes),
  "analysis_id": ObjectId (Analysis ref),
  "created_at": datetime
}
```

#### Analysis
```python
{
  "_id": ObjectId,
  "video": ObjectId (Video ref),
  "user": ObjectId (User ref),
  "status": "pending" | "processing" | "completed" | "failed",
  "total_events": int,
  "falls_detected": int,
  "crowds_detected": int,
  "abandoned_objects": int,
  "events_timeline": [
    {"type": "fall", "time": 12.5, "confidence": 0.95}
  ],
  "processing_time": float (seconds),
  "average_fps": float,
  "cpu_usage": float (%),
  "created_at": datetime,
  "completed_at": datetime
}
```

#### Alert
```python
{
  "_id": ObjectId,
  "analysis": ObjectId (Analysis ref),
  "user": ObjectId (User ref),
  "event_type": "fall" | "crowding" | "abandoned_object",
  "risk_level": "low" | "medium" | "high" | "critical",
  "event_details": {...},
  "frame_id": int,
  "timestamp": float (seconds),
  "status": "active" | "acknowledged" | "resolved",
  "created_at": datetime
}
```

### Authentification (JWT)

```
1. User → POST /api/auth/login {email, password}
2. Server → Hash password with stored hash (bcrypt)
3. Generate JWT token
4. Token = { user_id, email, role, exp: +24h }
5. Client → store token in localStorage
6. All requests: Header "Authorization: Bearer <token>"
7. Backend: verify_token() middleware
```

### Sécurité

```
- CORS enabled for frontend origin
- JWT expiration: 24 hours
- Password hashing: bcrypt (10 rounds)
- Input validation: all routes
- Role-based access control (RBAC)
- Protected routes: @token_required
- Admin only: @admin_required
```

## 3️⃣ Pipeline Agent Multi-Agents

### Architecture Pipeline

```
VIDEO INPUT
    │
    ▼
┌──────────────────────────────────────┐
│ AGENT PERCEPTION (YOLOv8n)           │
│ ─────────────────────────────────── │
│ • Charge frame par frame             │
│ • Lance YOLO (tous les N frames)     │
│ • Détecte: person, car, bicycle...   │
│ • Output: bboxes + confidence        │
│ • Publier sur channel:detections     │
└──────────────────────────────────────┘
    │
    │ Redis Channel: channel:detections
    │ {frame_id, detections: [{bbox, class, conf}, ...]}
    │
    ▼
┌──────────────────────────────────────┐
│ AGENT TRACKING (DeepSORT)            │
│ ─────────────────────────────────── │
│ • Reçoit les détections              │
│ • Apparie avec tracks existants      │
│ • Calcule la vitesse                 │
│ • Attribue IDs persistants           │
│ • Output: tracks avec IDs            │
│ • Publier sur channel:tracks         │
└──────────────────────────────────────┘
    │
    │ Redis Channel: channel:tracks
    │ {frame_id, tracks: [{id, bbox, class, velocity}, ...]}
    │
    ▼
┌──────────────────────────────────────┐
│ AGENT ANALYSE                        │
│ ─────────────────────────────────── │
│ • Fall Detector: détecte chutes      │
│   - Analyse posture (hauteur bbox)   │
│   - 40% de la hauteur normale        │
│   - Confirme après N frames          │
│                                      │
│ • Crowding Detector: détecte groupes │
│   - Distance inter-personnages       │
│   - Densité (personnes/pixels²)      │
│   - Formation suspecte               │
│                                      │
│ • Abandoned Detector: objets laissés │
│   - Suivi de position (5 frames)     │
│   - Pas de mouvement > 120 frames    │
│   - Éloignement du propriétaire      │
│                                      │
│ • Output: événements détectés        │
│ • Publier sur channel:analysis       │
└──────────────────────────────────────┘
    │
    │ Redis Channel: channel:analysis
    │ {events: [{type: "fall", track_id: 5, confidence: 0.92}, ...]}
    │
    ▼
┌──────────────────────────────────────┐
│ AGENT DÉCISION                       │
│ ─────────────────────────────────── │
│ • Évalue le risque pour chaque       │
│ • Risk Matrix:                       │
│   - fall → HIGH                      │
│   - crowding → MEDIUM                │
│   - abandoned → MEDIUM               │
│                                      │
│ • Escalade de risque:                │
│   - Même événement x3 → CRITICAL     │
│                                      │
│ • Génère alertes                     │
│ • Stocke dans MongoDB                │
│ • Envoie notifications               │
│ • Publie sur channel:alerts          │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ STORAGE & NOTIFICATIONS              │
│ ─────────────────────────────────── │
│ • MongoDB: Alertes persistantes      │
│ • Redis: Alertes en temps réel       │
│ • Frontend: WebSocket/Polling        │
│ • Email/SMS: Notification service    │
└──────────────────────────────────────┘
```

### Détection de Chute

```
Algorithme:
1. Garder historique des hauteurs (derniers N frames)
2. Calculer hauteur "normale" = médiane(historique)
3. Si hauteur actuelle < 40% × normal_height:
   - Incrémenter compteur frames_bas
   - Si compteur >= 10 frames:
     → Événement CHUTE détecté (confidence = compteur/10)
4. Si hauteur > 40% normal:
   - Réinitialiser compteur frames_bas

Paramètres:
- FALL_DETECTION["min_height_ratio"] = 0.4
- FALL_DETECTION["horizontal_frames"] = 10
```

### Détection d'Attroupement

```
Algorithme:
1. Pour chaque pair de personnes:
   - Calculer distance euclidienne entre centres
   - Si distance < 100 pixels → dans le même groupe
2. Clustering spatial (composantes connexes)
3. Pour chaque groupe:
   - Si taille >= 3 personnes:
     - Calculer densité = nb_personnes / surface_englobante
     - Si densité > 0.05 → ATTROUPEMENT détecté

Paramètres:
- CROWDING_DETECTION["min_crowd_size"] = 3
- CROWDING_DETECTION["density_threshold"] = 0.05
- CROWDING_DETECTION["proximity_distance"] = 100
```

### Détection d'Objet Abandonné

```
Algorithme:
1. Garder historique des 5 dernières positions
2. Calculer mouvement = distance_moyenne(positions)
3. Si mouvement < 5 pixels:
   - Incrémenter compteur frames_stationnaire
   - Si compteur >= 120 frames (4-5 secondes):
     → Objet ABANDONNÉ détecté
4. Vérifier si propriétaire s'est éloigné (optionnel)

Paramètres:
- ABANDONED_DETECTION["min_stationary_frames"] = 120
- ABANDONED_DETECTION["movement_threshold"] = 5
```

## 4️⃣ Communication Redis

### Channels

```
channel:detections
├── Source: Agent Perception (YOLO)
├── Format: {frame_id, detections: [{bbox, class, conf}]}
└── Subscribers: Agent Tracking

channel:tracks
├── Source: Agent Tracking (DeepSORT)
├── Format: {frame_id, tracks: [{id, bbox, class, velocity}]}
└── Subscribers: Agent Analysis

channel:analysis
├── Source: Agent Analysis
├── Format: {events: [{type, track_id, confidence}]}
└── Subscribers: Agent Decision

channel:alerts
├── Source: Agent Decision
├── Format: {alert_id, event_type, risk_level, timestamp}
└── Subscribers: Frontend (optional), API (storage)

channel:notifications
├── Source: Agent Decision
├── Format: {type, alert_id, message}
└── Subscribers: Email Service, SMS Service
```

### Throttling

```
Agent Perception:
- Publie max 10 messages/sec sur Redis
- Toutes les frames sont traitées/affichées
- Mais YOLO tourne seulement 1 frame sur 3

Agent Tracking:
- Queue de max 50 messages
- Thread listener asynchrone
- Thread principal (DeepSORT) synchrone
```

## 5️⃣ Performance & Optimisations

### CPU Optimization

```
✅ Frame Skipping
- YOLO s'exécute 1 frame / 3
- Réduit la charge CPU de 66%
- Les frames intermédiaires réutilisent le dernier résultat

✅ Model Size
- YOLOv8n (nano) : plus rapide, 7M paramètres
- Vs YOLOv8m (medium) : 26M paramètres

✅ Batch Processing
- Pas de batches, stream vidéo real-time
- Single image processing

✅ Device
- Device='cpu' (pas de GPU disponible)
- Optimisé pour CPU i7

✅ Inference Size
- IMG_SIZE = 640 (standard COCO)
- Détecte bien les petits objets
```

### Memory Management

```
✅ Circular Buffers
- deque(maxlen=N) pour l'historique
- Limite automatique de la mémoire

✅ Redis Cleanup
- Alertes expirées après 1h
- Tracks supprimés après 20 frames sans détection

✅ Database Indexes
- Index sur (user, status, created_at)
- Index sur (event_type, risk_level)
```

### Latency

```
Perception → Tracking → Analysis → Decision: ~100-200ms
Frontend Update: 5-10 sec (polling) ou real-time (WebSocket)
```

## 6️⃣ Déploiement

### Production Checklist

- [ ] Utiliser `ProductionConfig` dans config.py
- [ ] Vérifier HTTPS sur l'API
- [ ] Configurer CORS pour le domaine de prod
- [ ] Mettre en place la sauvegarde MongoDB
- [ ] Configurer les logs structurés
- [ ] Mettre en cache les modèles YOLOv8
- [ ] Utiliser un reverse proxy (Nginx)
- [ ] Configurer les alertes/notifications
- [ ] Rate limiting sur l'API
- [ ] Monitoring (Prometheus, Grafana)

### Docker (Optionnel)

```dockerfile
# Backend Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "app.py"]

# Frontend Dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend/package*.json .
RUN npm install
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

## 7️⃣ Scaling Future

```
Horizontal:
- Multiple instances Flask (load balancer)
- MongoDB Replica Set
- Redis Cluster
- Agent containers orchestrés (Kubernetes)

Vertical:
- GPU pour YOLO (CUDA)
- Quantization des modèles (INT8)
- Model pruning
```

---

**Architecture v1.0 - Mai 2026**
