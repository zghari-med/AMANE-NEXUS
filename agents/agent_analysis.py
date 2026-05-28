"""
Agent Analyse — Détection intelligent d'événements (chutes, attroupements, objets abandonnés)
Rôle : S'abonner aux tracks DeepSORT, analyser les patterns, publier les détections.
Canal entrée  : channel:tracks
Canal sortie  : channel:analysis
"""

import redis
import json
import time
import os
import logging
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AgentAnalysis] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

# Constantes
CHANNEL_IN = "channel:tracks"
CHANNEL_OUT = "channel:analysis"
CAMERA_ID = "cam_01"
LOG_INTERVAL = 5.0

# Paramètres chutes
FALL_DETECTION = {
    "min_height_ratio": 0.4,  # si hauteur < 40% de la hauteur initiale
    "horizontal_frames": 10,  # frames consécutives en position horizontale pour confirmer chute
    "height_history": 30,  # frames d'historique pour déterminer la hauteur "normale"
}

# Paramètres attroupements
CROWDING_DETECTION = {
    "min_crowd_size": 3,  # min personnes pour un attroupement
    "density_threshold": 0.05,  # densité min (personnes / pixels²) pour une zone dense
    "proximity_distance": 100,  # pixels - distance max entre personnes d'un groupe
    "frame_confirmation": 15,  # frames consécutives pour confirmer attroupement
}

# Paramètres objets abandonnés
ABANDONED_DETECTION = {
    "min_stationary_frames": 120,  # 4-5 secondes si 25 fps
    "movement_threshold": 5,  # pixels - mouvement accepté
    "min_object_confidence": 0.3,
    "tracking_history": 200,  # frames d'historique
}


class FallDetector:
    """Détection des chutes par changement de posture."""

    def __init__(self):
        self.height_history = {}  # {track_id: deque de hauteurs}
        self.fall_state = {}  # {track_id: 'normal', 'falling', 'down'}
        self.fall_frames = defaultdict(int)  # compteur frames en position basse

    def update(self, track_id: int, bbox: list) -> dict | None:
        """
        Analyse la posture d'une personne.
        bbox: [x1, y1, x2, y2]
        Retourne un événement 'fall' si détecté.
        """
        x1, y1, x2, y2 = bbox
        height = y2 - y1

        if track_id not in self.height_history:
            self.height_history[track_id] = deque(
                maxlen=FALL_DETECTION["height_history"]
            )
            self.fall_state[track_id] = "normal"

        self.height_history[track_id].append(height)

        # Déterminer la hauteur "normale"
        if len(self.height_history[track_id]) >= 5:
            normal_height = np.median(list(self.height_history[track_id]))
        else:
            return None

        # Vérifier si posture basse (hauteur < 40% de la normale)
        if height < normal_height * FALL_DETECTION["min_height_ratio"]:
            self.fall_frames[track_id] += 1

            # Confirmer la chute après N frames
            if (self.fall_frames[track_id] >=
                FALL_DETECTION["horizontal_frames"] and
                self.fall_state[track_id] != "down"):

                self.fall_state[track_id] = "down"
                return {
                    "type": "fall",
                    "track_id": track_id,
                    "risk_level": "high",
                    "confidence": min(self.fall_frames[track_id] /
                                    FALL_DETECTION["horizontal_frames"], 1.0),
                }
        else:
            # Retour à la posture normale
            if self.fall_frames[track_id] > 0:
                self.fall_frames[track_id] = 0
            if self.fall_state[track_id] == "down":
                self.fall_state[track_id] = "normal"

        return None


class CrowdingDetector:
    """Détection des attroupements et zones denses."""

    def __init__(self):
        self.crowd_state = {}  # {crowd_id: frames_count}
        self.next_crowd_id = 1
        self.crowd_history = {}  # historique des attroupements

    def update(self, tracks: list) -> dict | None:
        """
        Détecte les attroupements parmi les tracks.
        tracks: liste de {track_id, bbox, conf}
        """
        if len(tracks) < CROWDING_DETECTION["min_crowd_size"]:
            return None

        # Grouper les personnes proches
        grouped = self._group_nearby_persons(tracks)

        events = []
        for group_idx, group in enumerate(grouped):
            if len(group) >= CROWDING_DETECTION["min_crowd_size"]:
                # Calculer densité
                bbox_group = [t["bbox"] for t in group]
                density = self._calculate_density(bbox_group)

                if density > CROWDING_DETECTION["density_threshold"]:
                    crowd_id = f"crowd_{group_idx}_{int(time.time())}"

                    event = {
                        "type": "crowding",
                        "crowd_id": crowd_id,
                        "person_count": len(group),
                        "density": density,
                        "risk_level": "medium" if len(group) < 5 else "high",
                        "track_ids": [t["track_id"] for t in group],
                    }
                    events.append(event)

        return events if events else None

    def _group_nearby_persons(self, tracks: list) -> list:
        """Groupe les personnes proches via clustering spatial."""
        if not tracks:
            return []

        grouped = []
        used = set()

        for i, track in enumerate(tracks):
            if i in used:
                continue

            group = [track]
            used.add(i)

            for j, other in enumerate(tracks):
                if j in used or j <= i:
                    continue

                dist = self._distance_between_bboxes(
                    track["bbox"], other["bbox"]
                )
                if dist < CROWDING_DETECTION["proximity_distance"]:
                    group.append(other)
                    used.add(j)

            grouped.append(group)

        return grouped

    def _distance_between_bboxes(self, bbox1: list, bbox2: list) -> float:
        """Distance euclidienne entre centres des bboxes."""
        c1 = ((bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2)
        c2 = ((bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2)
        return np.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)

    def _calculate_density(self, bboxes: list) -> float:
        """Densité = nombre d'objets / surface totale."""
        if not bboxes:
            return 0.0

        # Bounding box englobant tous les objets
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[2] for b in bboxes)
        y2 = max(b[3] for b in bboxes)

        area = max((x2 - x1) * (y2 - y1), 1)
        return len(bboxes) / area


