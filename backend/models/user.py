"""Modèle utilisateur."""

from datetime import datetime
from mongoengine import Document, StringField, EmailField, BooleanField, DateTimeField, ListField


class User(Document):
    """Modèle utilisateur pour authentification et permissions."""

    email = EmailField(unique=True, required=True)
    password = StringField(required=True)  # hashed with bcrypt
    username = StringField(required=True)
    full_name = StringField(required=False)
    role = StringField(choices=["admin", "user"], default="user")
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(required=False)

    # Pour les admins : permissions supplémentaires
    can_manage_users = BooleanField(default=False)
    can_view_all_analyses = BooleanField(default=False)
    can_export_data = BooleanField(default=False)

    meta = {
        "collection": "users",
        "indexes": ["email", "username"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "can_manage_users": self.can_manage_users,
            "can_view_all_analyses": self.can_view_all_analyses,
            "can_export_data": self.can_export_data,
        }
