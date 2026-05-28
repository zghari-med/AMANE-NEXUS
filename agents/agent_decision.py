"""
Agent Décision — Évaluation du risque et génération des alertes
Rôle : S'abonner à l'analyse, évaluer le niveau de risque,
       générer des alertes et centraliser les événements.
Canal entrée  : channel:analysis
Canal sortie  : channel:alerts
"""

import redis
import json
import time
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AgentDecision] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

# Constantes
CHANNEL_IN = "channel:analysis"
CHANNEL_OUT = "channel:alerts"
CAMERA_ID = "cam_01"
LOG_INTERVAL = 5.0

# Matrice de sévérité des risques
RISK_LEVELS = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# Évaluation des événements
EVENT_RISK_MATRIX = {
    "fall": {
        "base_risk": "high",
        "escalation": True,
        "notification": True,
    },
    "crowding": {
        "base_risk": "medium",
        "escalation": False,
        "notification": True,
    },
    "abandoned_object": {
        "base_risk": "medium",
        "escalation": True,
        "notification": True,
    },
}


class RiskEvaluator:
    """Évalue le niveau de risque d'un événement."""

    def __init__(self):
        self.event_history = {}  # historique des événements par type
        self.escalation_counter = {}  # compteur d'escalade par type

    def evaluate(self, event: dict) -> dict:
        """
        Évalue le risque d'un événement et détermine l'action.
        """
        event_type = event["type"]

        if event_type not in EVENT_RISK_MATRIX:
            return None

        config = EVENT_RISK_MATRIX[event_type]
        risk_level = config["base_risk"]

        # Escalade du risque si événement répété
        key = f"{event_type}_{event.get('track_id', event.get('crowd_id'))}"

        if key not in self.escalation_counter:
            self.escalation_counter[key] = 0
        else:
            self.escalation_counter[key] += 1

        # Escalade automatique après 3 événements du même type
        if config["escalation"] and self.escalation_counter[key] >= 3:
            risk_level = "critical"

        return {
            "event_type": event_type,
            "risk_level": risk_level,
            "should_notify": config["notification"],
            "escalation_count": self.escalation_counter[key],
            "original_event": event,
        }


class AlertGenerator:
    """Génère et centralise les alertes."""

    def __init__(self):
        self.active_alerts = {}  # alertes actives
        self.alert_history = []  # historique des alertes
        self.alert_id_counter = 0

    def generate_alert(self, risk_eval: dict, frame_id: int,
                      timestamp: float) -> dict:
        """Génère une alerte à partir d'une évaluation de risque."""
        self.alert_id_counter += 1

        alert = {
            "alert_id": f"ALR_{self.alert_id_counter:06d}",
            "event_type": risk_eval["event_type"],
            "risk_level": risk_eval["risk_level"],
            "frame_id": frame_id,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "original_event": risk_eval["original_event"],
            "status": "active",
            "escalation_count": risk_eval["escalation_count"],
        }

        # Stocker dans les alertes actives
        alert_key = f"{risk_eval['event_type']}_{risk_eval['original_event'].get('track_id')}"
        self.active_alerts[alert_key] = alert

        # Ajouter à l'historique
        self.alert_history.append(alert)

        return alert

    def get_alert_summary(self) -> dict:
        """Résumé des alertes actuelles."""
        summary = {
            "total_active": len(self.active_alerts),
            "by_risk_level": {},
            "by_type": {},
        }

        for alert in self.active_alerts.values():
            # Compter par risque
            risk = alert["risk_level"]
            summary["by_risk_level"][risk] = summary["by_risk_level"].get(risk, 0) + 1

            # Compter par type
            event_type = alert["event_type"]
            summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1

        return summary


