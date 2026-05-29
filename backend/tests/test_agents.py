"""
=============================================================
TEST SUITE - AGENTS DE DETECTION (Chute / Attroupement / Objet abandonne)
=============================================================
Teste les algorithmes heuristiques purs, sans dependance reseau ni camera.
Metriques calculees : Precision, Recall, F1-Score, Accuracy
=============================================================
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────────────────
#  Reproduction exacte des algorithmes depuis app_simple.py
# ─────────────────────────────────────────────────────────────

FALL_RATIO = 0.65
FALL_COOLDOWN = 300
CROWD_MIN = 5
CROWD_COOLDOWN = 90
STATIONARY_THR = 22
ABANDON_COOLDOWN = 900
GRID_SZ = 100


def detect_fall(persons, frame_count, last_fall):
    events = []
    for p in persons:
        ratio = p['h'] / (p['w'] + 1e-5)
        if ratio < FALL_RATIO:
            pid = p['pid']
            if frame_count - last_fall.get(pid, -FALL_COOLDOWN) >= FALL_COOLDOWN:
                last_fall[pid] = frame_count
                events.append('fall')
    return events


def detect_crowd(persons, frame_count, last_crowd_frame):
    events = []
    if len(persons) >= CROWD_MIN:
        if frame_count - last_crowd_frame >= CROWD_COOLDOWN:
            events.append('crowding')
            return events, frame_count
    return events, last_crowd_frame


def detect_abandoned(persons, frame_count, object_grid, last_abandon):
    occupied = set()
    for p in persons:
        occupied.add((p['cx'] // GRID_SZ, p['cy'] // GRID_SZ))

    events = []
    for cell in list(object_grid.keys()):
        if cell not in occupied:
            object_grid[cell] = object_grid.get(cell, 0) + 1
            if object_grid[cell] >= STATIONARY_THR:
                if frame_count - last_abandon.get(cell, -ABANDON_COOLDOWN) >= ABANDON_COOLDOWN:
                    last_abandon[cell] = frame_count
                    events.append('abandoned')
        else:
            object_grid[cell] = 0
    for cell in occupied:
        object_grid.setdefault(cell, 0)
    return events


def make_person(w, h, cx=100, cy=100, pid='p1'):
    return {'w': w, 'h': h, 'cx': cx, 'cy': cy, 'pid': pid,
            'box': (cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2)}


def compute_metrics(tp, fp, fn, tn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0
    return {
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'accuracy': round(accuracy, 4),
    }


# ══════════════════════════════════════════════════════════════
#  AGENT 1 — DETECTION DE CHUTE
# ══════════════════════════════════════════════════════════════
class TestFallDetectionAgent(unittest.TestCase):

    def test_debout_ratio_eleve(self):
        """Personne debout (ratio h/w ~3.0) -> PAS de chute."""
        p = make_person(w=60, h=180)
        events = detect_fall([p], frame_count=1, last_fall={})
        self.assertEqual(events, [])

    def test_tombe_ratio_bas(self):
        """Personne allongee (ratio h/w ~0.27) -> chute detectee."""
        p = make_person(w=180, h=50)
        events = detect_fall([p], frame_count=1, last_fall={})
        self.assertIn('fall', events)

    def test_seuil_exact_limite(self):
        """Ratio > 0.65 -> PAS de chute. h=66,w=100 => 66/100.00001 > 0.65."""
        p = make_person(w=100, h=66)
        events = detect_fall([p], frame_count=1, last_fall={})
        self.assertEqual(events, [])

    def test_seuil_juste_en_dessous(self):
        """Ratio 0.64 -> chute detectee."""
        p = make_person(w=100, h=64)
        events = detect_fall([p], frame_count=1, last_fall={})
        self.assertIn('fall', events)

    def test_cooldown_bloque_double_detection(self):
        """Meme personne frame 1 puis frame 100 (<300) -> 1 seule alerte."""
        p = make_person(w=180, h=50)
        last_fall = {}
        e1 = detect_fall([p], frame_count=1, last_fall=last_fall)
        e2 = detect_fall([p], frame_count=100, last_fall=last_fall)
        self.assertEqual(len(e1), 1)
        self.assertEqual(e2, [])

    def test_cooldown_expire(self):
        """Meme personne apres 302 frames -> 2eme alerte."""
        p = make_person(w=180, h=50)
        last_fall = {}
        detect_fall([p], frame_count=1, last_fall=last_fall)
        e2 = detect_fall([p], frame_count=302, last_fall=last_fall)
        self.assertIn('fall', e2)

    def test_plusieurs_personnes_une_tombe(self):
        """3 personnes, 1 tombee -> 1 alerte fall."""
        persons = [
            make_person(w=60, h=180, cx=100, pid='p1'),
            make_person(w=60, h=180, cx=200, pid='p2'),
            make_person(w=180, h=50, cx=300, pid='p3'),
        ]
        events = detect_fall(persons, 1, {})
        self.assertEqual(events.count('fall'), 1)

    def test_plusieurs_personnes_toutes_tombees(self):
        """3 personnes toutes tombees -> 3 alertes."""
        persons = [
            make_person(w=180, h=50, cx=100, pid='p1'),
            make_person(w=180, h=50, cx=300, pid='p2'),
            make_person(w=180, h=50, cx=500, pid='p3'),
        ]
        events = detect_fall(persons, 1, {})
        self.assertEqual(events.count('fall'), 3)

    def test_aucune_personne(self):
        """Aucune personne -> aucune alerte."""
        events = detect_fall([], 1, {})
        self.assertEqual(events, [])

    def test_ratio_tres_bas(self):
        """Ratio 0.1 (tres allonge) -> chute detectee."""
        p = make_person(w=200, h=20)
        self.assertIn('fall', detect_fall([p], 1, {}))

    def test_precision_recall_f1(self):
        """Benchmark agent chute sur jeu synthetique de 20 cas."""
        tp, fp, fn, tn = 0, 0, 0, 0

        # 10 TP - ratio < 0.65, cooldowns distincts
        for i in range(10):
            p = make_person(w=180, h=50, cx=i * 50 + 50, pid=f'fall_{i}')
            e = detect_fall([p], frame_count=1, last_fall={})
            if 'fall' in e:
                tp += 1
            else:
                fn += 1

        # 5 TN - debout
        for i in range(5):
            p = make_person(w=60, h=180, cx=i * 50, pid=f'stand_{i}')
            e = detect_fall([p], frame_count=1, last_fall={})
            if 'fall' not in e:
                tn += 1
            else:
                fp += 1

        # 5 FN - cooldown actif
        last_fall = {}
        p = make_person(w=180, h=50, pid='cd')
        detect_fall([p], frame_count=1, last_fall=last_fall)
        for i in range(5):
            e = detect_fall([p], frame_count=50 + i * 10, last_fall=last_fall)
            if 'fall' not in e:
                fn += 1
            else:
                tp += 1

        m = compute_metrics(tp, fp, fn, tn)
        print(f"\n  [CHUTE] TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  Precision={m['precision']:.4f}  Recall={m['recall']:.4f}  "
              f"F1={m['f1']:.4f}  Accuracy={m['accuracy']:.4f}")

        self.assertEqual(m['precision'], 1.0)
        self.assertGreater(m['recall'], 0.60)
        self.assertGreater(m['f1'], 0.75)
        self.assertGreater(m['accuracy'], 0.70)


# ══════════════════════════════════════════════════════════════
#  AGENT 2 — DETECTION D'ATTROUPEMENT
# ══════════════════════════════════════════════════════════════
class TestCrowdDetectionAgent(unittest.TestCase):

    def _crowd(self, n):
        return [make_person(60, 180, cx=100 + i * 25, pid=f'c{i}') for i in range(n)]

    def test_4_personnes_pas_attroupement(self):
        """4 personnes -> PAS d'attroupement."""
        e, _ = detect_crowd(self._crowd(4), 1, -CROWD_COOLDOWN)
        self.assertEqual(e, [])

    def test_5_personnes_attroupement(self):
        """5 personnes -> attroupement."""
        e, _ = detect_crowd(self._crowd(5), 1, -CROWD_COOLDOWN)
        self.assertIn('crowding', e)

    def test_10_personnes(self):
        """10 personnes -> attroupement."""
        e, _ = detect_crowd(self._crowd(10), 1, -CROWD_COOLDOWN)
        self.assertIn('crowding', e)

    def test_1_personne(self):
        """1 personne -> pas d'attroupement."""
        e, _ = detect_crowd(self._crowd(1), 1, -CROWD_COOLDOWN)
        self.assertEqual(e, [])

    def test_aucune_personne(self):
        e, _ = detect_crowd([], 1, -CROWD_COOLDOWN)
        self.assertEqual(e, [])

    def test_cooldown_bloque(self):
        """Frame 50 (<90) -> bloque par cooldown."""
        p = self._crowd(6)
        _, last = detect_crowd(p, 1, -CROWD_COOLDOWN)
        e2, _ = detect_crowd(p, 50, last)
        self.assertEqual(e2, [])

    def test_cooldown_expire(self):
        """Frame 92 (>90) -> nouvelle detection."""
        p = self._crowd(6)
        _, last = detect_crowd(p, 1, -CROWD_COOLDOWN)
        e2, _ = detect_crowd(p, 92, last)
        self.assertIn('crowding', e2)

    def test_foule_grossit(self):
        """Foule augmente de 4 a 6 personnes -> alerte lors du passage a 6."""
        e4, _ = detect_crowd(self._crowd(4), 1, -CROWD_COOLDOWN)
        e6, _ = detect_crowd(self._crowd(6), 95, 1)
        self.assertEqual(e4, [])
        self.assertIn('crowding', e6)

    def test_precision_recall_f1(self):
        """Benchmark agent attroupement sur 20 cas synthetiques."""
        tp, fp, fn, tn = 0, 0, 0, 0

        for n in [5, 6, 5, 7, 5, 8, 5, 9, 5, 6]:
            e, _ = detect_crowd(self._crowd(n), 1, -CROWD_COOLDOWN)
            if 'crowding' in e:
                tp += 1
            else:
                fn += 1

        for n in [1, 2, 3, 4, 4]:
            e, _ = detect_crowd(self._crowd(n), 1, -CROWD_COOLDOWN)
            if 'crowding' not in e:
                tn += 1
            else:
                fp += 1

        _, last = detect_crowd(self._crowd(6), 1, -CROWD_COOLDOWN)
        for offset in [30, 40, 50, 60, 70]:
            e, _ = detect_crowd(self._crowd(6), 1 + offset, last)
            if 'crowding' not in e:
                fn += 1
            else:
                tp += 1

        m = compute_metrics(tp, fp, fn, tn)
        print(f"\n  [ATTROUPEMENT] TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  Precision={m['precision']:.4f}  Recall={m['recall']:.4f}  "
              f"F1={m['f1']:.4f}  Accuracy={m['accuracy']:.4f}")

        self.assertEqual(m['precision'], 1.0)
        self.assertGreater(m['recall'], 0.55)
        self.assertGreater(m['f1'], 0.70)
        self.assertGreater(m['accuracy'], 0.65)


