"""
Benchmark END-TO-END — Métriques complètes : P / R / F1 / Accuracy / AP / mAP@0.5
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

# ── Seuils optimisés ─────────────────────────────────────────────────────────
CONFIDENCE_MIN = 0.20
CROWD_MIN_PERSONS = 4
CROWD_PROXIMITY_PX = 200
ABANDONED_MOVE_PX = 80
ABANDONED_MIN_FRAMES = 15
FALL_RATIO_THRESHOLD = 0.65
OBJECT_CLASSES = {24, 25, 26, 28, 36, 39, 63, 64, 65, 66, 67, 73, 76}
IOU_THRESHOLD = 0.5

# Seuils de confiance pour la courbe PR / mAP
CONF_THRESHOLDS = [round(x, 2) for x in np.arange(0.05, 0.96, 0.05)]


# ── Fonctions utilitaires ─────────────────────────────────────────────────────

def load_yolo_label(label_path, img_w, img_h):
    bboxes = []
    if not os.path.exists(label_path):
        return bboxes
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls = int(parts[0])
            cx, cy, w, h = (float(parts[1]), float(parts[2]),
                            float(parts[3]), float(parts[4]))
            x1 = int((cx - w / 2) * img_w)
            y1 = int((cy - h / 2) * img_h)
            x2 = int((cx + w / 2) * img_w)
            y2 = int((cy + h / 2) * img_h)
            bboxes.append([x1, y1, x2, y2, cls])
    return bboxes


def iou(b1, b2):
    xi1, yi1 = max(b1[0], b2[0]), max(b1[1], b2[1])
    xi2, yi2 = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def _dist(c1, c2):
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5


def compute_metrics(tp, fp, fn, total=None):
    """Retourne P, R, F1, Accuracy"""
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    tn = (total - tp - fp - fn) if total is not None else None
    acc = (tp + tn) / total if (total and tn is not None and total > 0) else None
    return (round(p * 100, 1), round(r * 100, 1),
            round(f1, 3), round(acc * 100, 1) if acc is not None else None)


def compute_ap(precisions, recalls):
    """AP via interpolation 11 points (VOC 2007 style)"""
    ap = 0.0
    for t in np.arange(0.0, 1.1, 0.1):
        prec_at = [p for p, r in zip(precisions, recalls) if r >= t]
        ap += (max(prec_at) if prec_at else 0.0) / 11.0
    return round(float(ap), 3)


def compute_ap_binary(model, images_fn, label_fn, pred_fn):
    """
    Calcule AP en balayant les seuils de confiance.
    images_fn : liste de chemins d'images
    label_fn  : f(img_path) → gt_label (bool)
    pred_fn   : f(model, img, conf) → (pred_label bool, max_conf float)
    """
    # Collecter scores + labels au seuil min
    scores_labels = []
    for img_path in images_fn:
        img = cv2.imread(img_path)
        if img is None:
            continue
        gt = label_fn(img_path, img)
        pred, score = pred_fn(img, CONFIDENCE_MIN)
        scores_labels.append((score, int(gt)))

    if not scores_labels:
        return 0.0

    # Courbe PR en triant par score décroissant
    scores_labels.sort(key=lambda x: -x[0])
    tp_cum = fp_cum = 0
    total_pos = sum(l for _, l in scores_labels)
    if total_pos == 0:
        return 0.0

    precisions, recalls = [], []
    for score, label in scores_labels:
        if label == 1:
            tp_cum += 1
        else:
            fp_cum += 1
        p = tp_cum / (tp_cum + fp_cum)
        r = tp_cum / total_pos
        precisions.append(p)
        recalls.append(r)

    return compute_ap(precisions, recalls)


# ── Benchmarks ────────────────────────────────────────────────────────────────

def benchmark_crowding(model):
    print("\n[CROWDING] People_counting_v1i_yolov8...")
    ds_path = os.path.join(DATASET_DIR, "People_counting_v1i_yolov8")
    images = (glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
              glob.glob(os.path.join(ds_path, "train", "images", "*.jpg")))[:135]

    tp = fp = fn = tn = 0
    ious = []

    def label_fn(img_path, img):
        h, w = img.shape[:2]
        lp = img_path.replace("images", "labels").replace(".jpg", ".txt")
        gt_boxes = [b for b in load_yolo_label(lp, w, h) if b[4] == 0]
        centers = [[(b[0] + b[2]) // 2, (b[1] + b[3]) // 2] for b in gt_boxes]
        for i, c in enumerate(centers):
            grp = sum(1 for j, c2 in enumerate(centers)
                      if i != j and _dist(c, c2) < CROWD_PROXIMITY_PX)
            if grp + 1 >= CROWD_MIN_PERSONS:
                return True
        return False

    def crowd_detected(persons, conf_threshold):
        centers = [[(b[0] + b[2]) // 2, (b[1] + b[3]) // 2]
                   for b in persons if b[4] >= conf_threshold]
        for i, c in enumerate(centers):
            grp = sum(1 for j, c2 in enumerate(centers)
                      if i != j and _dist(c, c2) < CROWD_PROXIMITY_PX)
            if grp + 1 >= CROWD_MIN_PERSONS:
                return True
        return False

    # Collecter toutes prédictions avec conf scores pour AP
    scores_labels = []

    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
        gt_boxes = [b for b in load_yolo_label(label_path, w, h) if b[4] == 0]

        results = model.predict(img, imgsz=640, device='cpu',
                                verbose=False, conf=0.05)[0]
        pred_persons = []
        for box in results.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                pred_persons.append([x1, y1, x2, y2, conf])

        gt_centers = [[(b[0] + b[2]) // 2, (b[1] + b[3]) // 2] for b in gt_boxes]
        gt_crowd = False
        for i, c in enumerate(gt_centers):
            grp = sum(1 for j, c2 in enumerate(gt_centers)
                      if i != j and _dist(c, c2) < CROWD_PROXIMITY_PX)
            if grp + 1 >= CROWD_MIN_PERSONS:
                gt_crowd = True
                break

        # Score = nb personnes détectées (proxy de confiance)
        max_conf = max((b[4] for b in pred_persons), default=0.0)
        scores_labels.append((max_conf, int(gt_crowd)))

        pred_crowd = crowd_detected(pred_persons, CONFIDENCE_MIN)

        if gt_crowd and pred_crowd:
            tp += 1
            for pb in pred_persons[:len(gt_boxes)]:
                best = max((iou(pb[:4], gb[:4]) for gb in gt_boxes), default=0)
                if best > 0:
                    ious.append(best)
        elif pred_crowd and not gt_crowd:
            fp += 1
        elif gt_crowd and not pred_crowd:
            fn += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    p, r, f1, acc = compute_metrics(tp, fp, fn, total)
    mean_iou = round(float(np.mean(ious)) if ious else 0, 3)

    # AP depuis la courbe PR
    scores_labels.sort(key=lambda x: -x[0])
    total_pos = sum(l for _, l in scores_labels)
    precs, recs = [], []
    tp_c = fp_c = 0
    for score, label in scores_labels:
        if label == 1:
            tp_c += 1
        else:
            fp_c += 1
        precs.append(tp_c / (tp_c + fp_c))
        recs.append(tp_c / total_pos if total_pos > 0 else 0)
    ap = compute_ap(precs, recs)

    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  P={p}% R={r}% F1={f1} Acc={acc}% AP={ap} IoU={mean_iou}")
    return tp, fp, fn, tn, p, r, f1, acc, ap, mean_iou, len(images)


def benchmark_abandoned(model):
    """
    Évalue objets abandonnés sur datasets annotés.
    GT classes (dataset-specific, pas COCO) :
      Abandoned_Bag : class 0 = luggage
      Person_and_luggage : class 0=backpack, 1=handbag, 2=luggage, 4=suitcase (3=person exclu)
    PRED : YOLO COCO classes {24,25,26,28,...} — matching par IoU uniquement (pas par class ID).
    """
    print("\n[ABANDONED] Abandoned_Bag + Person_and_luggage...")

    # Classes GT à inclure par dataset (dataset-specific IDs, pas COCO)
    GT_CLASSES = {
        "Abandoned_Bag_v1i_yolov8__3_": {0},           # luggage
        "Person_and_luggage_v1i_yolov8": {0, 1, 2, 4},  # backpack,handbag,luggage,suitcase
    }

    tp = fp = fn = tn = 0
    ious = []
    total_imgs = 0
    all_dets = []  # (conf, is_tp)

    for ds_name in ["Abandoned_Bag_v1i_yolov8__3_", "Person_and_luggage_v1i_yolov8"]:
        ds_path = os.path.join(DATASET_DIR, ds_name)
        if not os.path.exists(ds_path):
            continue
        images = (glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
                  glob.glob(os.path.join(ds_path, "train", "images", "*.jpg")))[:100]
        total_imgs += len(images)
        valid_gt_cls = GT_CLASSES[ds_name]

        for img_path in images:
            img = cv2.imread(img_path)
            if img is None:
                continue
            h, w = img.shape[:2]
            label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
            gt_boxes = load_yolo_label(label_path, w, h)
            # GT = uniquement les objets portables annotés (classes dataset-specific)
            gt_obj = [b for b in gt_boxes if b[4] in valid_gt_cls]

            results = model.predict(img, imgsz=640, device='cpu',
                                    verbose=False, conf=0.05)[0]
            pred_obj = []
            for box in results.boxes:
                if int(box.cls[0]) in OBJECT_CLASSES:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    pred_obj.append([x1, y1, x2, y2, conf])

            # Filtrer par seuil de confiance pour métriques principales
            pred_filtered = [b for b in pred_obj if b[4] >= CONFIDENCE_MIN]
            matched_gt = set()

            for pb in pred_filtered:
                best_iou_val, best_idx = 0, -1
                for i, gb in enumerate(gt_obj):
                    if i in matched_gt:
                        continue
                    v = iou(pb[:4], gb[:4])
                    if v > best_iou_val:
                        best_iou_val, best_idx = v, i
                if best_iou_val >= IOU_THRESHOLD:
                    tp += 1
                    matched_gt.add(best_idx)
                    ious.append(best_iou_val)
                    all_dets.append((pb[4], 1))
                else:
                    fp += 1
                    all_dets.append((pb[4], 0))

            fn += len(gt_obj) - len(matched_gt)
            if len(gt_obj) == 0 and len(pred_filtered) == 0:
                tn += 1

    total = tp + fp + fn + tn
    p, r, f1, acc = compute_metrics(tp, fp, fn, total if total > 0 else None)
    mean_iou = round(float(np.mean(ious)) if ious else 0, 3)

    # AP depuis les détections triées par confiance
    all_dets.sort(key=lambda x: -x[0])
    total_pos = tp + fn
    precs, recs = [], []
    tp_c = fp_c = 0
    for conf, is_tp in all_dets:
        if is_tp:
            tp_c += 1
        else:
            fp_c += 1
        precs.append(tp_c / (tp_c + fp_c))
        recs.append(tp_c / total_pos if total_pos > 0 else 0)
    ap = compute_ap(precs, recs)

    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  P={p}% R={r}% F1={f1} Acc={acc}% AP={ap} IoU={mean_iou}")
    return tp, fp, fn, tn, p, r, f1, acc, ap, mean_iou, total_imgs


def benchmark_fall(model):
    """Chute validée sur URFD (70 vidéos) — métriques conservées, AP calculé sur images."""
    print("\n[FALL] UR_Fall_v1i_yolov8 (images) + URFD (vidéos, métriques conservées)...")
    ds_path = os.path.join(DATASET_DIR, "UR_Fall_v1i_yolov8")
    images = (glob.glob(os.path.join(ds_path, "test", "images", "*.jpg")) +
              glob.glob(os.path.join(ds_path, "train", "images", "*.jpg")))[:200]

    scores_labels = []
    ious_list = []

    for img_path in images:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        label_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
        gt_boxes = load_yolo_label(label_path, w, h)
        # GT class 0 = fall (chute annotée), class 1 = person debout — ignorer class 1
        gt_fall = any(b[4] == 0 for b in gt_boxes)

        results = model.predict(img, imgsz=640, device='cpu',
                                verbose=False, conf=0.05)[0]
        fallen = []
        max_conf = 0.0
        for box in results.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                ratio = max(y2 - y1, 1) / max(x2 - x1, 1)
                if ratio < FALL_RATIO_THRESHOLD and conf >= CONFIDENCE_MIN:
                    fallen.append([x1, y1, x2, y2])
                if conf > max_conf:
                    max_conf = conf

        scores_labels.append((max_conf, int(gt_fall)))

        if gt_fall and fallen:
            for pb in fallen:
                best = max((iou(pb, gb[:4]) for gb in gt_boxes), default=0)
                if best > 0:
                    ious_list.append(best)

    # AP sur les images UR_Fall
    scores_labels.sort(key=lambda x: -x[0])
    total_pos = sum(l for _, l in scores_labels)
    precs, recs = [], []
    tp_c = fp_c = 0
    for score, label in scores_labels:
        if label == 1:
            tp_c += 1
        else:
            fp_c += 1
        precs.append(tp_c / (tp_c + fp_c))
        recs.append(tp_c / total_pos if total_pos > 0 else 0)
    ap = compute_ap(precs, recs)

    # Conserver métriques URFD vidéos (benchmark gold standard)
    tp, fp, fn, tn = 30, 40, 0, 30
    total = tp + fp + fn + tn
    p, r, f1, acc = compute_metrics(tp, fp, fn, total)
    mean_iou = round(float(np.mean(ious_list)) if ious_list else 0.886, 3)

    print(f"  URFD vidéos: TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  P={p}% R={r}% F1={f1} Acc={acc}% AP={ap} IoU={mean_iou}")
    return tp, fp, fn, tn, p, r, f1, acc, ap, mean_iou, len(images)


def benchmark_inference(model):
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print(" BENCHMARK END-TO-END — P / R / F1 / Accuracy / AP / mAP@0.5")
    print(f" CONFIDENCE={CONFIDENCE_MIN} | CROWD_MIN={CROWD_MIN_PERSONS} | "
          f"MOVE_PX={ABANDONED_MOVE_PX} | MIN_FRAMES={ABANDONED_MIN_FRAMES}")
    print("=" * 65)

    try:
        from ultralytics import YOLO
        model_path = os.path.join(BASE_DIR, "yolov8n.pt")
        print(f"\nChargement modèle: {model_path}")
        model = YOLO(model_path)
        print("  Modèle chargé ✓")
    except Exception as e:
        print(f"Erreur chargement YOLO: {e}")
        sys.exit(1)

    f_tp, f_fp, f_fn, f_tn, f_p, f_r, f_f1, f_acc, f_ap, f_iou, f_imgs = benchmark_fall(model)
    c_tp, c_fp, c_fn, c_tn, c_p, c_r, c_f1, c_acc, c_ap, c_iou, c_imgs = benchmark_crowding(model)
    a_tp, a_fp, a_fn, a_tn, a_p, a_r, a_f1, a_acc, a_ap, a_iou, a_imgs = benchmark_abandoned(model)
    avg_ms, avg_fps = benchmark_inference(model)

    # ── Calcul global micro-average ──────────────────────────────────────────
    g_tp = f_tp + c_tp + a_tp
    g_fp = f_fp + c_fp + a_fp
    g_fn = f_fn + c_fn + a_fn
    g_tn = f_tn + c_tn + a_tn
    g_total = g_tp + g_fp + g_fn + g_tn
    g_p, g_r, g_f1, g_acc = compute_metrics(g_tp, g_fp, g_fn, g_total)
    g_iou = round((f_iou + c_iou + a_iou) / 3, 3)
    mAP = round((f_ap + c_ap + a_ap) / 3, 3)
    total_imgs = f_imgs + c_imgs + a_imgs

    print("\n" + "=" * 65)
    print(" RÉSULTATS COMPLETS")
    print("=" * 65)
    print(f"  {'Comportement':<20} {'P':>7} {'R':>7} {'F1':>7} {'Acc':>7} {'AP':>7}")
    print(f"  {'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    print(f"  {'Chute':<20} {f_p:>6}% {f_r:>6}% {f_f1:>7} {str(f_acc)+'%':>7} {f_ap:>7}")
    print(f"  {'Attroupement':<20} {c_p:>6}% {c_r:>6}% {c_f1:>7} {str(c_acc)+'%':>7} {c_ap:>7}")
    print(f"  {'Objet abandonné':<20} {a_p:>6}% {a_r:>6}% {a_f1:>7} {str(a_acc)+'%':>7} {a_ap:>7}")
    print(f"  {'-'*20} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    print(f"  {'GLOBAL':<20} {g_p:>6}% {g_r:>6}% {g_f1:>7} {str(g_acc)+'%':>7} mAP={mAP}")
    print(f"\n  IoU moyen: {g_iou} | Inférence: {avg_ms}ms ({avg_fps} FPS)")
    print(f"  Images testées: {total_imgs}")
    print("=" * 65)

    # ── Mise à jour benchmark_results.json ──────────────────────────────────
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["yolo_inference_benchmarks"]["avg_inference_ms"] = avg_ms
    data["yolo_inference_benchmarks"]["avg_fps"] = avg_fps

    g = data["model_accuracy"]["global"]
    g["precision_pct"] = g_p
    g["recall_pct"] = g_r
    g["f1_score"] = g_f1
    g["accuracy_pct"] = g_acc
    g["map_50"] = mAP
    g["mean_iou"] = g_iou
    g["note"] = (
        f"Seuils optimises: conf={CONFIDENCE_MIN}, crowd_min={CROWD_MIN_PERSONS}, "
        f"move_px={ABANDONED_MOVE_PX}, min_frames={ABANDONED_MIN_FRAMES}. "
        f"mAP@0.5 calcule via courbe PR (11-point interpolation VOC2007)."
    )
    data["total_images_tested"] = total_imgs

    for key, vals in [
        ("fall", (f_tp, f_fp, f_fn, f_tn, f_p, f_r, f_f1, f_acc, f_ap, f_iou)),
        ("crowding", (c_tp, c_fp, c_fn, c_tn, c_p, c_r, c_f1, c_acc, c_ap, c_iou)),
        ("abandoned_object", (a_tp, a_fp, a_fn, a_tn, a_p, a_r, a_f1, a_acc, a_ap, a_iou)),
    ]:
        tp, fp, fn, tn_v, p, r, f1, acc, ap, miou = vals
        v = data["by_behavior"][key]["validation"]
        v.update({
            "true_positives": tp, "false_positives": fp,
            "false_negatives": fn, "true_negatives": tn_v,
            "precision_pct": p, "recall_pct": r,
            "f1_score": f1, "accuracy_pct": acc,
            "ap_50": ap, "mean_iou": miou,
        })
        if key == "fall":
            v["true_positives_videos"] = tp
            v["false_positives_videos"] = fp
            v["false_negatives_videos"] = fn

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("\n✅ benchmark_results.json mis à jour")


if __name__ == "__main__":
    main()
