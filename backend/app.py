"""Application Flask principale."""

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Ajouter le chemin courant au sys.path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Essayer d'importer mongoengine, mais continuer si non disponible
try:
    from mongoengine import connect, disconnect
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False

try:
    from config.config import get_config
except ImportError:
    # Fallback config
    class FallbackConfig:
        DEBUG = True
        SECRET_KEY = 'dev-key'
        MONGO_URI = 'mongodb://localhost:27017/surveillance_db'

    def get_config():
        return FallbackConfig

# Essayer d'importer les routes
try:
    from routes.auth_routes import auth_bp
    from routes.video_routes import video_bp
    from routes.analysis_routes import analysis_bp
    HAS_ROUTES = True
except ImportError:
    HAS_ROUTES = False
    auth_bp = video_bp = analysis_bp = None

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def create_app(config=None):
    """Factory pour créer l'application Flask."""
    app = Flask(__name__)

    # Configuration
    if config is None:
        config = get_config()
    app.config.from_object(config)

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # MongoDB
    try:
        disconnect()  # Déconnecter les connexions précédentes
        connect(
            host=app.config['MONGO_URI'],
            retryWrites=False
        )
        log.info("✓ MongoDB connecté")
    except Exception as e:
        log.error(f"✗ Erreur connexion MongoDB: {e}")
        raise

    # Créer les dossiers uploads et exports
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORTS_FOLDER'], exist_ok=True)

    # Enregistrer les blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(analysis_bp)

    # Routes de base
    @app.route('/api/health', methods=['GET'])
    def health():
        """Vérifie la santé de l'application."""
        return jsonify({
            'status': 'healthy',
            'service': 'Surveillance Platform API',
            'version': '1.0.0'
        }), 200

    @app.route('/api', methods=['GET'])
    def api_info():
        """Informations sur l'API."""
        return jsonify({
            'name': 'Surveillance Platform API',
            'version': '1.0.0',
            'description': 'API pour système de surveillance intelligent multi-agents',
            'endpoints': {
                'auth': '/api/auth',
                'videos': '/api/videos',
                'analyses': '/api/analyses',
            }
        }), 200

    # Gestion des erreurs
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(error):
        log.error(f"Server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Access forbidden'}), 403

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
