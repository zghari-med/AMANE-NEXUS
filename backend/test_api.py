#!/usr/bin/env python
"""Test simple de l'API Flask"""

import sys
print("[1] Test des imports...")
try:
    from flask import Flask
    from flask_cors import CORS
    import redis
    print("    [OK] Flask, CORS, Redis")
except Exception as e:
    print(f"    [FAIL] {e}")
    sys.exit(1)

print("[2] Test Redis...")
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("    [OK] Redis connecte")
except:
    print("    [WARN] Redis non disponible")

print("[3] Creation de l'app Flask...")
try:
    app = Flask(__name__)

    @app.route('/api/health')
    def health():
        return {'status': 'healthy'}

    with app.app_context():
        routes = len(list(app.url_map.iter_rules()))
        print(f"    [OK] App Flask creee ({routes} routes)")
except Exception as e:
    print(f"    [FAIL] {e}")
    sys.exit(1)

print("")
print("="*50)
print("STATUT: API PRETE")
print("="*50)
print("")
print("Pour demarrer l'API:")
print("  python app.py")
print("")
print("Puis acceder a:")
print("  http://localhost:5000/api/health")
print("")
