"""
Test détection de chutes sur UR Fall Detection Dataset
"""
import os
import json
import cv2
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker_analysis import detect_fall, detect_crowd, detect_abandoned_object

# Configuration
URFD_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data', 'URFD-Dataset')
FALL_COOLDOWN = 300
CROWD_MIN = 5
CROWD_COOLDOWN = 90
ABANDON_COOLDOWN = 900
STATIONARY_THR = 22
GRID_SZ = 100
FRAME_SKIP = 3


def load_urfd_sequences(dataset_type='fall'):
    """Charger séquences URFD (fall ou adl)"""
    sequences = []

    urfd_dir = os.path.join(URFD_ROOT, dataset_type)
    if not os.path.exists(urfd_dir):
        print(f"❌ Dataset non trouvé : {urfd_dir}")
        return sequences

    for seq_dir in sorted(os.listdir(urfd_dir)):
        seq_path = os.path.join(urfd_dir, seq_dir)
        if os.path.isdir(seq_path):
            sequences.append(seq_path)

    return sequences


def load_rgb_frames(seq_path):
    """Charger frames RGB d'une séquence"""
    rgb_dir = os.path.join(seq_path, 'rgb')
    frames = []

    if not os.path.exists(rgb_dir):
        return frames

    for frame_file in sorted(os.listdir(rgb_dir)):
        if frame_file.endswith('.png'):
            frame_path = os.path.join(rgb_dir, frame_file)
            frame = cv2.imread(frame_path)
            if frame is not None:
                frames.append(frame)

    return frames


def load_annotations(seq_path):
    """Charger annotations d'une séquence (si existe)"""
    # UR Fall Detection inclut des fichiers de synchronisation
    # Format : frame_id, timestamp, accel_data
    # On suppose : chute = frame dans le dossier 'fall/'

    sync_file = os.path.join(seq_path, 'synchronization_data.txt')
    annotations = {'frames': []}

    if os.path.exists(sync_file):
        with open(sync_file, 'r') as f:
            for i, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) >= 2:
                    frame_id = int(parts[0])
                    annotations['frames'].append(frame_id)

    return annotations


def run_fall_detection(frames):
    """Exécuter détection chutes sur séquence"""
    detections = {
        'falls': [],
        'frame_count': len(frames)
    }

    if len(frames) == 0:
        return detections

    try:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
    except Exception as e:
        print(f"⚠️ YOLOv8 non disponible : {e}")
        return detections

    last_fall = {}
    FALL_RATIO = 0.65

    for frame_idx, frame in enumerate(frames):
        if frame_idx % FRAME_SKIP != 0:
            continue

        try:
            results = model(frame, conf=0.35, verbose=False, classes=[0])

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    h = y2 - y1
                    w = x2 - x1

                    if w > 0:
                        ratio = h / w

                        if ratio < FALL_RATIO:
                            pid = f"{(x1+x2)//40}_{(y1+y2)//40}"

                            if frame_idx - last_fall.get(pid, -FALL_COOLDOWN) >= FALL_COOLDOWN:
                                last_fall[pid] = frame_idx
                                detections['falls'].append({
                                    'frame': frame_idx,
                                    'ratio': ratio,
                                    'bbox': (x1, y1, x2, y2)
                                })
        except Exception as e:
            print(f"⚠️ Erreur frame {frame_idx} : {e}")
            continue

    return detections


def compute_metrics(y_true, y_pred):
    """Calculer Precision, Recall, F1"""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'TP': tp, 'FP': fp, 'FN': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }


def test_falls_urfd():
    """Test principal : Détection chutes sur UR Fall Detection"""
    print("\n" + "="*60)
    print("🧪 TEST DÉTECTION DE CHUTES - UR Fall Detection Dataset")
    print("="*60)

    # Charger séquences de chutes
    fall_sequences = load_urfd_sequences('fall')
    print(f"\n✅ {len(fall_sequences)} séquences de chutes trouvées")

    # Charger séquences ADL (non-chutes) pour faux positifs
    adl_sequences = load_urfd_sequences('adl')
    print(f"✅ {len(adl_sequences)} séquences ADL (non-chutes) trouvées")

    if len(fall_sequences) == 0:
        print("❌ Aucune séquence trouvée. Télécharger le dataset :")
        print("   git clone https://github.com/Hromeir/URFD-Dataset.git")
        return

    y_true = []
    y_pred = []

    # Tester séquences de chutes (label=1)
    print("\n📊 Traitement séquences de chutes...")
    for i, seq_path in enumerate(fall_sequences[:5]):  # Limiter à 5 pour rapidité
        print(f"  [{i+1}/{min(5, len(fall_sequences))}] {os.path.basename(seq_path)}...", end='', flush=True)

        frames = load_rgb_frames(seq_path)
        if len(frames) == 0:
            print(" ⚠️ Pas de frames")
            continue

        detections = run_fall_detection(frames)

        # Si > 0 chutes détectées = positive
        has_fall_detected = len(detections['falls']) > 0
        y_true.append(1)  # C'est une séquence de chute
        y_pred.append(1 if has_fall_detected else 0)

        print(f" ✓ {len(detections['falls'])} chutes détectées")

    # Tester séquences ADL (label=0)
    print("\n📊 Traitement séquences ADL (non-chutes)...")
    for i, seq_path in enumerate(adl_sequences[:5]):
        print(f"  [{i+1}/{min(5, len(adl_sequences))}] {os.path.basename(seq_path)}...", end='', flush=True)

        frames = load_rgb_frames(seq_path)
        if len(frames) == 0:
            print(" ⚠️ Pas de frames")
            continue

        detections = run_fall_detection(frames)

        has_fall_detected = len(detections['falls']) > 0
        y_true.append(0)  # Ce n'est pas une chute
        y_pred.append(1 if has_fall_detected else 0)

        print(f" ✓ {len(detections['falls'])} chutes détectées (faux positifs)")

    # Calculer métriques
    print("\n" + "="*60)
    print("📈 RÉSULTATS")
    print("="*60)

    metrics = compute_metrics(y_true, y_pred)

    print(f"\n✅ TP (Chutes correctement détectées) : {metrics['TP']}")
    print(f"❌ FN (Chutes manquées) : {metrics['FN']}")
    print(f"⚠️  FP (Fausses alertes) : {metrics['FP']}")

    print(f"\n📊 Précision : {metrics['precision']:.3f}")
    print(f"📊 Rappel : {metrics['recall']:.3f}")
    print(f"📊 F1-Score : {metrics['f1']:.3f}")

    # Matrice de confusion texte
    print("\n" + "="*60)
    print("🔲 MATRICE DE CONFUSION")
    print("="*60)
    print(f"\n             Prédiction")
    print(f"          Pas Chute | Chute")
    print(f"Réel Pas  [{metrics['TP']:3d}] | [{metrics['FP']:3d}]")
    print(f"     Oui  [{metrics['FN']:3d}] | [---]")

    # Sauvegarder résultats
    results = {
        'dataset': 'UR Fall Detection',
        'sequences_fall': len(fall_sequences),
        'sequences_adl': len(adl_sequences),
        'metrics': {
            'TP': int(metrics['TP']),
            'FP': int(metrics['FP']),
            'FN': int(metrics['FN']),
            'precision': float(metrics['precision']),
            'recall': float(metrics['recall']),
            'f1': float(metrics['f1'])
        }
    }

    results_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_falls_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Résultats sauvegardés : {results_file}")
    print("\n" + "="*60)


if __name__ == '__main__':
    test_falls_urfd()
