"""
=============================================================
TEST SUITE - API REST (endpoints Flask)
=============================================================
Tests d'integration des endpoints avec une vraie instance Flask
et une base MongoDB separee (test).
=============================================================
"""
import unittest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test_secret_key_2026')
os.environ.setdefault('MONGO_DB', 'surveillance_test_db')

from app_simple import app, db  # noqa: E402,F401


def get_token(client, email='test_api@test.com', password='testpass123'):
    """Helper : login et retourne le token JWT."""
    r = client.post('/api/auth/login',
                    data=json.dumps({'email': email, 'password': password}),
                    content_type='application/json')
    if r.status_code == 200:
        return json.loads(r.data)['token']
    return None


def auth_header(token):
    return {'Authorization': f'Bearer {token}'}


class TestAPIBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Creer un utilisateur de test dans la DB de test."""
        app.config['TESTING'] = True
        cls.client = app.test_client()

        # Nettoyage prealable
        db.user.delete_many({'email': {'$in': [
            'test_api@test.com', 'test_admin@test.com'
        ]}})

        import bcrypt
        hashed = bcrypt.hashpw(b'testpass123', bcrypt.gensalt(10))
        from datetime import datetime
        db.user.insert_one({
            'email':    'test_api@test.com',
            'username': 'test_api_user',
            'password': hashed,
            'role':     'user',
            'full_name': 'Test API User',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        })
        db.user.insert_one({
            'email':    'test_admin@test.com',
            'username': 'test_api_admin',
            'password': bcrypt.hashpw(b'testpass123', bcrypt.gensalt(10)),
            'role':     'admin',
            'full_name': 'Test Admin',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        })

    @classmethod
    def tearDownClass(cls):
        """Nettoyer les donnees de test."""
        db.user.delete_many({'email': {'$in': [
            'test_api@test.com', 'test_admin@test.com'
        ]}})
        db.camera.delete_many({'name': {'$regex': '^TEST_'}})


# ══════════════════════════════════════════════════════════════
#  AUTHENTIFICATION
# ══════════════════════════════════════════════════════════════
class TestAuthentication(TestAPIBase):

    def test_health_endpoint(self):
        """GET /api/health -> 200 healthy."""
        r = self.client.get('/api/health')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['status'], 'healthy')

    def test_login_success(self):
        """POST /api/auth/login avec bons identifiants -> 200 + token."""
        r = self.client.post('/api/auth/login',
                             data=json.dumps({'email': 'test_api@test.com',
                                              'password': 'testpass123'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'test_api@test.com')

    def test_login_mauvais_password(self):
        """POST /api/auth/login avec mauvais mot de passe -> 401."""
        r = self.client.post('/api/auth/login',
                             data=json.dumps({'email': 'test_api@test.com',
                                              'password': 'wrong'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_login_email_inexistant(self):
        """POST /api/auth/login email inconnu -> 401."""
        r = self.client.post('/api/auth/login',
                             data=json.dumps({'email': 'nobody@test.com',
                                              'password': 'any'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_login_champs_manquants(self):
        """POST /api/auth/login sans password -> 400."""
        r = self.client.post('/api/auth/login',
                             data=json.dumps({'email': 'test_api@test.com'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_endpoint_protege_sans_token(self):
        """GET /api/cameras sans token -> 401."""
        r = self.client.get('/api/cameras')
        self.assertEqual(r.status_code, 401)

    def test_endpoint_protege_token_invalide(self):
        """GET /api/cameras avec token bidon -> 401."""
        r = self.client.get('/api/cameras',
                            headers={'Authorization': 'Bearer faketoken.123.xyz'})
        self.assertEqual(r.status_code, 401)

    def test_logout_enregistre_activite(self):
        """POST /api/auth/logout -> 200 et enregistre dans activity_log."""
        token = get_token(self.client)
        self.assertIsNotNone(token)
        r = self.client.post('/api/auth/logout', headers=auth_header(token))
        self.assertEqual(r.status_code, 200)
        log = db.activity_log.find_one({'action': 'LOGOUT', 'username': 'test_api_user'})
        self.assertIsNotNone(log, "Logout doit etre enregistre dans activity_log")

    def test_me_endpoint(self):
        """GET /api/auth/me avec token valide -> 200 + user info."""
        token = get_token(self.client)
        r = self.client.get('/api/auth/me', headers=auth_header(token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertEqual(data['user']['email'], 'test_api@test.com')


# ══════════════════════════════════════════════════════════════
#  CAMERAS
# ══════════════════════════════════════════════════════════════
class TestCameras(TestAPIBase):

    def setUp(self):
        self.token = get_token(self.client)

    def test_get_cameras_authentifie(self):
        """GET /api/cameras authentifie -> 200 + liste cameras."""
        r = self.client.get('/api/cameras', headers=auth_header(self.token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('cameras', data)
        self.assertIsInstance(data['cameras'], list)

    def test_get_cameras_aucun_objectid(self):
        """GET /api/cameras -> aucun champ ObjectId non serialisable."""
        r = self.client.get('/api/cameras', headers=auth_header(self.token))
        data = json.loads(r.data)
        for cam in data.get('cameras', []):
            self.assertNotIn('created_by', cam, "created_by ObjectId ne doit pas etre expose")
            self.assertIsInstance(cam['_id'], str, "_id doit etre un string")

    def test_creer_camera(self):
        """POST /api/cameras -> 201 + objet camera retourne."""
        payload = {'name': 'TEST_Camera_Unitaire', 'url': 'http://192.168.1.10:8080/stream',
                   'location': 'Salle B', 'type': 'http'}
        r = self.client.post('/api/cameras', headers=auth_header(self.token),
                             data=json.dumps(payload), content_type='application/json')
        self.assertEqual(r.status_code, 201)
        data = json.loads(r.data)
        self.assertIn('camera', data)
        self.assertEqual(data['camera']['name'], 'TEST_Camera_Unitaire')
        self.assertNotIn('created_by', data['camera'])

    def test_creer_camera_champs_manquants(self):
        """POST /api/cameras sans URL -> 400."""
        r = self.client.post('/api/cameras', headers=auth_header(self.token),
                             data=json.dumps({'name': 'TEST_Sans_URL'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_supprimer_camera(self):
        """DELETE /api/cameras/<id> -> 200."""
        payload = {'name': 'TEST_Camera_A_Supprimer', 'url': 'http://del.test/stream'}
        r = self.client.post('/api/cameras', headers=auth_header(self.token),
                             data=json.dumps(payload), content_type='application/json')
        cam_id = json.loads(r.data)['camera']['_id']
        rd = self.client.delete(f'/api/cameras/{cam_id}', headers=auth_header(self.token))
        self.assertEqual(rd.status_code, 200)


# ══════════════════════════════════════════════════════════════
#  STATISTIQUES
# ══════════════════════════════════════════════════════════════
class TestStatistics(TestAPIBase):

    def setUp(self):
        self.token = get_token(self.client)

    def test_statistiques_retourne_champs_requis(self):
        """GET /api/analyses/statistics -> champs obligatoires presents."""
        r = self.client.get('/api/analyses/statistics', headers=auth_header(self.token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        for field in ['total_alerts', 'total_videos', 'total_analyses',
                      'falls_detected', 'crowds_detected', 'abandoned_objects',
                      'recent_alerts', 'chart_data', 'alerts_by_type']:
            self.assertIn(field, data, f"Champ manquant: {field}")

    def test_statistiques_avec_filtre_jours(self):
        """GET /api/analyses/statistics?days=7 -> 200."""
        r = self.client.get('/api/analyses/statistics?days=7',
                            headers=auth_header(self.token))
        self.assertEqual(r.status_code, 200)

    def test_statistiques_recent_alerts_max_4(self):
        """recent_alerts contient au plus 4 alertes."""
        r = self.client.get('/api/analyses/statistics', headers=auth_header(self.token))
        data = json.loads(r.data)
        self.assertLessEqual(len(data['recent_alerts']), 4)

    def test_admin_voit_total_users(self):
        """Admin voit total_users; user normal ne le voit pas."""
        admin_token = get_token(self.client, 'test_admin@test.com')
        r = self.client.get('/api/analyses/statistics', headers=auth_header(admin_token))
        data = json.loads(r.data)
        self.assertIn('total_users', data)

        user_token = get_token(self.client)
        r2 = self.client.get('/api/analyses/statistics', headers=auth_header(user_token))
        data2 = json.loads(r2.data)
        self.assertNotIn('total_users', data2)


# ══════════════════════════════════════════════════════════════
#  ACCES ADMIN
# ══════════════════════════════════════════════════════════════
class TestAdminAccess(TestAPIBase):

    def test_user_normal_ne_peut_pas_lister_users(self):
        """User normal -> GET /api/users -> 403."""
        token = get_token(self.client)
        r = self.client.get('/api/users', headers=auth_header(token))
        self.assertEqual(r.status_code, 403)

    def test_admin_peut_lister_users(self):
        """Admin -> GET /api/users -> 200."""
        token = get_token(self.client, 'test_admin@test.com')
        r = self.client.get('/api/users', headers=auth_header(token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('users', data)

    def test_user_normal_ne_peut_pas_creer_user(self):
        """User normal -> POST /api/users -> 403."""
        token = get_token(self.client)
        r = self.client.post('/api/users', headers=auth_header(token),
                             data=json.dumps({'email': 'hack@test.com',
                                              'username': 'hacker',
                                              'password': 'pass123'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_benchmarks_requiert_auth(self):
        """GET /api/analyses/benchmarks sans token -> 401."""
        r = self.client.get('/api/analyses/benchmarks')
        self.assertEqual(r.status_code, 401)

    def test_captures_requiert_auth(self):
        """GET /api/captures/test.jpg sans token -> 401."""
        r = self.client.get('/api/captures/test.jpg')
        self.assertEqual(r.status_code, 401)


# ══════════════════════════════════════════════════════════════
#  VIDEOS
# ══════════════════════════════════════════════════════════════
class TestVideos(TestAPIBase):

    def setUp(self):
        self.token = get_token(self.client)

    def test_get_videos_vide_ou_liste(self):
        """GET /api/videos -> 200 + liste."""
        r = self.client.get('/api/videos', headers=auth_header(self.token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('videos', data)
        self.assertIsInstance(data['videos'], list)

    def test_upload_sans_fichier(self):
        """POST /api/videos/upload sans fichier -> 400."""
        r = self.client.post('/api/videos/upload', headers=auth_header(self.token))
        self.assertEqual(r.status_code, 400)

    def test_delete_video_inexistante(self):
        """DELETE /api/videos/000000000000000000000000 -> 404."""
        r = self.client.delete('/api/videos/000000000000000000000000',
                               headers=auth_header(self.token))
        self.assertEqual(r.status_code, 404)

    def test_activity_log_accessible(self):
        """GET /api/activity-logs -> 200."""
        r = self.client.get('/api/activity-logs', headers=auth_header(self.token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('logs', data)
        self.assertIn('total', data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
