"""Configuration de l'application."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration de base."""

    SECRET_KEY = os.getenv('SECRET_KEY', 'pfe_surveillance_2026')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION = 86400  # 24 heures

    # MongoDB
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/surveillance_db')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

    # Upload
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
    UPLOAD_FOLDER = 'backend/uploads'
    EXPORTS_FOLDER = 'backend/exports'

    # Agents
    AGENT_PERCEPTION_ENABLED = True
    AGENT_TRACKING_ENABLED = True
    AGENT_ANALYSIS_ENABLED = True
    AGENT_DECISION_ENABLED = True


class DevelopmentConfig(Config):
    """Configuration développement."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configuration production."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Configuration tests."""
    DEBUG = True
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/surveillance_test_db'


def get_config():
    """Retourne la configuration appropriée."""
    env = os.getenv('FLASK_ENV', 'development')

    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()
