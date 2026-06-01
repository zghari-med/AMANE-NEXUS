#!/usr/bin/env python3
"""
Test END-TO-END sur datasets Roboflow YOLOv8
Calcul REEL: Precision / Recall / F1 / IoU
"""

import os
import cv2
import json
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("TEST END-TO-END - DATASETS ROBOFLOW YOLOv8")
print("Precision/Recall/F1 avec IoU sur bounding boxes REELLES")
print("=" * 70)

BASE_DIR = r'D:\surveillance_project\backend\data'

# ── Charger YOLOv8 ──────────────────────────────────────────────────────────
print("\n[LOAD] Chargement YOLOv8...")
try:
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')  # Modele nano (deja present dans le projet)
    print("[OK] YOLOv8n charge")
except Exception as e:
    print(f"[ERROR] YOLOv8: {e}")
    model = None

# ── Fonctions utilitaires ────────────────────────────────────────────────────

def load_yolo_labels(label_path, img_w, img_h):
    """Charger les annotations YOLO TXT → bbox absolues"""
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls = int(parts[0])
            cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            # Convertir en coordonnées absolues
            x1 = int((cx - w/2) * img_w)
            y1 = int((cy - h/2) * img_h)
            x2 = int((cx + w/2) * img_w)
            y2 = int((cy + h/2) * img_h)
            boxes.append({'class': cls, 'bbox': [x1, y1, x2, y2]})
    return boxes

