"""Modèle alerte."""

from datetime import datetime
from mongoengine import Document, StringField, ReferenceField, DateTimeField, DictField, IntField
from .analysis import Analysis
from .user import User


class Alert(Document):
    """Modèle pour stocker les alertes générées."""

    analysis = ReferenceField(Analysis, required=True)
    user = ReferenceField(User, required=True)

    # Type d'alerte
    event_type = StringField(
        choices=["fall", "crowding", "abandoned_object"],
        required=True
    )

    # Niveau de risque
    risk_level = StringField(
        choices=["low", "medium", "high", "critical"],
        required=True
    )

    # Détails de l'événement
    event_details = DictField()  # détails spécifiques de l'événement

    # Localisation dans la vidéo
    frame_id = IntField(required=False)
    timestamp = IntField(required=False)  # en secondes depuis le début de la vidéo

    # Statut
    status = StringField(
        choices=["active", "acknowledged", "resolved"],
        default="active"
    )

    # Notifications
    notification_sent = StringField(required=False)
    acknowledged_at = DateTimeField(required=False)
    acknowledged_by = ReferenceField(User, required=False)

    # Dates
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "alerts",
        "indexes": ["analysis", "user", "event_type", "risk_level", "status", "created_at"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "analysis_id": str(self.analysis.id),
            "event_type": self.event_type,
            "risk_level": self.risk_level,
            "event_details": self.event_details,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }
