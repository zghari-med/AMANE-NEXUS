"""Modèle analyse."""

from datetime import datetime
from mongoengine import Document, StringField, ReferenceField, DateTimeField, ListField, DictField, IntField, FloatField
from .video import Video
from .user import User


class Analysis(Document):
    """Modèle pour stocker les résultats d'analyse."""

    video = ReferenceField(Video, required=True)
    user = ReferenceField(User, required=True)

    # Statut
    status = StringField(
        choices=["pending", "processing", "completed", "failed"],
        default="pending"
    )

    # Résultats d'analyse
    total_events = IntField(default=0)
    falls_detected = IntField(default=0)
    crowds_detected = IntField(default=0)
    abandoned_objects = IntField(default=0)

    # Statistiques détaillées
    events_timeline = ListField(DictField())  # [{"type": "fall", "time": 12.5, "confidence": 0.95}, ...]
    alerts_generated = ListField(StringField())  # [alert_id1, alert_id2, ...]

    # Performance
    processing_time = FloatField(required=False)  # en secondes
    average_fps = FloatField(required=False)
    cpu_usage = FloatField(required=False)  # en %

    # Métadonnées
    camera_id = StringField(default="cam_01")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(required=False)

    # Exportation
    export_formats = ListField(StringField(choices=["csv", "json", "pdf"]))

    meta = {
        "collection": "analyses",
        "indexes": ["video", "user", "status", "created_at"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "video_id": str(self.video.id),
            "video_title": self.video.title,
            "user": self.user.username,
            "status": self.status,
            "total_events": self.total_events,
            "falls_detected": self.falls_detected,
            "crowds_detected": self.crowds_detected,
            "abandoned_objects": self.abandoned_objects,
            "processing_time": self.processing_time,
            "average_fps": self.average_fps,
            "cpu_usage": self.cpu_usage,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
