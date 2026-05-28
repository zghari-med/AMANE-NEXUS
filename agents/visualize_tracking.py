"""
Visualisation Tracking — YOLOv8n + DeepSORT sur vidéo
Affiche la vidéo avec les bboxes, IDs persistants, vitesses et trajectoires.
Usage : python agents/visualize_tracking.py videos/virat.mp4
"""

import cv2
import time
import math
import argparse
import numpy as np
from collections import deque, defaultdict
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# ------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------
MODEL_PATH     = "yolov8n.pt"
CONF           = 0.25
IOU            = 0.45
IMG_SIZE       = 640
FRAME_SKIP     = 3
TRAIL_LEN      = 30        # longueur de la trajectoire affichée
CLASSES_IDS    = [0]       # 0 = person uniquement

# Palette de couleurs HSV → BGR (une couleur par ID)
def id_to_color(track_id: int):
    hue = (track_id * 47) % 180
    hsv = np.uint8([[[hue, 220, 255]]])
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))


def run(source, display=True, output_path=None):
    # Modèle YOLO
    model = YOLO(MODEL_PATH)
    # Warm-up
    model(np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype="uint8"),
          imgsz=IMG_SIZE, device="cpu", half=False, verbose=False)

    # DeepSORT
    tracker = DeepSort(max_age=20, n_init=3, nn_budget=100, max_iou_distance=0.7)
    _u = np.ones(128, dtype=np.float32)
    _u /= np.linalg.norm(_u)

    # Vidéo
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[ERREUR] Impossible d'ouvrir : {source}")
        return

    fps_src  = cap.get(cv2.CAP_PROP_FPS) or 24.0
    W        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H        = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    delay    = 1.0 / fps_src

    # Writer vidéo (optionnel)
    writer = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps_src, (W, H))
        print(f"[INFO] Enregistrement → {output_path}")

    # Historique trajectoires {track_id: deque([(cx,cy)])}
    trails    = defaultdict(lambda: deque(maxlen=TRAIL_LEN))
    # Vitesse {track_id: float}
    speeds    = {}

    frame_count   = 0
    last_dets     = []
    last_tracks   = []

    # FPS compteur
    fps_t0, fps_n = time.time(), 0

    print(f"[INFO] Vidéo : {source} | {W}x{H} @ {fps_src:.0f} FPS")
    print("[INFO] Touche Q pour quitter.")

    while True:
        t_start = time.monotonic()
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # --- YOLO (1 frame / FRAME_SKIP) ---
        if frame_count % FRAME_SKIP == 0:
            results  = model.predict(
                frame, imgsz=IMG_SIZE, device="cpu",
                half=False, verbose=False,
                conf=CONF, iou=IOU, classes=CLASSES_IDS,
            )[0]

            raw_dets = []
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                raw_dets.append(
                    ([x1, y1, x2 - x1, y2 - y1], float(box.conf[0]), "person")
                )
            last_dets = raw_dets

            # --- DeepSORT ---
            embeds  = [_u.copy() for _ in raw_dets]
            tracks  = tracker.update_tracks(raw_dets, embeds=embeds)
            confirmed = [t for t in tracks if t.is_confirmed()]
            last_tracks = confirmed

            # Mettre à jour trajectoires et vitesses
            for t in confirmed:
                tid          = int(t.track_id)
                x1,y1,x2,y2 = map(int, t.to_ltrb())
                cx, cy       = (x1 + x2) // 2, (y1 + y2) // 2
                prev         = trails[tid][-1] if trails[tid] else None
                spd          = math.hypot(cx - prev[0], cy - prev[1]) if prev else 0.0
                speeds[tid]  = round(spd, 1)
                trails[tid].append((cx, cy))

        # --- Dessin sur TOUTES les frames ---
        active_ids = set()
        for t in last_tracks:
            tid          = int(t.track_id)
            active_ids.add(tid)
            x1,y1,x2,y2 = map(int, t.to_ltrb())
            cx, cy       = (x1 + x2) // 2, (y1 + y2) // 2
            color        = id_to_color(tid)
            spd          = speeds.get(tid, 0.0)

            # Bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label ID + vitesse
            label = f"ID:{tid}  v:{spd:.0f}px"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            # Centre
            cv2.circle(frame, (cx, cy), 4, color, -1)

        # Trajectoires
        for tid, trail in trails.items():
            if tid not in active_ids:
                continue
            pts = list(trail)
            for i in range(1, len(pts)):
                alpha = i / len(pts)
                c = id_to_color(tid)
                thick = max(1, int(alpha * 3))
                cv2.line(frame, pts[i - 1], pts[i], c, thick)

        # HUD — compteur en haut à gauche
        fps_n += 1
        elapsed = time.time() - fps_t0
        if elapsed >= 1.0:
            fps_disp = fps_n / elapsed
            fps_n, fps_t0 = 0, time.time()
        else:
            fps_disp = fps_n / max(elapsed, 0.001)

        n_persons = len(last_tracks)
        hud = (f"Frame:{frame_count}  "
               f"Personnes:{n_persons}  "
               f"FPS:{fps_disp:.1f}  "
               f"YOLO:~{fps_disp/FRAME_SKIP:.1f}")
        cv2.rectangle(frame, (0, 0), (len(hud) * 10, 28), (0, 0, 0), -1)
        cv2.putText(frame, hud, (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2)

        if writer:
            writer.write(frame)

        if display:
            cv2.imshow("YOLOv8n + DeepSORT Tracking", frame)

        # Contrôle vitesse
        elapsed_frame = time.monotonic() - t_start
        wait = max(0.0, delay - elapsed_frame)
        time.sleep(wait)

        if display and (cv2.waitKey(1) & 0xFF == ord("q")):
            print("[INFO] Arrêt demandé.")
            break

    cap.release()
    if writer:
        writer.release()
        print(f"[INFO] Vidéo sauvegardée : {output_path}")
    if display:
        cv2.destroyAllWindows()
    print(f"[INFO] Terminé. Frames traitées : {frame_count}")


# ------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualisation YOLO + DeepSORT")
    parser.add_argument("source", help="Chemin vidéo ou index webcam")
    parser.add_argument("--no-display", action="store_true",
                        help="Désactiver la fenêtre (headless)")
    parser.add_argument("--save", default=None,
                        help="Sauvegarder la vidéo annotée (ex: output.mp4)")
    args = parser.parse_args()

    src = int(args.source) if str(args.source).isdigit() else args.source
    run(source=src, display=not args.no_display, output_path=args.save)
