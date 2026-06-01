#!/usr/bin/env python3
"""
AUTO EXTRACT + TEST
1. Detecte les ZIPs dans data/zips/
2. Extrait vers le bon dossier selon le nom
3. Lance les tests automatiquement
"""

import os
import sys
import zipfile
import shutil
import json
import cv2
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime

ZIPS_DIR  = r'D:\surveillance_project\backend\data\zips'
BASE_DIR  = r'D:\surveillance_project\backend\data'

print("=" * 70)
print("AUTO EXTRACT + TEST - DATASETS ROBOFLOW")
print(f"Dossier ZIP: {ZIPS_DIR}")
print("=" * 70)

# ── 1. Detecter les ZIPs ─────────────────────────────────────────────────────

zips = [f for f in os.listdir(ZIPS_DIR) if f.endswith('.zip')]

if not zips:
    print(f"""
[ATTENTE] Aucun ZIP trouve dans:
  {ZIPS_DIR}

Mets tes fichiers ZIP dans ce dossier puis relance ce script.

Datasets a telecharger depuis Roboflow:
  1. Fall Detection     -> roboflow_falls.zip   (ou nom quelconque)
  2. Crowd Detection    -> roboflow_crowd.zip
  3. Abandoned Objects  -> roboflow_abandoned.zip
""")
    sys.exit(0)

print(f"\n[FOUND] {len(zips)} fichier(s) ZIP detecte(s):")
for z in zips:
    size = os.path.getsize(os.path.join(ZIPS_DIR, z))
    print(f"  - {z} ({size/1024**2:.1f} MB)")

# ── 2. Determiner le comportement depuis le nom du ZIP ───────────────────────

def detect_behavior(filename):
    """Deviner le comportement depuis le nom du fichier"""
    name = filename.lower()
    if any(k in name for k in ['fall', 'chute', 'fallen', 'ur-fall', 'urfall']):
        return 'chutes', 'roboflow_falls'
    elif any(k in name for k in ['crowd', 'people', 'person', 'foule', 'attroup']):
        return 'attroupements', 'roboflow_crowd'
    elif any(k in name for k in ['abandon', 'object', 'objet', 'luggage', 'bag']):
        return 'objets_abandonnes', 'roboflow_abandoned'
    else:
        return 'unknown', f'dataset_{filename.replace(".zip","")}'

# ── 3. Extraire chaque ZIP ────────────────────────────────────────────────────

extracted = {}

for zip_name in zips:
    zip_path = os.path.join(ZIPS_DIR, zip_name)
    behavior, dest_folder = detect_behavior(zip_name)
    dest_dir = os.path.join(BASE_DIR, dest_folder)

    print(f"\n[EXTRACT] {zip_name}")
    print(f"  Comportement detecte : {behavior}")
    print(f"  Destination          : {dest_dir}")

    os.makedirs(dest_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            total = len(z.namelist())
            print(f"  Fichiers dans ZIP    : {total}")
            z.extractall(dest_dir)
        print(f"  [OK] Extraction terminee!")
        extracted[behavior] = dest_dir
    except Exception as e:
        print(f"  [ERROR] {e}")

if not extracted:
    print("\n[ERROR] Aucune extraction reussie")
    sys.exit(1)

# ── 4. Charger YOLOv8 ────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("CHARGEMENT YOLOV8")
print("=" * 70)

model = None
try:
    from ultralytics import YOLO
    # Chercher le modele dans le projet
    model_paths = [
        r'D:\surveillance_project\backend\models\yolov8n.pt',
        r'D:\surveillance_project\backend\yolov8n.pt',
        'yolov8n.pt'
    ]
    for mp in model_paths:
        if os.path.exists(mp):
            model = YOLO(mp)
            print(f"[OK] Modele charge: {mp}")
            break
    if model is None:
        model = YOLO('yolov8n.pt')  # Telecharge auto si absent
        print("[OK] YOLOv8n telecharge et charge")
except Exception as e:
    print(f"[WARNING] YOLOv8 non disponible: {e}")
    print("[INFO] Test sans detection (comptage annotations uniquement)")

# ── 5. Fonctions de test ──────────────────────────────────────────────────────

def load_yolo_labels(label_path, img_w, img_h):
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            cls = int(parts[0])
            cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            x1 = int((cx - bw/2) * img_w)
            y1 = int((cy - bh/2) * img_h)
            x2 = int((cx + bw/2) * img_w)
            y2 = int((cy + bh/2) * img_h)
            boxes.append({'class': cls, 'bbox': [x1, y1, x2, y2]})
    return boxes

def compute_iou(b1, b2):
    ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
    ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0, ix2-ix1) * max(0, iy2-iy1)
    a1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
    a2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0

