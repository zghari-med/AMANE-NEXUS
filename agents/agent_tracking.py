"""
Agent Tracking — Suivi multi-personnes via DeepSORT
Rôle : S'abonner aux détections Redis, attribuer des IDs persistants,
       calculer vitesse et publier les tracks sur Redis.
Canal entrée  : channel:detections
Canal sortie  : channel:tracks
"""

import redis
import json
import time
import os
import math
import logging
import threading
import numpy as np
from queue import Queue, Empty
from datetime import datetime
from collections import deque
from deep_sort_realtime.deepsort_tracker import DeepSort
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AgentTracking] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------
CHANNEL_IN       = "channel:detections"   # abonnement
CHANNEL_OUT      = "channel:tracks"       # publication
CAMERA_ID        = "cam_01"
LOG_INTERVAL     = 3.0                    # secondes entre deux logs terminal
QUEUE_MAX        = 50                     # max messages en attente
SPEED_HISTORY    = 5                      # frames pour lisser la vitesse

# Paramètres DeepSORT
DEEPSORT_MAX_AGE  = 20   # frames avant de supprimer un track perdu
DEEPSORT_N_INIT   = 3    # frames consécutives pour confirmer un track
DEEPSORT_BUDGET   = 100  # taille max galerie d'apparence

# Embedding neutre normalisé — np.zeros provoque NaN dans la distance cosinus.
# Ce vecteur constant désactive l'apparence et laisse Kalman+IoU gérer le tracking.
_UNIT = np.ones(128, dtype=np.float32)
_UNIT /= np.linalg.norm(_UNIT)
DUMMY_EMBED = _UNIT


