# Contexte Technique — PFE MSID-TAM
## Système de Surveillance Intelligente Multi-Agent

---

## 1. Contexte du projet

Ce projet de fin d'études (PFE) s'inscrit dans le cadre du Master MSID (Master Sciences de l'Informatique et de la Décision) spécialité TAM (Technologies Avancées et Mobiles) à l'Université Mohammed V de Rabat.

L'objectif est de concevoir et implémenter une **plateforme de surveillance urbaine intelligente** exploitant des techniques de vision par ordinateur et d'intelligence artificielle pour détecter automatiquement des comportements anormaux dans des flux vidéo.

---

## 2. Problématique

La surveillance manuelle de flux vidéo en temps réel est :
- **Coûteuse** : nécessite du personnel formé 24h/24
- **Non fiable** : fatigue visuelle, réduction de l'attention après 20 minutes
- **Limitée** : un opérateur ne peut surveiller efficacement plus de 4 écrans simultanément
- **Réactive** : détection après l'incident, pas avant

La solution proposée automatise la détection et l'alerting, permettant à un opérateur de gérer 50+ caméras simultanément.

---

## 3. Architecture Multi-Agent

Le système adopte une architecture **multi-agent distribuée** composée de 5 agents spécialisés :

### Agent 1 — Perception (YOLOv8)
- Rôle : Détection d'objets et de personnes frame-by-frame
- Technologie : YOLOv8n (nano), optimisé pour CPU
- Classes détectées : 80 classes COCO (filtrées selon contexte)
- Modèle : `yolov8n.pt` (6.2 Mo)

### Agent 2 — Tracking (DeepSORT)
- Rôle : Suivi des entités détectées entre les frames
- Technologie : Deep SORT (Deep Simple Online and Realtime Tracking)
- Fonctionnement : Association des détections YOLO avec des trajectoires

### Agent 3 — Analyse Comportementale
- Rôle : Classification des comportements à partir des trajectoires
- Comportements détectés : chute, attroupement, objet abandonné
- Logique : règles heuristiques calibrées empiriquement

### Agent 4 — Décision & Alerting
- Rôle : Génération des alertes et persistance en base de données
- Anti-duplication : système de cooldown par type d'événement
- Captures annotées : bounding boxes + bannières colorées

### Agent 5 — Interface & API
- Rôle : Exposition REST API + interface utilisateur web
- Technologie : Flask (backend) + React 18 (frontend)

---

## 4. Stack Technique

### Backend
| Composant     | Technologie      | Version  |
|---------------|------------------|----------|
| Serveur web   | Flask            | 3.0.0    |
| Base de données | MongoDB        | 6.0      |
| ORM           | PyMongo (direct) | 4.6.1    |
| Auth          | JWT (PyJWT)      | 2.13.0   |
| Vision        | OpenCV           | 4.8.1    |
| IA            | YOLOv8 (Ultralytics) | 8.1.18 |
| Data Science  | Pandas           | 2.0+     |
| Sécurité pass | bcrypt           | 4.1.2    |

### Frontend
| Composant     | Technologie       | Version  |
|---------------|-------------------|----------|
| Framework     | React             | 18.2.0   |
| Routing       | React Router DOM  | 6.20.0   |
| State         | Zustand           | 4.4.1    |
| HTTP          | Fetch API natif   | —        |
| Graphes       | Recharts          | 2.10.3   |
| CSS           | Tailwind CSS      | 3.3.6    |
| Bundler       | Vite              | 5.0.7    |
| Icons         | Lucide React      | 0.292.0  |
| Notifications | React Hot Toast   | 2.4.1    |

### Infrastructure
| Composant     | Technologie      |
|---------------|------------------|
| Container     | Docker multi-stage |
| Orchestration | Docker Compose   |
| Reverse Proxy | Nginx            |
| CI/CD         | GitHub Actions   |
| OS Dev        | Windows 11 x64   |

---

## 5. Modèle de Données MongoDB

### Collection `user`
```json
{
  "_id": ObjectId,
  "email": String,
  "username": String,
  "password": BcryptHash,
  "full_name": String,
  "role": "admin|user",
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### Collection `video`
```json
{
  "_id": ObjectId,
  "title": String,
  "filename": String,
  "filepath": String,
  "uploaded_by": ObjectId (ref: user),
  "duration": Float,
  "fps": Float,
  "resolution": String,
  "file_size": Integer,
  "status": "uploaded",
  "created_at": DateTime
}
```

### Collection `analysis`
```json
{
  "_id": ObjectId,
  "video": ObjectId (ref: video),
  "user": ObjectId (ref: user),
  "status": "pending|processing|completed|failed",
  "progress": Integer (0-100),
  "falls_detected": Integer,
  "crowds_detected": Integer,
  "abandoned_objects": Integer,
  "total_events": Integer,
  "events_timeline": Array,
  "processing_time": Float,
  "average_fps": Float,
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### Collection `alert`
```json
{
  "_id": ObjectId,
  "analysis": ObjectId (ref: analysis),
  "event_type": "fall|crowding|abandoned",
  "risk_level": "high|medium|low",
  "frame_id": Integer,
  "timestamp": Float,
  "status": "active",
  "capture": String (filename),
  "created_at": DateTime
}
```

---

## 6. Algorithmes de Détection

### Détection de chute
```
Condition : bbox.height / bbox.width < 0.65
Interprétation : personne debout → ratio ~2.5-3.5
                 personne tombée → ratio ~0.4-0.6
Cooldown : 300 frames (~10s @ 30fps)
```

### Détection d'attroupement
```
Condition : count(persons) >= 5 AND
            EXISTS group WHERE
              |group| >= 5 AND
              FORALL i,j IN group: distance(center_i, center_j) < 200px
Cooldown : 90 frames (~3s @ 30fps)
```

### Détection d'objet abandonné
```
Condition : cls IN {backpack, umbrella, handbag, suitcase, skateboard, bottle, phone}
            AND movement < 50px
            AND immobile_frames >= 22
            AND NOT already_alerted
Cooldown global : 900 frames (~30s @ 30fps)
Grille de tracking : cellules 100×100px pour stabilité
```

---

## 7. API REST

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| POST | `/api/auth/login` | Connexion JWT | Non |
| GET | `/api/videos` | Liste vidéos | JWT |
| POST | `/api/videos/upload` | Upload vidéo | JWT |
| DELETE | `/api/videos/<id>` | Supprimer vidéo | JWT |
| GET | `/api/videos/<id>/file` | Streaming vidéo | JWT/Query |
| POST | `/api/analyses/create` | Lancer analyse | JWT |
| GET | `/api/analyses/<id>` | État analyse | JWT |
| GET | `/api/analyses/<id>/alerts` | Alertes analyse | JWT |
| GET | `/api/analyses/statistics` | Stats globales | JWT |
| GET | `/api/analyses/statistics/<id>` | Stats Pandas | JWT |
| GET | `/api/analyses/benchmarks` | Benchmarks YOLO | Non |
| GET | `/api/analyses/<id>/trends` | Tendances | JWT |
| GET | `/api/analyses/<id>/metrics-export` | Export CSV | JWT |
| GET | `/api/captures/<filename>` | Image capture | Non |
| GET | `/api/users` | Liste users | Admin |
| POST | `/api/users` | Créer user | Admin |
| PUT | `/api/users/<id>` | Modifier user | Admin |
| DELETE | `/api/users/<id>` | Supprimer user | Admin |
