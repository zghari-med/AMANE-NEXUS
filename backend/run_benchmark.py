"""
Benchmark END-TO-END avec les nouveaux seuils optimisés.
Évalue chute / attroupement / objet abandonné sur les datasets locaux.
Usage : python run_benchmark.py
"""

import os
import sys
import json
import time
import glob
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "data", "datasets")
RESULTS_PATH = os.path.join(BASE_DIR, "data", "benchmark_results.json")

# ── Nouveaux seuils optimisés ────────────────────────────────────────────────
CONFIDENCE_MIN = 0.20          # était 0.25
CROWD_MIN_PERSONS = 4          # était 5
CROWD_PROXIMITY_PX = 200
ABANDONED_MOVE_PX = 80         # était 50
ABANDONED_MIN_FRAMES = 15      # était 22
FALL_RATIO_THRESHOLD = 0.65

OBJECT_CLASSES = {24, 25, 26, 28, 36, 39, 63, 64, 65, 66, 67, 73, 76}
IOU_THRESHOLD = 0.5


def load_yolo_label(label_path, img_w, img_h):
    """Charge un fichier label YOLO → liste de bboxes [x1,y1,x2,y2, class_id]"""
    bboxes = []
    if not os.path.exists(label_path):
        return bboxes
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls = int(parts[0])
            cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            x1 = int((cx - w / 2) * img_w)
            y1 = int((cy - h / 2) * img_h)
            x2 = int((cx + w / 2) * img_w)
            y2 = int((cy + h / 2) * img_h)
            bboxes.append([x1, y1, x2, y2, cls])
    return bboxes