class AgentTracking:
    """
    Agent de tracking CPU-optimisé.

    Architecture :
      Thread Redis (listener)  →  Queue  →  Thread principal (DeepSORT)
    """

    def __init__(self):
        self.redis_pub  = self._connect_redis()   # client publication
        self.redis_sub  = self._connect_redis()   # client abonnement (bloquant)
        self.tracker    = self._init_tracker()

        self.queue      = Queue(maxsize=QUEUE_MAX)
        self.running    = False

        # Historique des centres par track_id pour calcul de vitesse
        # {track_id: deque([(cx, cy), ...], maxlen=SPEED_HISTORY)}
        self._centers: dict[int, deque] = {}

        # Stats terminal
        self._log_t0        = time.time()
        self._log_frames    = 0
        self._last_ids: list = []

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _connect_redis(self) -> redis.Redis:
        host   = os.getenv("REDIS_HOST", "localhost")
        port   = int(os.getenv("REDIS_PORT", 6379))
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()
        return client

    def _init_tracker(self) -> DeepSort:
        log.info(
            "Initialisation DeepSORT (max_age=%d, n_init=%d, nn_budget=%d)…",
            DEEPSORT_MAX_AGE, DEEPSORT_N_INIT, DEEPSORT_BUDGET,
        )
        tracker = DeepSort(
            max_age=DEEPSORT_MAX_AGE,
            n_init=DEEPSORT_N_INIT,
            nn_budget=DEEPSORT_BUDGET,
            max_iou_distance=0.7,
        )
        log.info("DeepSORT prêt.")
        return tracker

    # ------------------------------------------------------------------
    # Thread Redis listener (producteur)
    # ------------------------------------------------------------------

    def _redis_listener(self):
        """S'abonne à CHANNEL_IN et place les messages dans la queue."""
        pubsub = self.redis_sub.pubsub()
        pubsub.subscribe(CHANNEL_IN)
        log.info("Abonné au canal Redis '%s'.", CHANNEL_IN)

        for raw in pubsub.listen():
            if not self.running:
                break
            if raw["type"] != "message":
                continue
            try:
                msg = json.loads(raw["data"])
                if self.queue.full():
                    # Priorité au plus récent : jeter le plus ancien
                    try:
                        self.queue.get_nowait()
                    except Empty:
                        pass
                self.queue.put(msg)
            except (json.JSONDecodeError, KeyError):
                continue

        pubsub.unsubscribe()
        log.info("Listener Redis arrêté.")

    # ------------------------------------------------------------------
    # Calcul de vitesse
    # ------------------------------------------------------------------

    def _update_speed(self, track_id: int, cx: int, cy: int) -> float:
        """
        Retourne la vitesse moyenne (pixels/frame) sur les SPEED_HISTORY
        dernières positions connues du track.
        """
        if track_id not in self._centers:
            self._centers[track_id] = deque(maxlen=SPEED_HISTORY)

        history = self._centers[track_id]
        speed   = 0.0

        if history:
            prev_cx, prev_cy = history[-1]
            speed = math.hypot(cx - prev_cx, cy - prev_cy)

        history.append((cx, cy))
        return round(speed, 2)

    def _cleanup_lost_tracks(self, active_ids: set):
        """Supprime l'historique des tracks qui ne sont plus actifs."""
        lost = [tid for tid in self._centers if tid not in active_ids]
        for tid in lost:
            del self._centers[tid]

    # ------------------------------------------------------------------
    # Traitement DeepSORT
    # ------------------------------------------------------------------

    def _process(self, msg: dict):
        """
        Reçoit un message de perception, applique DeepSORT,
        publie le résultat sur CHANNEL_OUT.
        """
        detections = msg.get("detections", [])
        frame_id   = msg.get("frame_id", 0)

        if not detections:
            return

        # Convertir bbox [x1,y1,x2,y2] → [x1,y1,w,h] pour DeepSORT
        # Format attendu : ([x1,y1,w,h], confidence, class_id)
        raw_dets = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            w  = x2 - x1
            h  = y2 - y1
            raw_dets.append(([x1, y1, w, h], det["confidence"], det["label"]))

        # Embeddings normalisés constants : évite la division par zéro (NaN)
        # dans la distance cosinus de DeepSORT. Résultat : tracking Kalman + IoU.
        embeds = [DUMMY_EMBED.copy() for _ in raw_dets]

        try:
            tracks = self.tracker.update_tracks(raw_dets, embeds=embeds)
        except Exception as e:
            log.warning("Erreur DeepSORT : %s", e)
            return

        # Construire la liste des tracks confirmés
        active_ids  = set()
        track_list  = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = int(track.track_id)
            active_ids.add(track_id)

            ltrb = track.to_ltrb()          # [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, ltrb)
            cx  = (x1 + x2) // 2
            cy  = (y1 + y2) // 2

            speed = self._update_speed(track_id, cx, cy)

            track_list.append({
                "id":     track_id,
                "bbox":   [x1, y1, x2, y2],
                "center": [cx, cy],
                "vitesse": speed,
            })

        # Nettoyage historique des tracks perdus
        self._cleanup_lost_tracks(active_ids)

        # Publication Redis
        payload = {
            "camera_id": CAMERA_ID,
            "frame_id":  frame_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tracks":    track_list,
            "count":     len(track_list),
        }
        self.redis_pub.publish(CHANNEL_OUT, json.dumps(payload))

        # Log terminal
        self._log_tracks(frame_id, track_list)

    # ------------------------------------------------------------------
    # Log terminal périodique
    # ------------------------------------------------------------------

    def _log_tracks(self, frame_id: int, track_list: list):
        self._log_frames += 1
        self._last_ids   = [t["id"] for t in track_list]

        elapsed = time.time() - self._log_t0
        if elapsed >= LOG_INTERVAL:
            fps = self._log_frames / elapsed
            ids_str = str(self._last_ids) if self._last_ids else "[]"
            print(
                f"[TRACKING] Frame {frame_id:>5} | "
                f"{len(track_list):>2} personne(s) | "
                f"IDs: {ids_str} | "
                f"~{fps:.1f} msg/s"
            )
            self._log_frames = 0
            self._log_t0     = time.time()

    # ------------------------------------------------------------------
    # Boucle principale (consommateur)
    # ------------------------------------------------------------------

    def run(self):
        self.running = True

        # Démarrer le thread listener Redis
        listener_thread = threading.Thread(
            target=self._redis_listener, daemon=True, name="RedisListener"
        )
        listener_thread.start()

        log.info(
            "Agent Tracking démarré. "
            "Entrée: '%s' → Sortie: '%s'",
            CHANNEL_IN, CHANNEL_OUT,
        )

        try:
            while self.running:
                try:
                    msg = self.queue.get(timeout=1.0)
                except Empty:
                    continue
                self._process(msg)

        except KeyboardInterrupt:
            log.info("Interruption clavier.")
        finally:
            self.running = False
            log.info(
                "Agent Tracking arrêté. Dernier état : %d track(s) actif(s).",
                len(self._centers),
            )

    def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    # Statut
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return {
            "agent":          "tracking",
            "camera_id":      CAMERA_ID,
            "running":        self.running,
            "channel_in":     CHANNEL_IN,
            "channel_out":    CHANNEL_OUT,
            "active_tracks":  len(self._centers),
            "last_ids":       self._last_ids,
            "deepsort": {
                "max_age":   DEEPSORT_MAX_AGE,
                "n_init":    DEEPSORT_N_INIT,
                "nn_budget": DEEPSORT_BUDGET,
            },
        }


# ----------------------------------------------------------------------
# Point d'entrée
# ----------------------------------------------------------------------

if __name__ == "__main__":
    agent = AgentTracking()
    log.info("Statut initial : %s", agent.status())
    agent.run()
