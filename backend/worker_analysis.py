"""
Worker d'analyse vidéo réel — YOLO → détection événements → captures annotées → alertes MongoDB.
Fixes: anti-duplication stricte, objets portables uniquement, bboxes dessinées sur captures.
"""

import cv2
import time
import os
import logging
import threading
from datetime import datetime, timezone
from pymongo import MongoClient
from bson.objectid import ObjectId

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURES_DIR = os.path.join(BASE_DIR, 'captures')
os.makedirs(CAPTURES_DIR, exist_ok=True)

# ── Seuils calibrés ─────────────────────────────────────────────────────
FALL_RATIO_THRESHOLD = 0.65   # h/w < 0.65 → personne tombée (evite faux positifs angle defavorable)
CROWD_MIN_PERSONS = 5      # 5+ personnes proches = attroupement
CROWD_PROXIMITY_PX = 200
ABANDONED_MOVE_PX = 50     # mouvement max (px) pour "immobile"
ABANDONED_MIN_FRAMES = 22     # frames traitées immobiles avant alerte
CONFIDENCE_MIN = 0.25
FRAME_SKIP = 3

# Cooldown en FRAMES RÉELLES entre deux alertes du même type
FALL_COOLDOWN = 300   # ~10s @ 30fps — evite double detection meme chute
CROWD_COOLDOWN = 90
ABANDONED_COOLDOWN = 900   # ~30s @ 30fps — prevents re-alerting same drifting object

# Objets PORTABLES uniquement (pas les meubles/écrans fixes)
OBJECT_CLASSES = {
    24,  # backpack
    25,  # umbrella
    26,  # handbag
    28,  # suitcase
    36,  # skateboard
    39,  # bottle
    67,  # cell phone
}

COLORS = {
    'fall': (0, 0, 220),   # rouge
    'crowding': (0, 140, 255),  # orange
    'abandoned': (0, 200, 50),  # vert
}
LABELS_FR = {
    'fall': 'CHUTE DETECTEE',
    'crowding': 'ATTROUPEMENT',
    'abandoned': 'OBJET ABANDONNE',
}


def _dist(c1, c2):
    return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2) ** 0.5


