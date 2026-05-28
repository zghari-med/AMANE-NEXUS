#!/usr/bin/env python
"""Test de l'application Flask"""

import sys
import os

# Ajouter le chemin backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    print("[TEST] Chargement de l'application Flask...")

    # Test imports
    from flask import Flask
    print("  OK: Flask importé")

    from flask_cors import CORS
    print("  OK: Flask-CORS importé")

    # Test configuration
    from backend.config.config import DevelopmentConfig
    print("  OK: Configuration chargée")

    # Test si MongoDB est accessible
    try:
        import mongoengine
        print("  OK: mongoengine disponible")
    except Exception as e:
        print(f"  WARNING: mongoengine - {e}")

    # Test si Redis est accessible
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("  OK: Redis connecté")
    except Exception as e:
        print(f"  WARNING: Redis - {e}")

    # Test app creation
    from backend.app import create_app
    print("\n[TEST] Création de l'application...")
    app = create_app(DevelopmentConfig)
    print("  OK: Application créée")

    # Afficher les routes
    print("\n[ROUTES API DISPONIBLES]")
    api_routes = []
    for rule in app.url_map.iter_rules():
        if 'api' in str(rule):
            methods = ','.join(rule.methods - {'OPTIONS', 'HEAD'})
            api_routes.append(f"  {rule.rule} [{methods}]")

    for route in sorted(api_routes):
        print(route)

    print(f"\nTotal: {len(api_routes)} endpoints API")

    print("\n[SUCCESS] Application prête pour le test!")
    print("\nCommandes pour demarrer:")
    print("  1. Terminal: python agents/agent_perception.py")
    print("  2. Terminal: python agents/agent_tracking.py")
    print("  3. Terminal: python agents/agent_analysis.py")
    print("  4. Terminal: python agents/agent_decision.py")
    print("  5. Terminal: python app.py")
    print("  6. Terminal: cd frontend && npm run dev")

except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