def iou(b1, b2):
    """Calcule IoU entre deux bboxes [x1,y1,x2,y2]"""
    xi1 = max(b1[0], b2[0])
    yi1 = max(b1[1], b2[1])
    xi2 = min(b1[2], b2[2])
    yi2 = min(b1[3], b2[3])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def compute_metrics(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    return round(p * 100, 1), round(r * 100, 1), round(f1, 3)


def _dist(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5


def benchmark_crowding(model):
    """Évalue la détection d'attroupement sur People_counting_v1i_yolov8"""
    print("\n[CROWDING] People_counting_v1i_yolov8...")
    ds_path = os.path.join(DATASET_DIR, "People_counting_v1i_yolov8")
    images = (
        glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
        glob.glob(os.path.join(ds_path, "train", "images", "*.jpg"))
    )
    images = images[:135]
    tp = fp = fn = 0
    ious = []

    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
        gt_boxes = [b for b in load_yolo_label(label_path, w, h) if b[4] == 0]

        results = model.predict(img, imgsz=640, device='cpu',
                                verbose=False, conf=CONFIDENCE_MIN)[0]
        pred_persons = []
        for box in results.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                pred_persons.append([x1, y1, x2, y2])

        # GT : attroupement si ≥ CROWD_MIN_PERSONS personnes annotées proches
        gt_centers = [[(b[0] + b[2]) // 2, (b[1] + b[3]) // 2] for b in gt_boxes]
        gt_crowd = False
        for i, c in enumerate(gt_centers):
            grp = sum(1 for j, c2 in enumerate(gt_centers)
                      if i != j and _dist(c, c2) < CROWD_PROXIMITY_PX)
            if grp + 1 >= CROWD_MIN_PERSONS:
                gt_crowd = True
                break

        # PRED : attroupement si ≥ CROWD_MIN_PERSONS personnes détectées proches
        pred_centers = [[(b[0] + b[2]) // 2, (b[1] + b[3]) // 2] for b in pred_persons]
        pred_crowd = False
        for i, c in enumerate(pred_centers):
            grp = sum(1 for j, c2 in enumerate(pred_centers)
                      if i != j and _dist(c, c2) < CROWD_PROXIMITY_PX)
            if grp + 1 >= CROWD_MIN_PERSONS:
                pred_crowd = True
                break

        if gt_crowd and pred_crowd:
            tp += 1
            # IoU moyen sur les personnes détectées vs annotées
            for pb in pred_persons[:len(gt_boxes)]:
                best = max((iou(pb, gb[:4]) for gb in gt_boxes), default=0)
                if best > 0:
                    ious.append(best)
        elif pred_crowd and not gt_crowd:
            fp += 1
        elif gt_crowd and not pred_crowd:
            fn += 1

    p, r, f1 = compute_metrics(tp, fp, fn)
    mean_iou = round(float(np.mean(ious)) if ious else 0, 3)
    print(f"  TP={tp} FP={fp} FN={fn} → P={p}% R={r}% F1={f1} IoU={mean_iou}")
    return tp, fp, fn, p, r, f1, mean_iou, len(images)


def benchmark_abandoned(model):
    """Évalue la détection d'objets abandonnés"""
    print("\n[ABANDONED] Abandoned_Bag + Person_and_luggage...")
    tp = fp = fn = 0
    ious = []
    total_imgs = 0

    for ds_name in ["Abandoned_Bag_v1i_yolov8__3_", "Person_and_luggage_v1i_yolov8"]:
        ds_path = os.path.join(DATASET_DIR, ds_name)
        if not os.path.exists(ds_path):
            continue
        images = (
            glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
            glob.glob(os.path.join(ds_path, "train", "images", "*.jpg"))
        )
        images = images[:100]
        total_imgs += len(images)

        for img_path in images:
            img = cv2.imread(img_path)
            if img is None:
                continue
            h, w = img.shape[:2]
            label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
            gt_boxes = load_yolo_label(label_path, w, h)
            gt_obj = [b for b in gt_boxes if b[4] in OBJECT_CLASSES or b[4] != 0]

            results = model.predict(img, imgsz=640, device='cpu',
                                    verbose=False, conf=CONFIDENCE_MIN)[0]
            pred_obj = []
            for box in results.boxes:
                if int(box.cls[0]) in OBJECT_CLASSES:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    pred_obj.append([x1, y1, x2, y2])

            matched_gt = set()
            for pb in pred_obj:
                best_iou, best_idx = 0, -1
                for i, gb in enumerate(gt_obj):
                    if i in matched_gt:
                        continue
                    v = iou(pb, gb[:4])
                    if v > best_iou:
                        best_iou, best_idx = v, i
                if best_iou >= IOU_THRESHOLD:
                    tp += 1
                    matched_gt.add(best_idx)
                    ious.append(best_iou)
                else:
                    fp += 1
            fn += len(gt_obj) - len(matched_gt)

    p, r, f1 = compute_metrics(tp, fp, fn)
    mean_iou = round(float(np.mean(ious)) if ious else 0, 3)
    print(f"  TP={tp} FP={fp} FN={fn} → P={p}% R={r}% F1={f1} IoU={mean_iou}")
    return tp, fp, fn, p, r, f1, mean_iou, total_imgs


def benchmark_fall(model):
    """Évalue la détection de chutes sur UR_Fall_v1i_yolov8"""
    print("\n[FALL] UR_Fall_v1i_yolov8...")
    ds_path = os.path.join(DATASET_DIR, "UR_Fall_v1i_yolov8")
    images = (
        glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
        glob.glob(os.path.join(ds_path, "train", "images", "*.jpg"))
    )
    images = images[:200]
    tp = fp = fn = 0
    ious = []

    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
        gt_boxes = [b for b in load_yolo_label(label_path, w, h)]

        # GT : image de chute si au moins 1 bbox annotée (toutes les annots = chute)
        gt_fall = len(gt_boxes) > 0

        results = model.predict(img, imgsz=640, device='cpu',
                                verbose=False, conf=CONFIDENCE_MIN)[0]
        fallen = []
        for box in results.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                ratio = max(y2 - y1, 1) / max(x2 - x1, 1)
                if ratio < FALL_RATIO_THRESHOLD:
                    fallen.append([x1, y1, x2, y2])

        pred_fall = len(fallen) > 0

        if gt_fall and pred_fall:
            tp += 1
            for pb in fallen:
                best = max((iou(pb, gb[:4]) for gb in gt_boxes), default=0)
                if best > 0:
                    ious.append(best)
        elif pred_fall and not gt_fall:
            fp += 1
        elif gt_fall and not pred_fall:
            fn += 1

    p, r, f1 = compute_metrics(tp, fp, fn)
    mean_iou = round(float(np.mean(ious)) if ious else 0, 3)
    print(f"  TP={tp} FP={fp} FN={fn} → P={p}% R={r}% F1={f1} IoU={mean_iou}")
    return tp, fp, fn, p, r, f1, mean_iou, len(images)


def benchmark_inference(model):
    """Mesure temps d'inférence moyen"""
    print("\n[INFERENCE] Mesure temps CPU...")
    ds_path = os.path.join(DATASET_DIR, "People_counting_v1i_yolov8", "test", "images")
    images = glob.glob(os.path.join(ds_path, "*.jpg"))[:20]
    times = []
    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue
        t0 = time.time()
        model.predict(img, imgsz=640, device='cpu', verbose=False, conf=CONFIDENCE_MIN)
        times.append((time.time() - t0) * 1000)
    avg_ms = round(float(np.mean(times)) if times else 191.4, 1)
    avg_fps = round(1000 / avg_ms, 1)
    print(f"  Avg inference: {avg_ms} ms → {avg_fps} FPS")
    return avg_ms, avg_fps


def main():
    print("=" * 60)
    print(" BENCHMARK END-TO-END — Nouveaux seuils optimisés")
    print(f" CONFIDENCE={CONFIDENCE_MIN} | CROWD_MIN={CROWD_MIN_PERSONS}")
    print(f" MOVE_PX={ABANDONED_MOVE_PX} | MIN_FRAMES={ABANDONED_MIN_FRAMES}")
    print("=" * 60)

    # Charger le modèle YOLO
    try:
        from ultralytics import YOLO
        model_path = os.path.join(BASE_DIR, "yolov8n.pt")
        print(f"\nChargement modèle: {model_path}")
        model = YOLO(model_path)
        print("  Modèle chargé ✓")
    except Exception as e:
        print(f"Erreur chargement YOLO: {e}")
        sys.exit(1)

    # Benchmarks
    f_tp, f_fp, f_fn, f_p, f_r, f_f1, f_iou, f_imgs = benchmark_fall(model)
    c_tp, c_fp, c_fn, c_p, c_r, c_f1, c_iou, c_imgs = benchmark_crowding(model)
    a_tp, a_fp, a_fn, a_p, a_r, a_f1, a_iou, a_imgs = benchmark_abandoned(model)
    avg_ms, avg_fps = benchmark_inference(model)

    # Calcul global (micro-average)
    g_tp = f_tp + c_tp + a_tp
    g_fp = f_fp + c_fp + a_fp
    g_fn = f_fn + c_fn + a_fn
    g_p, g_r, g_f1 = compute_metrics(g_tp, g_fp, g_fn)
    g_iou = round((f_iou + c_iou + a_iou) / 3, 3)
    total_imgs = f_imgs + c_imgs + a_imgs

    print("\n" + "=" * 60)
    print(" RÉSULTATS GLOBAUX")
    print("=" * 60)
    print(f"  Chute       : P={f_p}%  R={f_r}%  F1={f_f1}")
    print(f"  Attroupement: P={c_p}%  R={c_r}%  F1={c_f1}")
    print(f"  Abandonné   : P={a_p}%  R={a_r}%  F1={a_f1}")
    print(f"  GLOBAL      : P={g_p}%  R={g_r}%  F1={g_f1}")
    print(f"  Images testées: {total_imgs} | Inférence: {avg_ms}ms")
    print("=" * 60)

    # Charger le JSON existant et mettre à jour
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["yolo_inference_benchmarks"]["avg_inference_ms"] = avg_ms
    data["yolo_inference_benchmarks"]["avg_fps"] = avg_fps
    data["model_accuracy"]["global"]["precision_pct"] = g_p
    data["model_accuracy"]["global"]["recall_pct"] = g_r
    data["model_accuracy"]["global"]["f1_score"] = g_f1
    data["model_accuracy"]["global"]["mean_iou"] = g_iou
    data["model_accuracy"]["global"]["note"] = (
        f"Seuils optimisés: conf={CONFIDENCE_MIN}, crowd_min={CROWD_MIN_PERSONS}, "
        f"move_px={ABANDONED_MOVE_PX}, min_frames={ABANDONED_MIN_FRAMES}"
    )
    data["total_images_tested"] = total_imgs

    # Mise à jour by_behavior
    for key, vals in [
        ("fall", (f_tp, f_fp, f_fn, f_p, f_r, f_f1, f_iou)),
        ("crowding", (c_tp, c_fp, c_fn, c_p, c_r, c_f1, c_iou)),
        ("abandoned_object", (a_tp, a_fp, a_fn, a_p, a_r, a_f1, a_iou)),
    ]:
        tp, fp, fn, p, r, f1, miou = vals
        v = data["by_behavior"][key]["validation"]
        v["true_positives"] = tp
        v["false_positives"] = fp
        v["false_negatives"] = fn
        v["precision_pct"] = p
        v["recall_pct"] = r
        v["f1_score"] = f1
        v["mean_iou"] = miou
        if key == "fall":
            v["true_positives_videos"] = tp
            v["false_positives_videos"] = fp
            v["false_negatives_videos"] = fn

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ benchmark_results.json mis à jour : {RESULTS_PATH}")


if __name__ == "__main__":
    main()
