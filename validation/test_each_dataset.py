#!/usr/bin/env python3
"""
TEST INDIVIDUEL PAR DATASET
Teste chaque dataset separement avec resultats detailles
"""

import os
import cv2
import json
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime

print("=" * 75)
print("TEST INDIVIDUEL - UN RESULTAT PAR DATASET")
print("=" * 75)

BASE_DIR   = r'D:\surveillance_project\backend\data\datasets'
URFD_DIR   = r'D:\surveillance_project\backend\data\URFD-Dataset'
RESULTS_FILE = r'D:\surveillance_project\RESULTATS_PAR_DATASET.json'

# ── Charger YOLOv8 ──────────────────────────────────────────────────────────
print("\n[LOAD] YOLOv8n...")

# Desactiver les verifications reseau
os.environ['YOLO_VERBOSE'] = 'False'
os.environ['ULTRALYTICS_OFFLINE'] = '1'

from ultralytics import YOLO

model_path = r'D:\surveillance_project\backend\yolov8n.pt'
if not os.path.exists(model_path):
    model_path = r'D:\surveillance_project\backend\models\yolov8n.pt'

if not os.path.exists(model_path):
    print(f"[ERROR] Modele non trouve: {model_path}")
    sys.exit(1)

model = YOLO(model_path)
print(f"[OK] Modele charge: {model_path}")

# ── Fonctions ────────────────────────────────────────────────────────────────

def load_labels(label_path, w, h):
    boxes = []
    if not os.path.exists(label_path):
        return boxes
    with open(label_path) as f:
        for line in f:
            p = line.strip().split()
            if len(p) < 5:
                continue
            cls = int(p[0])
            cx,cy,bw,bh = float(p[1]),float(p[2]),float(p[3]),float(p[4])
            x1=int((cx-bw/2)*w); y1=int((cy-bh/2)*h)
            x2=int((cx+bw/2)*w); y2=int((cy+bh/2)*h)
            boxes.append([x1,y1,x2,y2,cls])
    return boxes

def iou(a, b):
    ix1,iy1=max(a[0],b[0]),max(a[1],b[1])
    ix2,iy2=min(a[2],b[2]),min(a[3],b[3])
    inter=max(0,ix2-ix1)*max(0,iy2-iy1)
    ua=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/ua if ua>0 else 0.0

def collect_images(dataset_dir):
    """Collecter toutes les images + labels d'un dataset YOLOv8"""
    pairs = []
    for split in ['valid','test','train']:
        img_dir = os.path.join(dataset_dir, split, 'images')
        lbl_dir = os.path.join(dataset_dir, split, 'labels')
        if os.path.exists(img_dir):
            for f in sorted(os.listdir(img_dir)):
                if f.lower().endswith(('.jpg','.jpeg','.png')):
                    lbl = os.path.join(lbl_dir, Path(f).stem+'.txt')
                    pairs.append((os.path.join(img_dir,f), lbl, split))
    # Recherche recursive si structure differente
    if not pairs:
        for root,_,files in os.walk(dataset_dir):
            if 'images' in root.lower():
                lbl_root = root.replace('images','labels')
                for f in sorted(files):
                    if f.lower().endswith(('.jpg','.jpeg','.png')):
                        lbl = os.path.join(lbl_root, Path(f).stem+'.txt')
                        pairs.append((os.path.join(root,f), lbl, 'found'))
    return pairs