def _save_capture(frame, analysis_id, frame_id, event_type, bboxes=None, centers=None):
    """Sauvegarde une capture JPEG avec bboxes/cercles annotés."""
    try:
        color = COLORS.get(event_type, (100, 100, 100))
        img = frame.copy()

        # Dessiner les bboxes / cercles sur les objets détectés
        if bboxes:
            for bbox in bboxes:
                x1, y1, x2, y2 = map(int, bbox)
                # Rectangles épais + coins accentués
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
                # Coins marqués
                L = max(20, (x2 - x1) // 5)
                for px, py, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
                    cv2.line(img, (px, py), (px + dx * L, py), color, 4)
                    cv2.line(img, (px, py), (px, py + dy * L), color, 4)

        if centers:
            for cx, cy in centers:
                cv2.circle(img, (int(cx), int(cy)), 18, color, 3)
                cv2.circle(img, (int(cx), int(cy)), 5, color, -1)

        # Bandeau info en haut
        h, w = img.shape[:2]
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), color, -1)
        cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)
        cv2.putText(img, LABELS_FR.get(event_type, event_type.upper()),
                    (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(img, f"frame {frame_id}",
                    (w - 140, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 1)

        filename = f"{analysis_id}_{frame_id}_{event_type}.jpg"
        cv2.imwrite(os.path.join(CAPTURES_DIR, filename), img,
                    [cv2.IMWRITE_JPEG_QUALITY, 82])
        return filename
    except Exception as e:
        log.warning(f"Capture failed: {e}")
        return None


def run_analysis(analysis_id: str, video_path: str,
                 mongo_uri: str = 'mongodb://localhost:27017/'):

    client = MongoClient(mongo_uri)
    db = client['surveillance_db']
    aid = ObjectId(analysis_id)

    def update(fields):
        db.analysis.update_one(
            {'_id': aid},
            {'$set': {**fields, 'updated_at': datetime.now(timezone.utc)}}
        )

    update({'status': 'processing', 'progress': 0})

    try:
        from ultralytics import YOLO
        model = YOLO(os.path.join(BASE_DIR, 'yolov8n.pt'))

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            update({'status': 'failed', 'error': 'Cannot open video'})
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        t_start = time.time()

        falls = crowds = abandoned_count = 0
        timeline = []

        # Cooldowns : frame réelle du dernier déclenchement
        last_alert = {'fall': -9999, 'crowding': -9999, 'abandoned': -9999}

        # Tracking objets portables : key → {immobile_frames, last_cx, last_cy, alerted, bbox}
        obj_track = {}

        frame_id = 0
        last_progress = -1

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_id += 1

            progress = int((frame_id / total_frames) * 100)
            if progress - last_progress >= 5:
                update({'progress': progress,
                        'falls_detected': falls,
                        'crowds_detected': crowds,
                        'abandoned_objects': abandoned_count,
                        'total_events': falls + crowds + abandoned_count})
                last_progress = progress

            if frame_id % FRAME_SKIP != 0:
                continue

            # ── YOLO ─────────────────────────────────────────────────────
            results = model.predict(
                frame, imgsz=640, device='cpu', half=False,
                verbose=False, conf=CONFIDENCE_MIN,
            )[0]

            persons = []
            objects = []

            for box in results.boxes:
                cls = int(box.cls[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                det = {'bbox': [x1, y1, x2, y2], 'center': [cx, cy], 'cls': cls}
                if cls == 0:
                    persons.append(det)
                elif cls in OBJECT_CLASSES:
                    objects.append(det)

            ts = round(frame_id / fps, 2)
            events_this_frame = []  # (type, risk, bboxes, centers)

            # ── Règle 1 : Chute — max 1 alerte par frame ─────────────────
            if (frame_id - last_alert['fall']) > FALL_COOLDOWN:
                fallen = []
                for p in persons:
                    x1, y1, x2, y2 = p['bbox']
                    ratio = max(y2 - y1, 1) / max(x2 - x1, 1)
                    if ratio < FALL_RATIO_THRESHOLD:
                        fallen.append(p)
                if fallen:
                    events_this_frame.append((
                        'fall', 'high',
                        [p['bbox'] for p in fallen],
                        None,
                    ))

            # ── Règle 2 : Attroupement — max 1 alerte par frame ──────────
            if (len(persons) >= CROWD_MIN_PERSONS
                    and (frame_id - last_alert['crowding']) > CROWD_COOLDOWN):
                centers = [p['center'] for p in persons]
                used = set()
                crowd_group = None
                for i, c in enumerate(centers):
                    if i in used:
                        continue
                    grp = [i]
                    for j, c2 in enumerate(centers):
                        if j != i and j not in used and _dist(c, c2) < CROWD_PROXIMITY_PX:
                            grp.append(j)
                            used.add(j)
                    used.add(i)
                    if len(grp) >= CROWD_MIN_PERSONS:
                        crowd_group = grp
                        break
                if crowd_group:
                    events_this_frame.append((
                        'crowding', 'medium',
                        [persons[i]['bbox'] for i in crowd_group],
                        [persons[i]['center'] for i in crowd_group],
                    ))

            # ── Règle 3 : Objet abandonné ─────────────────────────────────
            seen_keys = set()
            abandoned_trigger = None

            for obj in objects:
                cx, cy = obj['center']
                cls = obj['cls']
                # Grille 100px pour stabilité
                key = f"{cls}_{cx // 100}_{cy // 100}"
                seen_keys.add(key)

                if key not in obj_track:
                    obj_track[key] = {
                        'immobile_frames': 0,
                        'last_cx': cx, 'last_cy': cy,
                        'alerted': False,
                        'bbox': obj['bbox'],
                    }

                trk = obj_track[key]
                move = _dist([cx, cy], [trk['last_cx'], trk['last_cy']])

                if move <= ABANDONED_MOVE_PX:
                    trk['immobile_frames'] += 1
                    trk['bbox'] = obj['bbox']  # màj bbox
                else:
                    trk['immobile_frames'] = 0
                    trk['alerted'] = False
                trk['last_cx'], trk['last_cy'] = cx, cy

                # Un seul objet abandonné par frame, et cooldown global
                if (trk['immobile_frames'] >= ABANDONED_MIN_FRAMES
                        and not trk['alerted']
                        and (frame_id - last_alert['abandoned']) > ABANDONED_COOLDOWN
                        and abandoned_trigger is None):
                    abandoned_trigger = (trk['bbox'],)
                    trk['alerted'] = True

            if abandoned_trigger:
                events_this_frame.append((
                    'abandoned', 'medium',
                    list(abandoned_trigger),
                    None,
                ))

            # Purger les objets disparus
            for key in list(obj_track.keys()):
                if key not in seen_keys:
                    obj_track[key]['immobile_frames'] = max(
                        0, obj_track[key]['immobile_frames'] - 1)

            # ── Sauvegarder les événements ────────────────────────────────
            for ev_type, risk, bboxes, centers in events_this_frame:
                # Mettre à jour le cooldown IMMÉDIATEMENT pour éviter doublons
                last_alert[ev_type] = frame_id

                capture_file = _save_capture(
                    frame.copy(), analysis_id, frame_id,
                    ev_type, bboxes=bboxes, centers=centers
                )

                if ev_type == 'fall':
                    falls += 1
                elif ev_type == 'crowding':
                    crowds += 1
                elif ev_type == 'abandoned':
                    abandoned_count += 1

                db.alert.insert_one({
                    'analysis': aid,
                    'event_type': ev_type,
                    'risk_level': risk,
                    'frame_id': frame_id,
                    'timestamp': ts,
                    'status': 'active',
                    'capture': capture_file,
                    'created_at': datetime.now(timezone.utc),
                })
                timeline.append({'event_type': ev_type, 'frame_id': frame_id,
                                 'timestamp': ts})

        cap.release()
        proc_time = round(time.time() - t_start, 2)

        update({
            'status': 'completed',
            'progress': 100,
            'falls_detected': falls,
            'crowds_detected': crowds,
            'abandoned_objects': abandoned_count,
            'total_events': falls + crowds + abandoned_count,
            'events_timeline': timeline[:100],
            'processing_time': proc_time,
            'average_fps': round(total_frames / max(proc_time, 1), 1),
        })
        log.info(f"[Worker] {analysis_id} OK — chutes={falls} foules={crowds} objets={abandoned_count}")

    except Exception as e:
        log.error(f"[Worker] Erreur {analysis_id}: {e}", exc_info=True)
        update({'status': 'failed', 'error': str(e)})
    finally:
        client.close()


def start_analysis_thread(analysis_id: str, video_path: str):
    t = threading.Thread(target=run_analysis, args=(analysis_id, video_path), daemon=True)
    t.start()
    return t
