"""
Tests unitaires pour benchmark_results.json et BenchmarkLoader.
Valident la structure, les valeurs scientifiques clés et le chargement.
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BENCHMARK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "benchmark_results.json"
)


class TestBenchmarkFileExists(unittest.TestCase):
    """Vérifie que benchmark_results.json existe et est lisible."""

    def test_file_exists(self):
        """benchmark_results.json doit exister."""
        self.assertTrue(
            os.path.exists(BENCHMARK_PATH),
            f"Fichier manquant : {BENCHMARK_PATH}"
        )

    def test_file_is_valid_json(self):
        """Le fichier doit être un JSON valide."""
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)


class TestBenchmarkStructure(unittest.TestCase):
    """Vérifie que la structure JSON des benchmarks est complète."""

    @classmethod
    def setUpClass(cls):
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_top_level_keys_present(self):
        """Toutes les clés de premier niveau requises sont présentes."""
        required = [
            "environment", "yolo_inference_benchmarks",
            "model_accuracy", "by_behavior"
        ]
        for key in required:
            self.assertIn(key, self.data, f"Clé manquante : {key}")

    def test_environment_fields(self):
        """L'environnement contient cpu, ram_gb, python_version."""
        env = self.data["environment"]
        for field in ["cpu", "ram_gb", "python_version", "yolo_model"]:
            self.assertIn(field, env, f"Champ env manquant : {field}")

    def test_yolo_inference_avg_ms(self):
        """Temps d'inférence moyen doit être entre 100ms et 500ms (CPU)."""
        avg_ms = self.data["yolo_inference_benchmarks"]["avg_inference_ms"]
        self.assertGreater(avg_ms, 100)
        self.assertLess(avg_ms, 500)

    def test_yolo_avg_fps(self):
        """FPS moyen doit être cohérent avec le temps d'inférence."""
        benchmarks = self.data["yolo_inference_benchmarks"]
        avg_ms = benchmarks["avg_inference_ms"]
        avg_fps = benchmarks["avg_fps"]
        expected_fps = 1000 / avg_ms
        self.assertAlmostEqual(avg_fps, expected_fps, delta=1.0,
            msg=f"FPS incohérent : {avg_fps} vs {expected_fps:.1f} attendu")

    def test_global_f1_equals_0627(self):
        """F1-score global doit être 0.627 (±0.01) — validé END-TO-END."""
        f1 = self.data["model_accuracy"]["global"]["f1_score"]
        self.assertAlmostEqual(f1, 0.627, delta=0.01,
            msg=f"F1 attendu 0.627, obtenu {f1}")

    def test_global_precision(self):
        """Précision globale doit être 57.2% (±0.5)."""
        precision = self.data["model_accuracy"]["global"]["precision_pct"]
        self.assertAlmostEqual(precision, 57.2, delta=0.5,
            msg=f"Précision attendue 57.2%, obtenu {precision}%")

    def test_global_recall(self):
        """Rappel global doit être 76.4% (±0.5)."""
        recall = self.data["model_accuracy"]["global"]["recall_pct"]
        self.assertAlmostEqual(recall, 76.4, delta=0.5,
            msg=f"Rappel attendu 76.4%, obtenu {recall}%")

    def test_by_behavior_has_three_types(self):
        """by_behavior doit contenir fall, crowding, abandoned_object."""
        bb = self.data["by_behavior"]
        for btype in ["fall", "crowding", "abandoned_object"]:
            self.assertIn(btype, bb, f"Comportement manquant : {btype}")

    def test_each_behavior_has_metrics(self):
        """Chaque comportement a validation avec precision_pct, recall_pct, f1_score."""
        bb = self.data["by_behavior"]
        for btype, behavior in bb.items():
            self.assertIn("validation", behavior,
                f"{btype} manque la clé 'validation'")
            v = behavior["validation"]
            for field in ["precision_pct", "recall_pct", "f1_score",
                          "true_positives", "false_positives", "false_negatives"]:
                self.assertIn(field, v,
                    f"{btype}.validation manque le champ {field}")

    def test_f1_consistency_by_behavior(self):
        """F1 de chaque comportement est cohérent avec P et R."""
        bb = self.data["by_behavior"]
        for btype, behavior in bb.items():
            v = behavior["validation"]
            p = v["precision_pct"] / 100
            r = v["recall_pct"] / 100
            if (p + r) > 0:
                expected_f1 = 2 * p * r / (p + r)
                self.assertAlmostEqual(
                    v["f1_score"], expected_f1, delta=0.01,
                    msg=f"F1 incohérent pour {btype}"
                )


class TestBenchmarkLoader(unittest.TestCase):
    """Teste le chargement via BenchmarkLoader."""

    def test_benchmark_loader_returns_dict(self):
        """BenchmarkLoader.get_or_load() retourne un dict non vide."""
        from services.analytics_service import BenchmarkLoader
        data = BenchmarkLoader.get_or_load()
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 0)

    def test_benchmark_loader_has_f1(self):
        """BenchmarkLoader expose bien le F1=0.627 (validé END-TO-END)."""
        from services.analytics_service import BenchmarkLoader
        data = BenchmarkLoader.get_or_load()
        f1 = data["model_accuracy"]["global"]["f1_score"]
        self.assertAlmostEqual(f1, 0.627, delta=0.01)

    def test_benchmark_loader_caches(self):
        """Deux appels successifs retournent le même objet (cache)."""
        from services.analytics_service import BenchmarkLoader
        BenchmarkLoader.reload()  # reset cache
        d1 = BenchmarkLoader.get_or_load()
        d2 = BenchmarkLoader.get_or_load()
        self.assertIs(d1, d2, "Le cache ne fonctionne pas (objets différents)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