class NotificationManager:
    """Gère les notifications des alertes."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def send_notification(self, alert: dict):
        """Envoie une notification pour une alerte."""
        notification = {
            "type": "alert_notification",
            "alert_id": alert["alert_id"],
            "event_type": alert["event_type"],
            "risk_level": alert["risk_level"],
            "message": self._format_message(alert),
            "timestamp": alert["created_at"],
        }

        # Publier sur le channel des notifications
        self.redis.publish(
            "channel:notifications",
            json.dumps(notification)
        )

        log.warning(f"⚠️  ALERTE: {notification['message']}")

    def _format_message(self, alert: dict) -> str:
        """Formate le message d'alerte."""
        event_type = alert["event_type"]
        risk = alert["risk_level"]
        event = alert["original_event"]

        messages = {
            "fall": f"Chute détectée (personne {event.get('track_id')}) - Risque: {risk}",
            "crowding": f"Attroupement détecté ({event.get('person_count')} personnes) - Risque: {risk}",
            "abandoned_object": f"Objet abandonné détecté ({event.get('object_type')}) - Risque: {risk}",
        }

        return messages.get(event_type, f"Événement détecté - Risque: {risk}")


class AgentDecision:
    """Agent principal de décision et d'alerte."""

    def __init__(self):
        self.redis_pub = self._connect_redis()
        self.redis_sub = self._connect_redis()

        self.risk_evaluator = RiskEvaluator()
        self.alert_generator = AlertGenerator()
        self.notification_manager = NotificationManager(self.redis_pub)

        self.running = False
        self._log_t0 = time.time()
        self._alert_count = 0

    def _connect_redis(self) -> redis.Redis:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        client = redis.Redis(host=host, port=port, decode_responses=True)
        try:
            client.ping()
            log.info("Connecté à Redis ✓")
        except Exception as e:
            log.error(f"Erreur connexion Redis: {e}")
            raise
        return client

    def run(self):
        """Boucle principale de l'agent."""
        self.running = True
        pubsub = self.redis_sub.pubsub()
        pubsub.subscribe(CHANNEL_IN)

        log.info(f"Agent Décision en écoute sur {CHANNEL_IN}")

        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    self._process_analysis(message["data"])
                    self._log_stats()
        except KeyboardInterrupt:
            log.info("Arrêt de l'agent...")
        finally:
            self.running = False
            pubsub.close()

    def _process_analysis(self, data: str):
        """Traite les résultats d'analyse."""
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return

        events = payload.get("events", [])
        frame_id = payload.get("frame_id", 0)
        timestamp = payload.get("timestamp", time.time())

        for event in events:
            # Évaluer le risque
            risk_eval = self.risk_evaluator.evaluate(event)

            if not risk_eval:
                continue

            # Générer l'alerte
            alert = self.alert_generator.generate_alert(
                risk_eval, frame_id, timestamp
            )

            # Envoyer notification si nécessaire
            if risk_eval["should_notify"]:
                self.notification_manager.send_notification(alert)

            # Publier l'alerte
            self._publish_alert(alert)

            self._alert_count += 1

    def _publish_alert(self, alert: dict):
        """Publie l'alerte sur le channel des alertes."""
        self.redis_pub.publish(
            CHANNEL_OUT,
            json.dumps(alert)
        )

        # Stocker aussi dans Redis pour accès par l'API
        alert_key = f"alert:{alert['alert_id']}"
        self.redis_pub.hset(alert_key, mapping={
            "alert_id": alert["alert_id"],
            "event_type": alert["event_type"],
            "risk_level": alert["risk_level"],
            "timestamp": str(alert["timestamp"]),
            "status": alert["status"],
        })
        self.redis_pub.expire(alert_key, 3600)  # expire après 1h

    def _log_stats(self):
        """Affiche les stats."""
        if time.time() - self._log_t0 >= LOG_INTERVAL:
            summary = self.alert_generator.get_alert_summary()
            log.info(
                f"Alertes générées: {self._alert_count} | "
                f"Actives: {summary['total_active']} | "
                f"Par type: {summary['by_type']}"
            )
            self._log_t0 = time.time()


if __name__ == "__main__":
    agent = AgentDecision()
    agent.run()
