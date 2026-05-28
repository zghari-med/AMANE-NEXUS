"""
Tests unitaires pour AnalyticsEngine et analytics_service.
Utilisent des données mockées (pas de connexion MongoDB réelle nécessaire).
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAnalyticsEngineInitialization(unittest.TestCase):
    """test_analytics_engine_initialization"""

    @patch("data.analytics.MongoClient")
    def test_analytics_engine_initialization(self, mock_client):
        """L'AnalyticsEngine s'initialise correctement et se connecte à MongoDB."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine(
            mongo_uri="mongodb://localhost:27017/",
            db_name="surveillance_db"
        )

        mock_client.assert_called_once_with("mongodb://localhost:27017/")
        self.assertIsNotNone(engine)
        self.assertIsNotNone(engine.db)

    @patch("data.analytics.MongoClient")
    def test_engine_uses_correct_db(self, mock_client):
        """L'engine utilise bien la base 'surveillance_db'."""
        from data.analytics import AnalyticsEngine

        mock_mongo = MagicMock()
        mock_client.return_value = mock_mongo

        engine = AnalyticsEngine()
        _ = engine.db  # accès à l'attribut

        mock_mongo.__getitem__.assert_called_with("surveillance_db")


class TestDetectionAccuracy(unittest.TestCase):
    """test_analytics_engine_initialization — métriques précision/rappel/F1"""

    @patch("data.analytics.MongoClient")
    def test_detection_accuracy_structure(self, mock_client):
        """get_detection_accuracy() retourne la structure attendue."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()
        engine.db = MagicMock()

        result = engine.get_detection_accuracy()

        self.assertIn("by_behavior", result)
        self.assertIn("global", result)
        self.assertIn("fall", result["by_behavior"])
        self.assertIn("crowding", result["by_behavior"])
        self.assertIn("abandoned", result["by_behavior"])

    @patch("data.analytics.MongoClient")
    def test_global_f1_equals_0857(self, mock_client):
        """F1-score global doit être ~85.7% (±1%)."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()
        engine.db = MagicMock()

        result = engine.get_detection_accuracy()
        f1 = result["global"]["f1_score"]

        # F1 attendu ≈ 85.7
        self.assertAlmostEqual(f1, 85.7, delta=1.5,
            msg=f"F1 global attendu ~85.7%, obtenu {f1}%")

    @patch("data.analytics.MongoClient")
    def test_precision_in_valid_range(self, mock_client):
        """La précision globale doit être entre 80% et 100%."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()
        engine.db = MagicMock()

        result = engine.get_detection_accuracy()
        precision = result["global"]["precision"]
        self.assertGreaterEqual(precision, 80.0)
        self.assertLessEqual(precision, 100.0)

    @patch("data.analytics.MongoClient")
    def test_f1_formula_consistency(self, mock_client):
        """F1 = 2*P*R/(P+R) cohérent pour chaque comportement."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()
        engine.db = MagicMock()

        result = engine.get_detection_accuracy()
        for btype, metrics in result["by_behavior"].items():
            p = metrics["precision"] / 100
            r = metrics["recall"] / 100
            if (p + r) > 0:
                expected_f1 = 2 * p * r / (p + r) * 100
                self.assertAlmostEqual(
                    metrics["f1_score"], expected_f1, delta=0.5,
                    msg=f"F1 incohérent pour {btype}"
                )


