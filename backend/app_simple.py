#!/usr/bin/env python
"""Application Flask simple - Démarrage rapide"""

import os
import logging
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
import cv2
import sys
import os as _os
from werkzeug.utils import secure_filename

# Worker analyse réel
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    from worker_analysis import start_analysis_thread
    HAS_WORKER = True
except ImportError:
    HAS_WORKER = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [API] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pfe_surveillance_2026'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
CORS(app)

# MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['surveillance_db']

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm'}

# Decorateur pour JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Accept token from Authorization header OR query string (for <video> src)
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.args.get('token', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
            request.user_role = data['role']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'Surveillance Platform API', 'version': '1.0.0'}), 200

@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({'name': 'Surveillance Platform API', 'version': '1.0.0'}), 200

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    user = db.user.find_one({'email': email})
    if not user or not bcrypt.checkpw(password.encode(), user['password']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

    token = jwt.encode({
        'user_id': str(user['_id']),
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({
        'token': token,
        'user': {
            'id': str(user['_id']),
            'email': user['email'],
            'username': user['username'],
            'role': user['role']
        }
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_me():
    user = db.user.find_one({'_id': ObjectId(request.user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': {'email': user['email'], 'username': user['username'], 'role': user['role']}}), 200

# VIDEO ENDPOINTS
@app.route('/api/videos/upload', methods=['POST'])
@token_required
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    title = request.form.get('title', file.filename)

    if not file.filename or '.' not in file.filename:
        return jsonify({'error': 'Invalid file'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'File type not allowed. Allowed: {ALLOWED_EXTENSIONS}'}), 400

    filename = secure_filename(f"{ObjectId()}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Extract video metadata
    try:
        cap = cv2.VideoCapture(filepath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
    except:
        duration = 0
        fps = 30
        width = 0
        height = 0

    # Save to DB
    video_doc = {
        'title': title,
        'filename': filename,
        'filepath': filepath,
        'uploaded_by': ObjectId(request.user_id),
        'status': 'uploaded',
        'duration': duration,
        'fps': fps,
        'resolution': f"{width}x{height}",
        'file_size': os.path.getsize(filepath),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    result = db.video.insert_one(video_doc)

    return jsonify({
        'message': 'Video uploaded successfully',
        'video': {
            '_id': str(result.inserted_id),
            'title': title,
            'duration': duration
        }
    }), 201

@app.route('/api/videos', methods=['GET'])
@token_required
def get_videos():
    user_id = ObjectId(request.user_id)
    videos = list(db.video.find({'uploaded_by': user_id}).sort('created_at', -1))

    return jsonify({
        'videos': [{
            '_id': str(v['_id']),
            'title': v['title'],
            'duration': v.get('duration', 0),
            'status': v.get('status', 'unknown'),
            'created_at': v.get('created_at')
        } for v in videos]
    }), 200

@app.route('/api/videos/<video_id>', methods=['DELETE'])
@token_required
def delete_video(video_id):
    try:
        vid = db.video.find_one({'_id': ObjectId(video_id)})
        if not vid:
            return jsonify({'error': 'Video not found'}), 404

        if str(vid['uploaded_by']) != request.user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        if os.path.exists(vid['filepath']):
            os.remove(vid['filepath'])

        db.video.delete_one({'_id': ObjectId(video_id)})
        return jsonify({'message': 'Video deleted'}), 200
    except:
        return jsonify({'error': 'Error deleting video'}), 500

# ANALYSIS ENDPOINTS
@app.route('/api/analyses/create', methods=['POST'])
@token_required
def create_analysis():
    data = request.json
    video_id = data.get('video_id')

    if not video_id:
        return jsonify({'error': 'video_id required'}), 400

    try:
        vid = db.video.find_one({'_id': ObjectId(video_id)})
        if not vid:
            return jsonify({'error': 'Video not found'}), 404

        # Check if analysis already exists
        existing = db.analysis.find_one({
            'video': ObjectId(video_id),
            'status': {'$in': ['pending', 'processing']}
        })
        if existing:
            return jsonify({'error': 'Analysis already in progress'}), 400

        analysis_doc = {
            'video': ObjectId(video_id),
            'user': ObjectId(request.user_id),
            'status': 'pending',
            'total_events': 0,
            'falls_detected': 0,
            'crowds_detected': 0,
            'abandoned_objects': 0,
            'events_timeline': [],
            'processing_time': 0,
            'average_fps': 0,
            'cpu_usage': 0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = db.analysis.insert_one(analysis_doc)
        analysis_id = str(result.inserted_id)

        # Lancer le worker d'analyse réel dans un thread
        if HAS_WORKER and os.path.exists(vid['filepath']):
            start_analysis_thread(analysis_id, vid['filepath'])
        else:
            log.warning('Worker non disponible ou fichier introuvable')

        return jsonify({
            'message': 'Analysis created',
            'analysis_id': analysis_id
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses', methods=['GET'])
@token_required
def get_analyses():
    user_id = ObjectId(request.user_id)
    analyses = list(db.analysis.find({'user': user_id}).sort('created_at', -1))

    return jsonify({
        'analyses': [{
            '_id': str(a['_id']),
            'status': a.get('status', 'unknown'),
            'total_events': a.get('total_events', 0),
            'falls_detected': a.get('falls_detected', 0),
            'crowds_detected': a.get('crowds_detected', 0),
            'abandoned_objects': a.get('abandoned_objects', 0),
            'created_at': a.get('created_at')
        } for a in analyses]
    }), 200

@app.route('/api/analyses/statistics', methods=['GET'])
@token_required
def get_statistics():
    is_admin = request.user_role == 'admin'
    uid = ObjectId(request.user_id)
    query = {} if is_admin else {'user': uid}
    analyses = list(db.analysis.find(query).sort('created_at', -1))

    completed = [a for a in analyses if a.get('status') == 'completed']
    total_falls     = sum(a.get('falls_detected', 0) for a in completed)
    total_crowds    = sum(a.get('crowds_detected', 0) for a in completed)
    total_abandoned = sum(a.get('abandoned_objects', 0) for a in completed)

    analysis_ids = [a['_id'] for a in analyses]
    alert_query  = {} if is_admin else {'analysis': {'$in': analysis_ids}}
    total_alerts = db.alert.count_documents(alert_query)

    # Breakdown by type
    falls_alerts     = db.alert.count_documents({**alert_query, 'event_type': 'fall'})
    crowding_alerts  = db.alert.count_documents({**alert_query, 'event_type': 'crowding'})
    abandoned_alerts = db.alert.count_documents({**alert_query, 'event_type': 'abandoned'})

    # Total videos
    video_query = {} if is_admin else {'uploaded_by': uid}
    total_videos = db.video.count_documents(video_query)

    # Total users (admin only)
    total_users = db.user.count_documents({}) if is_admin else None

    # Recent alerts (last 8)
    recent_raw = list(db.alert.find(alert_query).sort('created_at', -1).limit(8))
    recent_alerts = []
    for al in recent_raw:
        a_doc = db.analysis.find_one({'_id': al.get('analysis')})
        v_doc = db.video.find_one({'_id': a_doc.get('video')}) if a_doc else None
        recent_alerts.append({
            '_id':        str(al['_id']),
            'event_type': al.get('event_type', ''),
            'risk_level': al.get('risk_level', 'low'),
            'timestamp':  al.get('timestamp', 0),
            'frame_id':   al.get('frame_id', 0),
            'capture':    al.get('capture'),
            'video_title': v_doc['title'] if v_doc else 'Inconnu',
            'created_at': str(al.get('created_at', '')),
        })

    # Per-analysis chart data (last 10)
    chart_data = []
    for a in completed[:10][::-1]:
        vid = db.video.find_one({'_id': a.get('video')})
        chart_data.append({
            'name':          (vid['title'] if vid else 'Vidéo')[:10],
            'chutes':        a.get('falls_detected', 0),
            'attroupements': a.get('crowds_detected', 0),
            'objets':        a.get('abandoned_objects', 0),
        })

    result = {
        'falls_detected':     total_falls,
        'crowds_detected':    total_crowds,
        'abandoned_objects':  total_abandoned,
        'total_events':       total_falls + total_crowds + total_abandoned,
        'total_analyses':     len(analyses),
        'completed_analyses': len(completed),
        'total_alerts':       total_alerts,
        'total_videos':       total_videos,
        'alerts_by_type': {
            'fall':      falls_alerts,
            'crowding':  crowding_alerts,
            'abandoned': abandoned_alerts,
        },
        'recent_alerts': recent_alerts,
        'chart_data':    chart_data,
    }
    if is_admin:
        result['total_users'] = total_users
    return jsonify(result), 200

# USER MANAGEMENT (admin only)
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.args.get('token', '')
        if not token:
            return jsonify({'error': 'Missing token'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            if data.get('role') != 'admin':
                return jsonify({'error': 'Admin only'}), 403
            request.user_id = data['user_id']
            request.user_role = 'admin'
        except:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    users = list(db.user.find({}).sort('created_at', -1))
    return jsonify({'users': [{
        '_id': str(u['_id']),
        'username': u.get('username', ''),
        'email': u.get('email', ''),
        'role': u.get('role', 'user'),
        'full_name': u.get('full_name', ''),
        'created_at': str(u.get('created_at', '')),
    } for u in users]}), 200

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.json
    email    = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role     = data.get('role', 'user')
    full_name = data.get('full_name', '')

    if not email or not username or not password:
        return jsonify({'error': 'email, username et password sont requis'}), 400
    if role not in ('admin', 'user'):
        return jsonify({'error': 'Rôle invalide (admin ou user)'}), 400
    if db.user.find_one({'email': email}):
        return jsonify({'error': 'Email déjà utilisé'}), 409
    if db.user.find_one({'username': username}):
        return jsonify({'error': "Nom d'utilisateur déjà pris"}), 409

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10))
    result = db.user.insert_one({
        'email': email,
        'username': username,
        'password': hashed,
        'full_name': full_name,
        'role': role,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    })
    return jsonify({'message': 'Utilisateur créé', 'user_id': str(result.inserted_id)}), 201

@app.route('/api/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == request.user_id:
        return jsonify({'error': 'Impossible de supprimer votre propre compte'}), 400
    r = db.user.delete_one({'_id': ObjectId(user_id)})
    if r.deleted_count == 0:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    return jsonify({'message': 'Utilisateur supprimé'}), 200

@app.route('/api/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    data = request.json
    upd = {}
    if 'role' in data and data['role'] in ('admin', 'user'):
        upd['role'] = data['role']
    if 'full_name' in data:
        upd['full_name'] = data['full_name']
    if not upd:
        return jsonify({'error': 'Rien à mettre à jour'}), 400
    db.user.update_one({'_id': ObjectId(user_id)}, {'$set': upd})
    return jsonify({'message': 'Utilisateur mis à jour'}), 200

@app.route('/api/captures/<filename>', methods=['GET'])
def serve_capture(filename):
    captures_dir = os.path.join(BASE_DIR, 'captures')
    path = os.path.join(captures_dir, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Capture not found'}), 404
    return send_file(path, mimetype='image/jpeg')

@app.route('/api/videos/<video_id>/file', methods=['GET'])
@token_required
def serve_video(video_id):
    try:
        vid = db.video.find_one({'_id': ObjectId(video_id)})
        if not vid:
            return jsonify({'error': 'Video not found'}), 404
        if not os.path.exists(vid['filepath']):
            return jsonify({'error': 'File not found on disk'}), 404
        return send_file(vid['filepath'], mimetype='video/mp4', conditional=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses/<analysis_id>', methods=['GET'])
@token_required
def get_analysis(analysis_id):
    try:
        a = db.analysis.find_one({'_id': ObjectId(analysis_id)})
        if not a:
            return jsonify({'error': 'Analysis not found'}), 404
        vid = db.video.find_one({'_id': a.get('video')})
        return jsonify({'analysis': {
            '_id': str(a['_id']),
            'status': a.get('status', 'unknown'),
            'progress': a.get('progress', 0),
            'total_events': a.get('total_events', 0),
            'falls_detected': a.get('falls_detected', 0),
            'crowds_detected': a.get('crowds_detected', 0),
            'abandoned_objects': a.get('abandoned_objects', 0),
            'processing_time': a.get('processing_time', 0),
            'average_fps': a.get('average_fps', 0),
            'video_id': str(a['video']) if a.get('video') else None,
            'video_title': vid['title'] if vid else 'Unknown',
            'created_at': a.get('created_at')
        }}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyses/<analysis_id>/alerts', methods=['GET'])
@token_required
def get_analysis_alerts(analysis_id):
    try:
        alerts = list(db.alert.find({'analysis': ObjectId(analysis_id)}).sort('created_at', -1))
        return jsonify({'alerts': [{
            '_id': str(al['_id']),
            'event_type': al.get('event_type', ''),
            'risk_level': al.get('risk_level', 'low'),
            'frame_id': al.get('frame_id', 0),
            'timestamp': al.get('timestamp', 0),
            'status': al.get('status', 'active'),
            'capture': al.get('capture'),
            'created_at': str(al.get('created_at', ''))
        } for al in alerts]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Analytics & Benchmarks routes ─────────────────────────────────────────

@app.route('/api/analyses/statistics/<analysis_id>', methods=['GET'])
@token_required
def get_analysis_statistics(analysis_id):
    """Stats Pandas détaillées pour une analyse spécifique."""
    try:
        import sys as _sys
        _sys.path.insert(0, BASE_DIR)
        from services.analytics_service import get_analysis_statistics
        result = get_analysis_statistics(analysis_id)
        return jsonify(result), 200
    except Exception as e:
        log.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses/benchmarks', methods=['GET'])
def get_benchmarks():
    """Retourne benchmark_results.json (données scientifiques YOLO)."""
    try:
        import sys as _sys
        _sys.path.insert(0, BASE_DIR)
        from services.analytics_service import get_benchmarks
        return jsonify(get_benchmarks()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses/<analysis_id>/trends', methods=['GET'])
@token_required
def get_trends(analysis_id):
    """Tendances hebdomadaires des alertes de l'utilisateur courant."""
    try:
        import sys as _sys
        _sys.path.insert(0, BASE_DIR)
        from services.analytics_service import generate_trend_analysis
        weeks = int(request.args.get('weeks', 8))
        result = generate_trend_analysis(weeks=weeks, user_id=request.user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses/<analysis_id>/metrics-export', methods=['GET'])
@token_required
def metrics_export(analysis_id):
    """Exporte les alertes d'une analyse en CSV."""
    try:
        import sys as _sys
        _sys.path.insert(0, BASE_DIR)
        from services.analytics_service import export_metrics_csv
        csv_content = export_metrics_csv(analysis_id)
        from flask import Response
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=analyse_{analysis_id}.csv'}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    log.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    log.info("Demarrage de l'API Flask...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