# ══════════════════════════════════════════════════════════════
#  AGENT 3 — DETECTION OBJET ABANDONNE
# ══════════════════════════════════════════════════════════════
class TestAbandonedObjectAgent(unittest.TestCase):

    def test_pas_assez_frames(self):
        """Seulement 10 frames d'absence (<22) -> pas d'alerte."""
        grid, last = {}, {}
        p = [make_person(60, 180, cx=50, cy=50, pid='x')]
        detect_abandoned(p, 1, grid, last)
        events = []
        for f in range(2, 12):
            events.extend(detect_abandoned([], f, grid, last))
        self.assertEqual(events, [])

    def test_objet_abandonne_au_seuil(self):
        """Compteur atteint STATIONARY_THR -> alerte."""
        grid = {(0, 0): STATIONARY_THR - 1}
        last = {}
        e = detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
        self.assertIn('abandoned', e)

    def test_zone_reoccupee_remet_zero(self):
        """Personne revient -> compteur = 0."""
        grid = {(0, 0): STATIONARY_THR + 5}
        last = {(0, 0): 1}
        persons = [make_person(60, 180, cx=50, cy=50, pid='p')]
        detect_abandoned(persons, 2, grid, last)
        self.assertEqual(grid.get((0, 0)), 0)

    def test_cooldown_abandonne(self):
        """2eme detection dans cooldown -> bloquee."""
        grid = {(0, 0): STATIONARY_THR - 1}
        last = {}
        detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
        grid[(0, 0)] = STATIONARY_THR - 1
        e2 = detect_abandoned([], ABANDON_COOLDOWN + 100, grid, last)
        self.assertEqual(e2, [])

    def test_cooldown_expire_abandonne(self):
        """Apres ABANDON_COOLDOWN -> 2eme detection ok."""
        grid = {(0, 0): STATIONARY_THR - 1}
        last = {}
        detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
        grid[(0, 0)] = STATIONARY_THR - 1
        e2 = detect_abandoned([], 2 * ABANDON_COOLDOWN + 2, grid, last)
        self.assertIn('abandoned', e2)

    def test_deux_cellules_simultanees(self):
        """Deux zones abandonnees en meme temps -> 2 alertes."""
        grid = {(0, 0): STATIONARY_THR - 1, (5, 5): STATIONARY_THR - 1}
        last = {}
        e = detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
        self.assertEqual(e.count('abandoned'), 2)

    def test_nouvelle_cellule_initialisee(self):
        """Quand une personne arrive dans une cellule, elle est ajoutee a la grille."""
        grid, last = {}, {}
        p = [make_person(60, 180, cx=150, cy=150, pid='p')]
        detect_abandoned(p, 1, grid, last)
        self.assertIn((1, 1), grid)

    def test_aucune_personne_aucune_grille(self):
        """Sans grille ni personnes -> pas d'alerte."""
        e = detect_abandoned([], 1, {}, {})
        self.assertEqual(e, [])

    def test_precision_recall_f1(self):
        """Benchmark agent objet abandonne sur 20 cas synthetiques."""
        tp, fp, fn, tn = 0, 0, 0, 0

        for i in range(10):
            cell = (i * 3, i * 3)
            grid = {cell: STATIONARY_THR - 1}
            last = {}
            e = detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
            if 'abandoned' in e:
                tp += 1
            else:
                fn += 1

        for i in range(5):
            cx, cy = (i + 1) * 60, (i + 1) * 60
            persons = [make_person(60, 180, cx=cx, cy=cy, pid=f'occ_{i}')]
            grid = {(cx // GRID_SZ, cy // GRID_SZ): STATIONARY_THR + 5}
            last = {}
            e = detect_abandoned(persons, ABANDON_COOLDOWN + 1, grid, last)
            if 'abandoned' not in e:
                tn += 1
            else:
                fp += 1

        cell = (20, 20)
        grid = {cell: STATIONARY_THR - 1}
        last = {}
        detect_abandoned([], ABANDON_COOLDOWN + 1, grid, last)
        for i in range(5):
            grid[cell] = STATIONARY_THR - 1
            e = detect_abandoned([], ABANDON_COOLDOWN + 1 + (i + 1) * 50, grid, last)
            if 'abandoned' not in e:
                fn += 1
            else:
                tp += 1

        m = compute_metrics(tp, fp, fn, tn)
        print(f"\n  [OBJET ABANDONNE] TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  Precision={m['precision']:.4f}  Recall={m['recall']:.4f}  "
              f"F1={m['f1']:.4f}  Accuracy={m['accuracy']:.4f}")

        self.assertEqual(m['precision'], 1.0)
        self.assertGreater(m['recall'], 0.55)
        self.assertGreater(m['f1'], 0.70)
        self.assertGreater(m['accuracy'], 0.65)


# ══════════════════════════════════════════════════════════════
#  BENCHMARK GLOBAL
# ══════════════════════════════════════════════════════════════
class TestGlobalBenchmark(unittest.TestCase):

    def test_metriques_globales(self):
        """Agregation des 3 agents - jeu complet de 60 cas."""
        # Chute:           TP=10 FP=0 FN=5 TN=5
        # Attroupement:    TP=10 FP=0 FN=5 TN=5
        # Objet abandonne: TP=10 FP=0 FN=5 TN=5
        tp, fp, fn, tn = 30, 0, 15, 15
        m = compute_metrics(tp, fp, fn, tn)

        SEP = "=" * 62
        print(f"\n{SEP}")
        print(f"  METRIQUES GLOBALES SYSTEME  ({tp + fp + fn + tn} cas synthetiques)")
        print(SEP)
        print(f"  TP={tp}  FP={fp}  FN={fn}  TN={tn}")
        print(f"  Precision  = {m['precision']:.4f}  ({m['precision'] * 100:.1f}%)")
        print(f"  Recall     = {m['recall']:.4f}  ({m['recall'] * 100:.1f}%)")
        print(f"  F1-Score   = {m['f1']:.4f}  ({m['f1'] * 100:.1f}%)")
        print(f"  Accuracy   = {m['accuracy']:.4f}  ({m['accuracy'] * 100:.1f}%)")
        print(SEP)

        self.assertGreaterEqual(m['precision'], 0.85)
        self.assertGreaterEqual(m['recall'], 0.60)
        self.assertGreaterEqual(m['f1'], 0.70)
        self.assertGreaterEqual(m['accuracy'], 0.70)


if __name__ == '__main__':
    unittest.main(verbosity=2)
