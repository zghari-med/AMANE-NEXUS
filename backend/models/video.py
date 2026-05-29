"""Modèle vidéo."""

from datetime import datetime
from mongoengine import Document, StringField, ReferenceField, DateTimeField, FloatField, IntField, ListField, BooleanField
from .user import User


class Video(Document):
    """Modèle vidéo uploadée."""

    title = StringField(required=True)
    description = StringField(required=False)
    filename = StringField(required=True, unique=True)
    filepath = StringField(required=True)

    # Uploader
    uploaded_by = ReferenceField(User, required=True)

    # Métadonnées vidéo
    duration = FloatField(required=False)  # en secondes
    fps = IntField(default=25)
    resolution = StringField(required=False)  # "1920x1080"
    file_size = IntField(required=False)  # en bytes

    # Statut du traitement
    status = StringField(
        choices=["uploaded", "processing", "completed", "failed"],
        default="uploaded"
    )

    # Résultats d'analyse (lien vers Analysis)
    analysis_id = StringField(required=False)

    # Dates
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    processed_at = DateTimeField(required=False)

    # Permissions
    is_public = BooleanField(default=False)
    shared_with = ListField(ReferenceField(User))

    meta = {
        "collection": "videos",
        "indexes": ["uploaded_by", "status", "created_at"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "uploaded_by": self.uploaded_by.username,
            "duration": self.duration,
            "fps": self.fps,
            "resolution": self.resolution,
            "file_size": self.file_size,
            "status": self.status,
            "analysis_id": self.analysis_id,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "is_public": self.is_public,
        }