def test_single_dataset(name, dataset_dir, behavior, max_images=None, iou_thr=0.5):
    """Tester UN dataset et retourner ses metriques"""
    print(f"\n{'='*75}")
    print(f"DATASET: {name}")
    print(f"Comportement: {behavior}")
    print(f"Dossier: {dataset_dir}")
    print(f"{'='*75}")

    if not os.path.exists(dataset_dir):
        print(f"  [SKIP] Dossier introuvable")
        return None

    # Classes
    yaml_f = os.path.join(dataset_dir, 'data.yaml')
    classes = ['object']
    if os.path.exists(yaml_f):
        with open(yaml_f) as f:
            d = yaml.safe_load(f)
            classes = d.get('names', ['object'])

    # Images
    all_pairs = collect_images(dataset_dir)
    if not all_pairs:
        print(f"  [SKIP] Aucune image trouvee")
        return None

    # Stats par split
    splits = {}
    for _,_,sp in all_pairs:
        splits[sp] = splits.get(sp,0)+1

    n = len(all_pairs) if max_images is None else min(len(all_pairs), max_images)
    test_pairs = all_pairs[:n]

    print(f"  Classes    : {classes}")
    print(f"  Splits     : {splits}")
    print(f"  Total imgs : {len(all_pairs)}")
    print(f"  Test sur   : {n} images")
    print(f"  IoU seuil  : {iou_thr}")
    print()

    TP=FP=FN=0
    iou_scores=[]
    imgs_with_gt=0
    imgs_no_det=0

    for i,(img_path,lbl_path,sp) in enumerate(test_pairs):
        try:
            img=cv2.imread(img_path)
            if img is None: continue
            h,w=img.shape[:2]

            gt = load_labels(lbl_path, w, h)
            if gt: imgs_with_gt+=1

            # Prediction
            preds=[]
            results=model(img, verbose=False, conf=0.25)
            for r in results:
                for box in r.boxes:
                    x1,y1,x2,y2=map(int,box.xyxy[0].tolist())
                    preds.append([x1,y1,x2,y2,int(box.cls[0]),float(box.conf[0])])

            if not preds and gt: imgs_no_det+=1

            # Matching
            matched_gt=set()
            for pred in preds:
                best_iou,best_gi=0,-1
                for gi,g in enumerate(gt):
                    if gi in matched_gt: continue
                    v=iou(pred[:4], g[:4])
                    if v>best_iou: best_iou,best_gi=v,gi
                if best_iou>=iou_thr and best_gi>=0:
                    TP+=1; matched_gt.add(best_gi); iou_scores.append(best_iou)
                else:
                    FP+=1
            FN+=len(gt)-len(matched_gt)

            # Progress toutes les 50 images
            if (i+1)%50==0 or (i+1)==n:
                p_tmp=TP/(TP+FP) if (TP+FP)>0 else 0
                r_tmp=TP/(TP+FN) if (TP+FN)>0 else 0
                print(f"  [{i+1:4d}/{n}] TP={TP} FP={FP} FN={FN} | P={p_tmp:.1%} R={r_tmp:.1%}")

        except KeyboardInterrupt:
            print(f"\n  [STOP] Interrompu a {i+1}/{n}")
            break
        except Exception as e:
            continue

    # Metriques finales
    P  = TP/(TP+FP)   if (TP+FP)>0   else 0
    R  = TP/(TP+FN)   if (TP+FN)>0   else 0
    F1 = 2*P*R/(P+R)  if (P+R)>0     else 0
    mIoU = np.mean(iou_scores) if iou_scores else 0

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │ RESULTATS: {name[:28]}")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │ Images testees   : {n:<6}             │")
    print(f"  │ Images avec GT   : {imgs_with_gt:<6}             │")
    print(f"  │ Images sans det  : {imgs_no_det:<6}             │")
    print(f"  │ TP={TP:<5} FP={FP:<5} FN={FN:<5}          │")
    print(f"  │ Precision        : {P:.1%}              │")
    print(f"  │ Recall           : {R:.1%}              │")
    print(f"  │ F1-Score         : {F1:.3f}              │")
    print(f"  │ Mean IoU         : {mIoU:.3f}              │")
    print(f"  └─────────────────────────────────────┘")

    return {
        'name': name, 'behavior': behavior,
        'path': dataset_dir, 'classes': classes,
        'total_images': len(all_pairs), 'tested': n,
        'imgs_with_gt': imgs_with_gt,
        'TP': TP, 'FP': FP, 'FN': FN,
        'precision': round(P,3), 'recall': round(R,3),
        'f1': round(F1,3), 'mean_iou': round(mIoU,3)
    }

