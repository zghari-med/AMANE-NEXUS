"""Service d'authentification."""

import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from ..models.user import User


class AuthService:
    """Service de gestion de l'authentification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe avec bcrypt."""
        salt = bcrypt.gensalt(rounds=10)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Vérifie un mot de passe."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def generate_token(user: User, expires_in: int = 86400) -> str:
        """Génère un JWT token."""
        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
        }
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token

    @staticmethod
    def verify_token(token: str) -> dict | None:
        """Vérifie et décode un JWT token."""
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def register_user(email: str, password: str, username: str, full_name: str = "") -> dict:
        """Enregistre un nouvel utilisateur."""
        # Vérifier que l'email n'existe pas
        if User.objects(email=email):
            return {"error": "Email already exists", "code": 400}

        if User.objects(username=username):
            return {"error": "Username already exists", "code": 400}

        # Créer l'utilisateur
        hashed_password = AuthService.hash_password(password)
        user = User(
            email=email,
            password=hashed_password,
            username=username,
            full_name=full_name,
            role="user"
        )
        user.save()

        return {"user": user.to_dict(), "code": 201}

    @staticmethod
    def login_user(email: str, password: str) -> dict:
        """Authentifie un utilisateur."""
        user = User.objects(email=email).first()

        if not user:
            return {"error": "Invalid credentials", "code": 401}

        if not AuthService.verify_password(password, user.password):
            return {"error": "Invalid credentials", "code": 401}

        # Mettre à jour le dernier login
        user.last_login = datetime.utcnow()
        user.save()

        # Générer le token
        token = AuthService.generate_token(user)

        return {
            "user": user.to_dict(),
            "token": token,
            "code": 200
        }

    @staticmethod
    def get_user_by_id(user_id: str) -> User | None:
        """Récupère un utilisateur par son ID."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


def token_required(f):
    """Décorateur pour protéger les routes avec JWT."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Chercher le token dans le header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        # Vérifier le token
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Récupérer l'utilisateur
        user = AuthService.get_user_by_id(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Passer l'utilisateur à la fonction
        request.user = user
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'user') or request.user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)

    return decorated_function