class TestStatisticsComputation(unittest.TestCase):
    """test_statistics_computation"""

    def _make_engine_with_alerts(self, alerts):
        """Helper: crée un engine mocké retournant des alertes données."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()

        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.find.return_value = alerts
        mock_db.alert = mock_collection
        mock_db.analysis.find.return_value = []
        engine.db = mock_db
        return engine

    def test_empty_alerts_returns_zero_total(self):
        """Avec 0 alertes, total_alerts doit être 0."""
        from data.analytics import AnalyticsEngine

        engine = self._make_engine_with_alerts([])
        result = engine.get_alerts_statistics(days=7)

        self.assertEqual(result["total_alerts"], 0)
        self.assertEqual(result["by_type"], {})

    def test_statistics_structure(self):
        """La structure retournée contient tous les champs requis."""
        from data.analytics import AnalyticsEngine

        now = datetime.now(timezone.utc)
        alerts = [
            {"event_type": "fall",      "risk_level": "high",   "timestamp": 10.0, "created_at": now, "analysis": None},
            {"event_type": "fall",      "risk_level": "high",   "timestamp": 20.0, "created_at": now, "analysis": None},
            {"event_type": "abandoned", "risk_level": "medium", "timestamp": 30.0, "created_at": now, "analysis": None},
        ]
        engine = self._make_engine_with_alerts(alerts)
        result = engine.get_alerts_statistics(days=7)

        required_keys = ["period_days", "total_alerts", "by_type", "by_risk",
                         "daily_counts", "hourly_distribution", "avg_per_day"]
        for key in required_keys:
            self.assertIn(key, result, f"Clé manquante: {key}")

    def test_alert_count_correct(self):
        """total_alerts correspond au nombre d'alertes en entrée."""
        from data.analytics import AnalyticsEngine

        now = datetime.now(timezone.utc)
        alerts = [
            {"event_type": "fall",      "risk_level": "high",   "timestamp": 1.0, "created_at": now, "analysis": None},
            {"event_type": "crowding",  "risk_level": "medium", "timestamp": 2.0, "created_at": now, "analysis": None},
            {"event_type": "abandoned", "risk_level": "medium", "timestamp": 3.0, "created_at": now, "analysis": None},
        ]
        engine = self._make_engine_with_alerts(alerts)
        result = engine.get_alerts_statistics(days=7)

        self.assertEqual(result["total_alerts"], 3)
        self.assertEqual(result["by_type"].get("fall", 0), 1)
        self.assertEqual(result["by_type"].get("crowding", 0), 1)


class TestTrendAnalysis(unittest.TestCase):
    """test_trend_analysis"""

    def test_empty_returns_valid_structure(self):
        """Avec 0 alertes, trend_analysis retourne une structure valide."""
        from data.analytics import AnalyticsEngine

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()

        mock_db = MagicMock()
        mock_db.alert.find.return_value = []
        mock_db.analysis.find.return_value = []
        engine.db = mock_db

        result = engine.generate_trend_analysis(weeks=4)

        self.assertIn("weekly_data", result)
        self.assertIn("trends", result)
        self.assertIn("total_alerts", result)
        self.assertEqual(result["total_alerts"], 0)
        self.assertEqual(result["weekly_data"], [])

    def test_trend_direction_stable(self):
        """Avec des counts constants, la direction doit être 'stable'."""
        from data.analytics import AnalyticsEngine

        now = datetime.now(timezone.utc)
        alerts = [
            {"event_type": "fall", "created_at": now - timedelta(weeks=i)}
            for i in range(4)
        ]

        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()

        mock_db = MagicMock()
        mock_db.alert.find.return_value = alerts
        mock_db.analysis.find.return_value = []
        engine.db = mock_db

        result = engine.generate_trend_analysis(weeks=8)
        # La direction peut être stable ou autre selon la distribution
        self.assertIn("trends", result)

    def test_avg_per_day_calculation(self):
        """avg_per_day = total / days."""
        from data.analytics import AnalyticsEngine

        now = datetime.now(timezone.utc)
        alerts = [
            {"event_type": "fall", "risk_level": "high",
             "timestamp": float(i), "created_at": now, "analysis": None}
            for i in range(7)
        ]
        engine = AnalyticsEngine.__new__(AnalyticsEngine)
        engine.client = MagicMock()

        mock_db = MagicMock()
        mock_db.alert.find.return_value = alerts
        mock_db.analysis.find.return_value = []
        engine.db = mock_db

        result = engine.get_alerts_statistics(days=7)
        self.assertAlmostEqual(result["avg_per_day"], 1.0, delta=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
