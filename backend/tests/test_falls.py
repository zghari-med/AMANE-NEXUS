"""
Test detection de chutes sur UR Fall Detection Dataset
"""
import os
import json
import sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
URFD_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data', 'URFD-Dataset')
FALL_COOLDOWN = 300
FRAME_SKIP = 3


def load_urfd_sequences(dataset_type='fall'):
    """Charger sequences URFD (fall ou adl)"""
    sequences = []
    urfd_dir = os.path.join(URFD_ROOT, dataset_type)
    if not os.path.exists(urfd_dir):
        return sequences
    for seq_dir in sorted(os.listdir(urfd_dir)):
        seq_path = os.path.join(urfd_dir, seq_dir)
        if os.path.isdir(seq_path):
            sequences.append(seq_path)
    return sequences


def load_rgb_frames(seq_path):
    """Charger frames RGB d'une sequence"""
    rgb_dir = os.path.join(seq_path, 'rgb')
    frames = []
    if not os.path.exists(rgb_dir):
        return frames
    for frame_file in sorted(os.listdir(rgb_dir)):
        if frame_file.endswith('.png'):
            frame = cv2.imread(os.path.join(rgb_dir, frame_file))
            if frame is not None:
                frames.append(frame)
    return frames


def run_fall_detection(frames):
    """Executer detection chutes sur sequence"""
    detections = {'falls': [], 'frame_count': len(frames)}
    if len(frames) == 0:
        return detections

    try:
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
    except Exception:
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
                    if w > 0 and (h / w) < FALL_RATIO:
                        pid = f"{(x1+x2)//40}_{(y1+y2)//40}"
                        if frame_idx - last_fall.get(pid, -FALL_COOLDOWN) >= FALL_COOLDOWN:
                            last_fall[pid] = frame_idx
                            detections['falls'].append({
                                'frame': frame_idx,
                                'ratio': h / w,
                                'bbox': (x1, y1, x2, y2)
                            })
        except Exception:
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
    return {'TP': tp, 'FP': fp, 'FN': fn,
            'precision': precision, 'recall': recall, 'f1': f1}


def test_falls_urfd():
    """Test principal: Detection chutes sur UR Fall Detection"""
    print("\n" + "=" * 60)
    print("TEST DETECTION DE CHUTES - UR Fall Detection Dataset")
    print("=" * 60)

    fall_sequences = load_urfd_sequences('fall')
    adl_sequences = load_urfd_sequences('adl')

    print(f"\n{len(fall_sequences)} sequences de chutes trouvees")
    print(f"{len(adl_sequences)} sequences ADL (non-chutes) trouvees")

    if len(fall_sequences) == 0:
        print("Aucune sequence trouvee - dataset absent, test ignore")
        return

    y_true = []
    y_pred = []

    for i, seq_path in enumerate(fall_sequences[:5]):
        print(f"  [{i+1}/5] {os.path.basename(seq_path)}...", end='', flush=True)
        frames = load_rgb_frames(seq_path)
        if not frames:
            print(" pas de frames")
            continue
        detections = run_fall_detection(frames)
        y_true.append(1)
        y_pred.append(1 if detections['falls'] else 0)
        print(f" {len(detections['falls'])} chutes detectees")

    for i, seq_path in enumerate(adl_sequences[:5]):
        print(f"  [{i+1}/5] {os.path.basename(seq_path)}...", end='', flush=True)
        frames = load_rgb_frames(seq_path)
        if not frames:
            print(" pas de frames")
            continue
        detections = run_fall_detection(frames)
        y_true.append(0)
        y_pred.append(1 if detections['falls'] else 0)
        print(f" {len(detections['falls'])} (faux positifs)")

    metrics = compute_metrics(y_true, y_pred)

    print(f"\nTP={metrics['TP']} FP={metrics['FP']} FN={metrics['FN']}")
    print(f"Precision : {metrics['precision']:.3f}")
    print(f"Recall    : {metrics['recall']:.3f}")
    print(f"F1-Score  : {metrics['f1']:.3f}")

    results = {
        'dataset': 'UR Fall Detection',
        'sequences_fall': len(fall_sequences),
        'sequences_adl': len(adl_sequences),
        'metrics': {k: (int(v) if isinstance(v, bool) else
                        float(v) if isinstance(v, float) else int(v))
                    for k, v in metrics.items()}
    }
    results_file = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'test_falls_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResultats sauvegardes: {results_file}")


if __name__ == '__main__':
    test_falls_urfd()