# ── Test URFD (videos → frames) ──────────────────────────────────────────────
def test_urfd():
    print(f"\n{'='*75}")
    print(f"DATASET: URFD (Fall Detection — Videos reelles)")
    print(f"{'='*75}")
    fall_dirs = sorted([d for d in os.listdir(URFD_DIR) if d.startswith('fall-')])
    adl_dirs  = sorted([d for d in os.listdir(URFD_DIR) if d.startswith('adl-')])
    all_videos = [(v,True) for v in fall_dirs]+[(v,False) for v in adl_dirs]

    print(f"  Videos chutes : {len(fall_dirs)}")
    print(f"  Videos normal : {len(adl_dirs)}")
    print(f"  Total         : {len(all_videos)} videos")
    print()

    TP=FP=FN=TN=0
    for i,(vname,is_fall) in enumerate(all_videos):
        vpath=os.path.join(URFD_DIR,vname)
        imgs=sorted([f for f in os.listdir(vpath) if f.endswith('.png')])
        if not imgs: continue

        fall_frames=0
        sample=imgs[::max(1,len(imgs)//10)][:10]
        for fname in sample:
            img=cv2.imread(os.path.join(vpath,fname))
            if img is None: continue
            h,w=img.shape[:2]
            gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            _,thr=cv2.threshold(gray,30,255,cv2.THRESH_BINARY)
            cnts,_=cv2.findContours(thr,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                lg=max(cnts,key=cv2.contourArea)
                x,y,cw,ch=cv2.boundingRect(lg)
                if cw>20 and ch>20 and (ch/cw)<0.85:
                    fall_frames+=1

        detected = (fall_frames/max(len(sample),1)) > 0.20
        if is_fall and detected:     TP+=1; r="TP"
        elif is_fall and not detected: FN+=1; r="FN"
        elif not is_fall and detected: FP+=1; r="FP"
        else:                          TN+=1; r="TN"

        if (i+1)%10==0 or (i+1)==len(all_videos):
            print(f"  [{i+1:2d}/{len(all_videos)}] TP={TP} FP={FP} FN={FN} TN={TN}")

    P  = TP/(TP+FP) if (TP+FP)>0 else 0
    R  = TP/(TP+FN) if (TP+FN)>0 else 0
    F1 = 2*P*R/(P+R) if (P+R)>0 else 0
    Acc= (TP+TN)/len(all_videos)

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │ RESULTATS: URFD                      │")
    print(f"  ├─────────────────────────────────────┤")
    print(f"  │ Videos testees   : {len(all_videos):<6}             │")
    print(f"  │ TP={TP:<3} FP={FP:<3} FN={FN:<3} TN={TN:<3}         │")
    print(f"  │ Precision        : {P:.1%}              │")
    print(f"  │ Recall           : {R:.1%}              │")
    print(f"  │ F1-Score         : {F1:.3f}              │")
    print(f"  │ Accuracy         : {Acc:.1%}              │")
    print(f"  └─────────────────────────────────────┘")

    return {
        'name':'URFD','behavior':'chutes',
        'total_images':len(all_videos),'tested':len(all_videos),
        'TP':TP,'FP':FP,'FN':FN,'TN':TN,
        'precision':round(P,3),'recall':round(R,3),
        'f1':round(F1,3),'accuracy':round(Acc,3)
    }

# ── Lancer tous les tests ─────────────────────────────────────────────────────

ALL = {}

# 1. URFD
ALL['URFD'] = test_urfd()

# 2. Chaque dataset Roboflow
if os.path.exists(BASE_DIR):
    dataset_map = {}
    for folder in sorted(os.listdir(BASE_DIR)):
        fpath = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(fpath): continue
        name_lower = folder.lower()
        if 'fall' in name_lower or 'ur_fall' in name_lower:
            behavior = 'chutes'
        elif 'crowd' in name_lower or 'human' in name_lower:
            behavior = 'attroupements'
        elif 'abandon' in name_lower or 'object' in name_lower:
            behavior = 'objets_abandonnes'
        else:
            behavior = 'inconnu'
        dataset_map[folder] = (fpath, behavior)

    for folder,(fpath,behavior) in dataset_map.items():
        result = test_single_dataset(folder, fpath, behavior, max_images=200)
        if result:
            ALL[folder] = result
else:
    print(f"\n[WARNING] Dossier datasets non trouve: {BASE_DIR}")
    print("Lance d'abord l'extraction des ZIPs")

# ── Rapport Final ─────────────────────────────────────────────────────────────

print(f"\n{'='*75}")
print("RAPPORT FINAL — RESULTATS PAR DATASET")
print(f"{'='*75}")

print(f"\n  {'DATASET':<40} {'COMPORT.':<18} {'IMGS':>6} {'P':>7} {'R':>7} {'F1':>7} {'IoU':>7}")
print("  "+"-"*92)

for name,res in ALL.items():
    imgs = res.get('tested', res.get('total_images',0))
    P    = res.get('precision',0)
    R    = res.get('recall',0)
    F1   = res.get('f1',0)
    mIoU = res.get('mean_iou', res.get('accuracy',0))
    beh  = res.get('behavior','?')
    print(f"  {name:<40} {beh:<18} {imgs:>6} {P:>6.1%} {R:>6.1%} {F1:>6.3f} {mIoU:>6.3f}")

# Moyenne par comportement
print(f"\n  {'PAR COMPORTEMENT':}")
print("  "+"-"*92)
for beh in ['chutes','attroupements','objets_abandonnes']:
    vals = [v for v in ALL.values() if v.get('behavior')==beh]
    if not vals: continue
    ap  = sum(v['precision'] for v in vals)/len(vals)
    ar  = sum(v['recall']    for v in vals)/len(vals)
    af1 = sum(v['f1']        for v in vals)/len(vals)
    total = sum(v.get('tested',0) for v in vals)
    print(f"  {beh:<40} {'MOYENNE':<18} {total:>6} {ap:>6.1%} {ar:>6.1%} {af1:>6.3f}")

with open(RESULTS_FILE,'w',encoding='utf-8') as f:
    json.dump({'timestamp':datetime.utcnow().isoformat(),'results':ALL},
              f, indent=2, ensure_ascii=False, default=str)

print(f"\n[OK] Resultats sauvegardes: {RESULTS_FILE}")
print("="*75+"\n")
