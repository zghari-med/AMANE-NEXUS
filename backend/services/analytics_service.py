"""
AnalyticsService — façade singleton encapsulant AnalyticsEngine.
Fournit un lazy-loading des benchmarks et un cache simple en mémoire.
"""

import json
import os
import time
import logging

from data.analytics import AnalyticsEngine

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCHMARK_PATH = os.path.join(BASE_DIR, "data", "benchmark_results.json")
CACHE_TTL = int(os.environ.get("ANALYTICS_CACHE_TTL", 3600))  # 1h par défaut


class _Cache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        entry = self._store.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL:
            return entry["data"]
        return None

    def set(self, key, data):
        self._store[key] = {"data": data, "ts": time.time()}

    def invalidate(self, key=None):
        if key:
            self._store.pop(key, None)
        else:
            self._store.clear()


_cache = _Cache()
_engine = None


def _get_engine() -> AnalyticsEngine:
    global _engine
    if _engine is None:
        _engine = AnalyticsEngine()
    return _engine


# ── API publique ───────────────────────────────────────────────────────────

def get_alerts_statistics(days: int = 7, user_id: str = None) -> dict:
    """Stats agrégées des alertes sur N jours (avec cache)."""
    key = f"alerts_stats_{days}_{user_id}"
    cached = _cache.get(key)
    if cached:
        return cached
    result = _get_engine().get_alerts_statistics(days=days, user_id=user_id)
    _cache.set(key, result)
    return result


def get_detection_accuracy() -> dict:
    """Précision/Rappel/F1 par comportement (avec cache)."""
    key = "detection_accuracy"
    cached = _cache.get(key)
    if cached:
        return cached
    result = _get_engine().get_detection_accuracy()
    _cache.set(key, result)
    return result


def generate_trend_analysis(weeks: int = 8, user_id: str = None) -> dict:
    """Tendances hebdomadaires (avec cache)."""
    key = f"trends_{weeks}_{user_id}"
    cached = _cache.get(key)
    if cached:
        return cached
    result = _get_engine().generate_trend_analysis(weeks=weeks, user_id=user_id)
    _cache.set(key, result)
    return result


def get_analysis_statistics(analysis_id: str) -> dict:
    """Stats Pandas détaillées pour une analyse spécifique."""
    key = f"analysis_stats_{analysis_id}"
    cached = _cache.get(key)
    if cached:
        return cached
    result = _get_engine().get_analysis_statistics(analysis_id)
    _cache.set(key, result)
    return result


def export_metrics_csv(analysis_id: str) -> str:
    """Exporte les alertes d'une analyse en CSV (string)."""
    return _get_engine().export_metrics_csv(analysis_id)


# ── BenchmarkLoader ────────────────────────────────────────────────────────

class BenchmarkLoader:
    """
    Charge et expose le fichier benchmark_results.json.
    Implémente un lazy-loading avec cache mémoire.
    """

    _data = None
    _loaded_at = 0

    @classmethod
    def get_or_load(cls) -> dict:
        """Retourne les benchmarks, rechargés si le fichier a changé."""
        try:
            mtime = os.path.getmtime(BENCHMARK_PATH)
        except FileNotFoundError:
            return {"error": "benchmark_results.json not found"}

        if cls._data is None or mtime > cls._loaded_at:
            with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
                cls._data = json.load(f)
            cls._loaded_at = mtime
            log.info("Benchmarks rechargés depuis %s", BENCHMARK_PATH)

        return cls._data

    @classmethod
    def reload(cls):
        cls._data = None


def get_benchmarks() -> dict:
    """Retourne le contenu du fichier benchmark_results.json."""
    return BenchmarkLoader.get_or_load()


def invalidate_cache():
    """Invalide tous les caches (utile après une nouvelle analyse)."""
    _cache.invalidate()
    BenchmarkLoader.reload()
