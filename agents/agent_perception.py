"""
Agent Perception — Détection d'objets via YOLOv8n (optimisé CPU i7)
Rôle : Capturer le flux vidéo, détecter les objets, publier les détections sur Redis.
Canal Redis : 'detections'
"""

import cv2
import redis
import json
import time
import os
import logging
import argparse
from datetime import datetime
from collections import Counter
from ultralytics import YOLO
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AgentPerception] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

# Classes COCO retenues pour la surveillance urbaine
CLASSES_SURVEILLANCE = {
    0:  "person",
    1:  "bicycle",
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
    14: "bird",
    15: "cat",
    16: "dog",
}

REDIS_CHANNEL    = "channel:detections"   # aligné avec agent_tracking
CONFIDENCE_MIN   = 0.25       # abaissé pour détecter plus de personnes
IOU_THRESHOLD    = 0.45       # NMS : évite les doublons sans supprimer trop
MODEL_PATH       = "yolov8n.pt"
FRAME_SKIP       = 3
IMG_SIZE         = 640        # résolution max : meilleure détection des petits objets
REDIS_MAX_PPS    = 10
FPS_LOG_INTERVAL = 3.0
CAM_ID           = "CAM_01"
DEBUG            = False      # True pour afficher les stats brutes par frame


class AgentPerception:
    """
    Agent de perception CPU-optimisé.

    Stratégie vitesse :
    - Toutes les frames sont LUES et AFFICHÉES à la vitesse réelle de la vidéo.
    - YOLO tourne seulement sur 1 frame / FRAME_SKIP (charge CPU réduite).
    - Le dernier résultat YOLO est réutilisé pour les frames intermédiaires.
    - time.sleep() compense le temps restant dans chaque intervalle de frame.
    """

    def __init__(self, source: str | int = 0, display: bool = False, debug: bool = False):
        self.source  = source
        self.display = display
        self.debug   = debug
        self.model   = self._load_model()
        self.redis_client = self._connect_redis()

        self.frame_count      = 0
        self.processed_count  = 0
        self.total_detections = 0
        self.running          = False

        # Throttle Redis
        self._last_publish_time = 0.0
        self._publish_interval  = 1.0 / REDIS_MAX_PPS

        # FPS tracking (frames affichées)
        self._fps_t0     = time.time()
        self._fps_frames = 0

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_model(self) -> YOLO:
        log.info("Chargement YOLOv8n (CPU, imgsz=%d)…", IMG_SIZE)
        model = YOLO(MODEL_PATH)
        import numpy as np
        model(np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype="uint8"),
              imgsz=IMG_SIZE, device="cpu", half=False, verbose=False)
        log.info("Modèle YOLOv8n prêt (device=cpu).")
        return model

    def _connect_redis(self) -> redis.Redis:
        host   = os.getenv("REDIS_HOST", "localhost")
        port   = int(os.getenv("REDIS_PORT", 6379))
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()
        log.info("Redis connecté (%s:%s).", host, port)
        return client

    # ------------------------------------------------------------------
    # Détection
    # ------------------------------------------------------------------

    def _detect(self, frame) -> list:
        results = self.model.predict(
            frame,
            imgsz=IMG_SIZE,
            device="cpu",
            half=False,
            verbose=False,
            conf=CONFIDENCE_MIN,
            iou=IOU_THRESHOLD,
            classes=list(CLASSES_SURVEILLANCE.keys()),  # filtre COCO côté YOLO
        )[0]

        raw_count = len(results.boxes)
        detections = []

        for box in results.boxes:
            class_id   = int(box.cls[0])
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append({
                "class_id":   class_id,
                "label":      CLASSES_SURVEILLANCE[class_id],
                "confidence": round(confidence, 3),
                "bbox":       [x1, y1, x2, y2],
                "center":     [(x1 + x2) // 2, (y1 + y2) // 2],
            })

        if self.debug:
            persons = sum(1 for d in detections if d["class_id"] == 0)
            print(
                f"[DEBUG] Brut: {raw_count} boîtes | "
                f"Après filtre: {len(detections)} | "
                f"Personnes: {persons}"
            )

        return detections

    # ------------------------------------------------------------------
    # Publication Redis (throttlée, seulement si détections non vides)
    # ------------------------------------------------------------------

    def _publish(self, detections: list, frame_id: int):
        if not detections:
            return
        now = time.monotonic()
        if now - self._last_publish_time < self._publish_interval:
            return
        self._last_publish_time = now

        self.redis_client.publish(REDIS_CHANNEL, json.dumps({
            "agent":      "perception",
            "cam_id":     CAM_ID,
            "frame_id":   frame_id,
            "timestamp":  datetime.utcnow().isoformat(),
            "detections": detections,
            "count":      len(detections),
        }))

    # ------------------------------------------------------------------
    # Compteur FPS terminal (frames affichées)
    # ------------------------------------------------------------------

    def _log_fps(self, last_detections: list):
        self._fps_frames += 1
        elapsed = time.time() - self._fps_t0
        if elapsed >= FPS_LOG_INTERVAL:
            fps    = self._fps_frames / elapsed
            counts = Counter(d["label"] for d in last_detections)
            det_str = ", ".join(f"{v} {k}" for k, v in counts.items()) or "aucune"
            print(
                f"[{CAM_ID}] FPS affichage: {fps:.1f} | "
                f"YOLO: ~{fps / FRAME_SKIP:.1f} FPS | "
                f"Détections: {det_str}"
            )
            self._fps_frames = 0
            self._fps_t0     = time.time()

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def run(self, max_frames: int = None):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            log.error("Impossible d'ouvrir la source : %s", self.source)
            return

        fps_video = cap.get(cv2.CAP_PROP_FPS) or 25.0
        delay     = 1.0 / fps_video          # durée théorique d'une frame (secondes)

        log.info("Source ouverte — FPS vidéo: %.1f | délai/frame: %.1f ms",
                 fps_video, delay * 1000)
        log.info("Agent Perception démarré [%s]. Canal Redis : '%s'", CAM_ID, REDIS_CHANNEL)

        self.running      = True
        last_detections   = []   # résultat YOLO réutilisé sur les frames intermédiaires

        try:
            while self.running:
                t_frame_start = time.monotonic()

                ret, frame = cap.read()
                if not ret:
                    log.info("Fin du flux vidéo.")
                    break

                self.frame_count += 1

                # --- YOLO sur 1 frame / FRAME_SKIP ---
                if self.frame_count % FRAME_SKIP == 0:
                    last_detections = self._detect(frame)
                    self.processed_count  += 1
                    self.total_detections += len(last_detections)
                    self._publish(last_detections, self.frame_count)

                # --- Affichage de TOUTES les frames avec le dernier résultat YOLO ---
                self._log_fps(last_detections)

                if self.display:
                    self._draw(frame, last_detections)
                    cv2.imshow(f"Agent Perception [{CAM_ID}]", frame)

                # --- Contrôle de vitesse : sleep pour respecter le FPS source ---
                elapsed    = time.monotonic() - t_frame_start
                sleep_time = delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # waitKey(1) suffit ici car le sleep gère déjà la synchronisation
                if self.display and (cv2.waitKey(1) & 0xFF == ord("q")):
                    log.info("Arrêt demandé (touche q).")
                    break

                if max_frames and self.processed_count >= max_frames:
                    break

        except KeyboardInterrupt:
            log.info("Interruption clavier.")
        finally:
            self.running = False
            cap.release()
            if self.display:
                cv2.destroyAllWindows()
            log.info(
                "Arrêt — Frames lues: %d | YOLO: %d | Détections: %d",
                self.frame_count, self.processed_count, self.total_detections,
            )

    # ------------------------------------------------------------------
    # Affichage OpenCV
    # ------------------------------------------------------------------

    def _draw(self, frame, detections: list):
        COLORS = {
            "person":     (0, 255, 0),
            "car":        (255, 128, 0),
            "bus":        (0, 128, 255),
            "truck":      (0, 0, 255),
            "motorcycle": (255, 0, 255),
            "bicycle":    (255, 255, 0),
        }
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = COLORS.get(det["label"], (200, 200, 200))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame, f"{det['label']} {det['confidence']:.0%}",
                (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2
            )
        cv2.putText(
            frame,
            f"{CAM_ID} | det:{len(detections)} | f:{self.frame_count}",
            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
        )

    # ------------------------------------------------------------------
    # Statut
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return {
            "agent":            "perception",
            "cam_id":           CAM_ID,
            "running":          self.running,
            "frames_read":      self.frame_count,
            "frames_processed": self.processed_count,
            "total_detections": self.total_detections,
            "redis_channel":    REDIS_CHANNEL,
            "model":            MODEL_PATH,
            "imgsz":            IMG_SIZE,
            "device":           "cpu",
            "frame_skip":       FRAME_SKIP,
            "redis_max_pps":    REDIS_MAX_PPS,
        }


# ----------------------------------------------------------------------
# Point d'entrée
# ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Perception — YOLOv8n CPU")
    parser.add_argument("source", nargs="?", default=0,
                        help="Chemin vidéo ou index webcam (défaut: 0)")
    parser.add_argument("--display", action="store_true",
                        help="Afficher la fenêtre OpenCV")
    parser.add_argument("--max-frames", type=int, default=None,
                        help="Arrêter après N frames YOLO traitées")
    parser.add_argument("--debug", action="store_true",
                        help="Afficher les stats brutes de détection par frame")
    args = parser.parse_args()

    source = int(args.source) if str(args.source).isdigit() else args.source

    agent = AgentPerception(source=source, display=args.display, debug=args.debug)
    log.info("Statut initial : %s", agent.status())
    agent.run(max_frames=args.max_frames)