def test_dataset(behavior, dataset_dir, max_images=100, iou_thr=0.5):
    print(f"\n{'='*70}")
    print(f"TEST: {behavior.upper()}")
    print(f"{'='*70}")

    # Trouver les images
    all_images = []
    for split in ['valid', 'test', 'train']:
        img_dir = os.path.join(dataset_dir, split, 'images')
        lbl_dir = os.path.join(dataset_dir, split, 'labels')
        if os.path.exists(img_dir):
            for fname in sorted(os.listdir(img_dir)):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(img_dir, fname)
                    lbl_path = os.path.join(lbl_dir, Path(fname).stem + '.txt')
                    all_images.append((img_path, lbl_path))

    # Chercher aussi a la racine
    if not all_images:
        for fname in os.listdir(dataset_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(dataset_dir, fname)
                lbl_path = os.path.join(dataset_dir, Path(fname).stem + '.txt')
                all_images.append((img_path, lbl_path))

    if not all_images:
        # Chercher recursivement
        for root, dirs, files in os.walk(dataset_dir):
            if 'images' in root:
                for fname in files:
                    if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                        img_path = os.path.join(root, fname)
                        lbl_dir  = root.replace('images', 'labels')
                        lbl_path = os.path.join(lbl_dir, Path(fname).stem + '.txt')
                        all_images.append((img_path, lbl_path))

    if not all_images:
        print(f"  [SKIP] Aucune image trouvee dans {dataset_dir}")
        return None

    test_imgs = all_images[:max_images]
    print(f"  Total images : {len(all_images)} | Test sur : {len(test_imgs)}")

    # Charger classes
    yaml_file = os.path.join(dataset_dir, 'data.yaml')
    classes = ['object']
    if os.path.exists(yaml_file):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            classes = data.get('names', ['object'])
    print(f"  Classes      : {classes}")
    print()

    TP = FP = FN = 0
    iou_list = []

    for i, (img_path, lbl_path) in enumerate(test_imgs):
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        fname = os.path.basename(img_path)

        gt_boxes   = load_yolo_labels(lbl_path, w, h)
        pred_boxes = []

        if model:
            results = model(img, verbose=False, conf=0.25)
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    cls  = int(box.cls[0])
                    conf = float(box.conf[0])
                    pred_boxes.append({'class': cls, 'bbox': [x1,y1,x2,y2], 'conf': conf})

        # Matching GT ↔ Pred
        matched_gt = set()
        for pred in pred_boxes:
            best_iou, best_gi = 0, -1
            for gi, gt in enumerate(gt_boxes):
                if gi in matched_gt:
                    continue
                iou = compute_iou(pred['bbox'], gt['bbox'])
                if iou > best_iou:
                    best_iou, best_gi = iou, gi
            if best_iou >= iou_thr and best_gi >= 0:
                TP += 1
                matched_gt.add(best_gi)
                iou_list.append(best_iou)
            else:
                FP += 1
        FN += len(gt_boxes) - len(matched_gt)

        icon = "[OK]" if len(pred_boxes) >= len(gt_boxes) else "[LOW]"
        print(f"  [{i+1:3d}/{len(test_imgs)}] {icon} {fname[:35]:35s} GT={len(gt_boxes)} Pred={len(pred_boxes)}")

    P   = TP / (TP+FP)   if (TP+FP)   > 0 else 0
    R   = TP / (TP+FN)   if (TP+FN)   > 0 else 0
    F1  = 2*P*R / (P+R)  if (P+R)     > 0 else 0
    mIoU = np.mean(iou_list) if iou_list else 0

    print(f"\n  RESULTATS {behavior.upper()}:")
    print(f"    TP={TP}  FP={FP}  FN={FN}")
    print(f"    Precision : {P:.1%}")
    print(f"    Recall    : {R:.1%}")
    print(f"    F1-Score  : {F1:.3f}")
    print(f"    Mean IoU  : {mIoU:.3f}")

    return {
        'behavior': behavior, 'images_tested': len(test_imgs),
        'TP': TP, 'FP': FP, 'FN': FN,
        'precision': round(P,3), 'recall': round(R,3),
        'f1': round(F1,3), 'mean_iou': round(mIoU,3),
        'classes': classes
    }

# ── 6. Lancer les tests ───────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("LANCEMENT DES TESTS")
print("=" * 70)

ALL_RESULTS = {
    'timestamp': datetime.utcnow().isoformat(),
    'model': 'YOLOv8n',
    'behaviors': {}
}

for behavior, dest_dir in extracted.items():
    result = test_dataset(behavior, dest_dir)
    if result:
        ALL_RESULTS['behaviors'][behavior] = result

# ── 7. Rapport Final ──────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("RAPPORT FINAL - VRAIS RESULTATS SCIENTIFIQUES")
print("=" * 70)

if ALL_RESULTS['behaviors']:
    print(f"\n  {'COMPORTEMENT':<22} {'IMAGES':<8} {'TP':>4} {'FP':>4} {'FN':>4} "
          f"{'PRECISION':>10} {'RECALL':>8} {'F1':>7} {'IoU':>7}")
    print("  " + "-"*72)

    vals = list(ALL_RESULTS['behaviors'].values())
    for res in vals:
        print(f"  {res['behavior']:<22} {res['images_tested']:<8} "
              f"{res['TP']:>4} {res['FP']:>4} {res['FN']:>4} "
              f"{res['precision']:>9.1%} {res['recall']:>7.1%} "
              f"{res['f1']:>7.3f} {res['mean_iou']:>7.3f}")

    if len(vals) > 1:
        ap  = sum(v['precision'] for v in vals) / len(vals)
        ar  = sum(v['recall']    for v in vals) / len(vals)
        af1 = sum(v['f1']        for v in vals) / len(vals)
        aiu = sum(v['mean_iou']  for v in vals) / len(vals)
        print("  " + "-"*72)
        print(f"  {'GLOBAL (moyenne)':<22} {'':<8} {'':<4} {'':<4} {'':<4} "
              f"{ap:>9.1%} {ar:>7.1%} {af1:>7.3f} {aiu:>7.3f}")

        ALL_RESULTS['global'] = {
            'avg_precision': round(ap,3), 'avg_recall': round(ar,3),
            'avg_f1': round(af1,3),       'avg_iou':    round(aiu,3)
        }

# Sauvegarder
out = r'D:\surveillance_project\VRAIS_RESULTATS_ROBOFLOW.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(ALL_RESULTS, f, indent=2, ensure_ascii=False, default=str)

print(f"\n  [OK] Resultats sauvegardes: {out}")
print("=" * 70 + "\n")