class AbandonedDetector:
    """Détection d'objets abandonnés (immobiles)."""

    def __init__(self):
        self.object_history = {}  # {track_id: deque de positions}
        self.stationary_frames = defaultdict(int)  # compteur frames sans mouvement
        self.abandoned_state = {}  # {track_id: 'moving', 'stationary', 'abandoned'}

    def update(self, track_id: int, bbox: list, class_name: str) -> dict | None:
        """
        Détecte les objets abandonnés (pas de mouvement > N frames).
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        if track_id not in self.object_history:
            self.object_history[track_id] = deque(
                maxlen=ABANDONED_DETECTION["tracking_history"]
            )
            self.abandoned_state[track_id] = "moving"

        self.object_history[track_id].append((cx, cy))

        # Déterminer le mouvement récent
        if len(self.object_history[track_id]) >= 5:
            recent_positions = list(self.object_history[track_id])[-5:]
            movement = self._calculate_movement(recent_positions)
        else:
            movement = 0

        # Mettre à jour l'état de stationnarité
        if movement < ABANDONED_DETECTION["movement_threshold"]:
            self.stationary_frames[track_id] += 1
        else:
            self.stationary_frames[track_id] = 0

        # Détecter objet abandonné
        if (self.stationary_frames[track_id] >=
            ABANDONED_DETECTION["min_stationary_frames"] and
            self.abandoned_state[track_id] != "abandoned"):

            self.abandoned_state[track_id] = "abandoned"
            return {
                "type": "abandoned_object",
                "track_id": track_id,
                "object_type": class_name,
                "risk_level": "medium",
                "stationary_time": self.stationary_frames[track_id] / 25.0,
            }

        if movement >= ABANDONED_DETECTION["movement_threshold"]:
            self.abandoned_state[track_id] = "moving"

        return None

    def _calculate_movement(self, positions: list) -> float:
        """Calcule le mouvement entre les dernières positions."""
        if len(positions) < 2:
            return 0.0

        distances = []
        for i in range(1, len(positions)):
            d = np.sqrt(
                (positions[i][0] - positions[i-1][0]) ** 2 +
                (positions[i][1] - positions[i-1][1]) ** 2
            )
            distances.append(d)

        return np.mean(distances) if distances else 0.0


class AgentAnalysis:
    """Agent principal d'analyse."""

    def __init__(self):
        self.redis_pub = self._connect_redis()
        self.redis_sub = self._connect_redis()

        self.fall_detector = FallDetector()
        self.crowding_detector = CrowdingDetector()
        self.abandoned_detector = AbandonedDetector()

        self.running = False
        self._log_t0 = time.time()
        self._log_count = 0

    def _connect_redis(self) -> redis.Redis:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        client = redis.Redis(host=host, port=port, decode_responses=True)
        try:
            client.ping()
            log.info("Connecté à Redis ✓")
        except Exception as e:
            log.error(f"Erreur connexion Redis: {e}")
            raise
        return client

    def run(self):
        """Boucle principale de l'agent."""
        self.running = True
        pubsub = self.redis_sub.pubsub()
        pubsub.subscribe(CHANNEL_IN)

        log.info(f"Agent Analyse en écoute sur {CHANNEL_IN}")

        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    self._process_tracks(message["data"])
                    self._log_stats()
        except KeyboardInterrupt:
            log.info("Arrêt de l'agent...")
        finally:
            self.running = False
            pubsub.close()

    def _process_tracks(self, data: str):
        """Traite les données de tracking."""
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return

        tracks = payload.get("tracks", [])
        frame_id = payload.get("frame_id", 0)
        timestamp = payload.get("timestamp", time.time())

        events = []

        # Séparer les personnes et les objets
        persons = [t for t in tracks if t.get("class") == "person"]
        objects = [t for t in tracks if t.get("class") != "person"]

        # Analyse des chutes
        for person in persons:
            fall_event = self.fall_detector.update(
                person["track_id"], person["bbox"]
            )
            if fall_event:
                events.append(fall_event)

        # Analyse des attroupements
        crowd_events = self.crowding_detector.update(persons)
        if crowd_events:
            events.extend(crowd_events)

        # Analyse des objets abandonnés
        for obj in objects:
            abandoned_event = self.abandoned_detector.update(
                obj["track_id"],
                obj["bbox"],
                obj.get("class", "unknown")
            )
            if abandoned_event:
                events.append(abandoned_event)

        # Publier les événements détectés
        if events:
            for event in events:
                analysis_result = {
                    "camera_id": CAMERA_ID,
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                    "events": [event],
                    "analyzed_at": datetime.now().isoformat(),
                }

                self.redis_pub.publish(
                    CHANNEL_OUT,
                    json.dumps(analysis_result)
                )

                self._log_count += 1

    def _log_stats(self):
        """Affiche les stats."""
        if time.time() - self._log_t0 >= LOG_INTERVAL:
            log.info(
                f"Événements détectés: {self._log_count} | "
                f"Chutes tracées: {len(self.fall_detector.fall_state)} | "
                f"Objets tracés: {len(self.abandoned_detector.object_history)}"
            )
            self._log_t0 = time.time()


if __name__ == "__main__":
    agent = AgentAnalysis()
    agent.run()