def compute_iou(box1, box2):
    """Calculer IoU entre 2 bounding boxes [x1,y1,x2,y2]"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
    area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0

def test_dataset(dataset_dir, behavior_name, iou_threshold=0.5):
    """
    Tester un dataset YOLOv8 complet
    Retourne: TP, FP, FN, precision, recall, f1
    """
    print(f"\n{'='*70}")
    print(f"TEST: {behavior_name.upper()}")
    print(f"Dossier: {dataset_dir}")
    print(f"{'='*70}")

    if not os.path.exists(dataset_dir):
        print(f"  [SKIP] Dossier non trouve: {dataset_dir}")
        return None

    # Charger data.yaml pour les classes
    yaml_file = os.path.join(dataset_dir, 'data.yaml')
    classes = ['object']
    if os.path.exists(yaml_file):
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            classes = data.get('names', ['object'])
        print(f"  Classes: {classes}")

    # Chercher images dans train/ et valid/
    all_images = []
    for split in ['valid', 'test', 'train']:
        img_dir = os.path.join(dataset_dir, split, 'images')
        lbl_dir = os.path.join(dataset_dir, split, 'labels')
        if os.path.exists(img_dir):
            for fname in os.listdir(img_dir):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(img_dir, fname)
                    lbl_path = os.path.join(lbl_dir, os.path.splitext(fname)[0] + '.txt')
                    all_images.append((img_path, lbl_path, split))

    if not all_images:
        print(f"  [SKIP] Aucune image trouvee")
        return None

    # Limiter a 100 images pour test rapide
    test_images = all_images[:100]
    print(f"  Images disponibles: {len(all_images)} | Test sur: {len(test_images)}")
    print(f"  IoU threshold: {iou_threshold}")
    print()

    TP = FP = FN = 0
    iou_scores = []
    details = []

    for i, (img_path, lbl_path, split) in enumerate(test_images):
        img = cv2.imread(img_path)
        if img is None:
            continue

        h, w = img.shape[:2]
        fname = os.path.basename(img_path)

        # Ground truth annotations
        gt_boxes = load_yolo_labels(lbl_path, w, h)

        # Prediction YOLOv8
        pred_boxes = []
        if model:
            results = model(img, verbose=False, conf=0.25)
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    pred_boxes.append({'class': cls, 'bbox': [x1,y1,x2,y2], 'conf': conf})

        # Matching GT vs Predictions avec IoU
        matched_gt = set()
        matched_pred = set()

        for pi, pred in enumerate(pred_boxes):
            best_iou = 0
            best_gt = -1
            for gi, gt in enumerate(gt_boxes):
                if gi in matched_gt:
                    continue
                iou = compute_iou(pred['bbox'], gt['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_gt = gi

            if best_iou >= iou_threshold and best_gt >= 0:
                TP += 1
                matched_gt.add(best_gt)
                matched_pred.add(pi)
                iou_scores.append(best_iou)
            else:
                FP += 1

        # GT non matchees = FN
        FN += len(gt_boxes) - len(matched_gt)

        # Log
        status = "[OK]" if len(pred_boxes) > 0 else "[NO_DET]"
        gt_str = f"GT={len(gt_boxes)}"
        pd_str = f"Pred={len(pred_boxes)}"
        print(f"  [{i+1:3d}/{len(test_images)}] {status} {fname[:30]:30s} {gt_str} {pd_str}")

    # Métriques finales
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    mean_iou  = np.mean(iou_scores) if iou_scores else 0

    print(f"\n  METRIQUES FINALES ({behavior_name}):")
    print(f"    Images testees : {len(test_images)}")
    print(f"    TP={TP}  FP={FP}  FN={FN}")
    print(f"    Precision      : {precision:.1%}")
    print(f"    Recall         : {recall:.1%}")
    print(f"    F1-Score       : {f1:.3f}")
    print(f"    Mean IoU       : {mean_iou:.3f}")

    return {
        'behavior': behavior_name,
        'dataset': dataset_dir,
        'images_tested': len(test_images),
        'TP': TP, 'FP': FP, 'FN': FN,
        'precision': round(precision, 3),
        'recall': round(recall, 3),
        'f1': round(f1, 3),
        'mean_iou': round(mean_iou, 3),
        'classes': classes
    }


# ── Tests sur les 3 comportements ───────────────────────────────────────────

DATASETS = {
    'Chutes':             os.path.join(BASE_DIR, 'roboflow_falls'),
    'Attroupements':      os.path.join(BASE_DIR, 'roboflow_crowd'),
    'Objets_Abandonnes':  os.path.join(BASE_DIR, 'roboflow_abandoned'),
}

ALL_RESULTS = {
    'timestamp': datetime.utcnow().isoformat(),
    'model': 'YOLOv8n',
    'iou_threshold': 0.5,
    'behaviors': {}
}

for behavior, dataset_dir in DATASETS.items():
    result = test_dataset(dataset_dir, behavior)
    if result:
        ALL_RESULTS['behaviors'][behavior] = result

# ── Rapport Global ───────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("RAPPORT FINAL - VRAIS RESULTATS SCIENTIFIQUES")
print("=" * 70)

if ALL_RESULTS['behaviors']:
    print(f"\n{'COMPORTEMENT':<22} {'IMAGES':<8} {'TP':>5} {'FP':>5} {'FN':>5} {'PRECISION':>10} {'RECALL':>8} {'F1':>8} {'IoU':>8}")
    print("-" * 80)

    for beh, res in ALL_RESULTS['behaviors'].items():
        print(f"  {beh:<20} {res['images_tested']:<8} {res['TP']:>5} {res['FP']:>5} "
              f"{res['FN']:>5} {res['precision']:>9.1%} {res['recall']:>7.1%} "
              f"{res['f1']:>7.3f} {res['mean_iou']:>7.3f}")

    # Moyenne globale
    vals = list(ALL_RESULTS['behaviors'].values())
    avg_p   = sum(v['precision'] for v in vals) / len(vals)
    avg_r   = sum(v['recall']    for v in vals) / len(vals)
    avg_f1  = sum(v['f1']        for v in vals) / len(vals)
    avg_iou = sum(v['mean_iou']  for v in vals) / len(vals)

    print("-" * 80)
    print(f"  {'GLOBAL (moyenne)':<20} {'':<8} {'':>5} {'':>5} {'':>5} "
          f"{avg_p:>9.1%} {avg_r:>7.1%} {avg_f1:>7.3f} {avg_iou:>7.3f}")

    ALL_RESULTS['global'] = {
        'avg_precision': round(avg_p, 3),
        'avg_recall': round(avg_r, 3),
        'avg_f1': round(avg_f1, 3),
        'avg_iou': round(avg_iou, 3)
    }

# Sauvegarder
out = r'D:\surveillance_project\VRAIS_RESULTATS_ROBOFLOW.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False, default=str)

print(f"\n[OK] Resultats sauvegardes: {out}")
print("=" * 70 + "\n")
