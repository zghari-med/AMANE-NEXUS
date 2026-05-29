#!/usr/bin/env python
"""Application Flask simple - Démarrage rapide"""

import os
import logging
import jwt
import threading
import time
import subprocess
import re
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

# Charger les variables d'environnement depuis .env si python-dotenv est disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optionnel — les variables système restent disponibles

# Worker analyse réel
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    from worker_analysis import start_analysis_thread
    HAS_WORKER = True
except ImportError:
    HAS_WORKER = False

# Suivi des analyses en direct (cam_id -> dict)
live_analyses = {}  # {cam_id: {'running': bool, 'analysis_id': str, 'thread': Thread}}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [API] %(levelname)s — %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pfe_surveillance_2026_change_in_production')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
CORS(app)

# MongoDB
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB  = os.environ.get('MONGO_DB',  'surveillance_db')
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

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
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# ── Activity Log ──────────────────────────────────────────────────────────────
def log_activity(action, details='', user_id=None, username='system', status='success'):
    """Enregistre une activité dans la collection activity_log."""
    try:
        db.activity_log.insert_one({
            'user_id':   ObjectId(user_id) if user_id else None,
            'username':  username,
            'action':    action,
            'details':   details,
            'ip':        request.remote_addr if request else '—',
            'method':    request.method if request else '—',
            'endpoint':  request.path if request else '—',
            'status':    status,
            'created_at': datetime.utcnow(),
        })
    except Exception as e:
        log.warning(f"log_activity failed: {e}")

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

    log_activity('LOGIN', f"Connexion réussie depuis {request.remote_addr}",
                 user_id=str(user['_id']), username=user['username'])
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

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    user = db.user.find_one({'_id': ObjectId(request.user_id)})
    username = user.get('username') if user else 'unknown'
    log_activity('LOGOUT', f"Déconnexion réussie depuis {request.remote_addr}",
                 user_id=str(request.user_id), username=username)
    return jsonify({'message': 'Déconnexion réussie'}), 200

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
    except Exception as e:
        log.warning(f"Impossible d'extraire les métadonnées vidéo: {e}")
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
    u = db.user.find_one({'_id': ObjectId(request.user_id)})
    log_activity('UPLOAD_VIDEO', f"Vidéo uploadée: {title} ({duration:.1f}s)", request.user_id, u.get('username','?') if u else '?')

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
    # Tous les utilisateurs voient toutes les vidéos
    videos = list(db.video.find({}).sort('created_at', -1))

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

        if request.user_role != 'admin' and str(vid['uploaded_by']) != request.user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        if os.path.exists(vid['filepath']):
            os.remove(vid['filepath'])

        db.video.delete_one({'_id': ObjectId(video_id)})
        u = db.user.find_one({'_id': ObjectId(request.user_id)})
        log_activity('DELETE_VIDEO', f"Vidéo supprimée: {vid.get('title','')}", request.user_id, u.get('username','?') if u else '?')
        return jsonify({'message': 'Video deleted'}), 200
    except Exception as e:
        log.error(f"delete_video error: {e}")
        return jsonify({'error': 'Erreur lors de la suppression de la vidéo'}), 500

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

        u = db.user.find_one({'_id': ObjectId(request.user_id)})
        log_activity('CREATE_ANALYSIS', f"Analyse lancée sur: {vid.get('title','')}", request.user_id, u.get('username','?') if u else '?')
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
    # Optional date filter: ?days=7|30|90 (default: all time)
    days_param = request.args.get('days')
    date_filter = {}
    if days_param and days_param.isdigit():
        cutoff = datetime.utcnow() - timedelta(days=int(days_param))
        date_filter = {'created_at': {'$gte': cutoff}}
    # EVERYONE sees the SAME data — no user filtering
    analyses = list(db.analysis.find(date_filter).sort('created_at', -1))

    completed = [a for a in analyses if a.get('status') == 'completed']
    total_falls     = sum(a.get('falls_detected', 0) for a in completed)
    total_crowds    = sum(a.get('crowds_detected', 0) for a in completed)
    total_abandoned = sum(a.get('abandoned_objects', 0) for a in completed)

    # EVERYONE sees ALL alerts (filtered by date if requested)
    total_alerts = db.alert.count_documents(date_filter if date_filter else {})

    # Breakdown by type
    base_q = dict(date_filter) if date_filter else {}
    falls_alerts     = db.alert.count_documents({**base_q, 'event_type': 'fall'})
    crowding_alerts  = db.alert.count_documents({**base_q, 'event_type': 'crowding'})
    abandoned_alerts = db.alert.count_documents({**base_q, 'event_type': 'abandoned'})

    # EVERYONE sees ALL videos
    total_videos = db.video.count_documents({})

    # Total users (admin only)
    total_users = db.user.count_documents({}) if is_admin else None

    # Recent alerts (last 4) — everyone sees all
    recent_raw = list(db.alert.find({}).sort('created_at', -1).limit(4))
    recent_alerts = []
    for al in recent_raw:
        analysis_ref = al.get('analysis')
        a_doc = db.analysis.find_one({'_id': analysis_ref}) if analysis_ref else None
        v_doc = db.video.find_one({'_id': a_doc.get('video')}) if a_doc and a_doc.get('video') else None
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

    # Chart data — grouped by date (no duplicate dates)
    from collections import OrderedDict
    from datetime import datetime as _dt
    date_map = OrderedDict()
    for a in reversed(completed):
        ts = a.get('completed_at') or a.get('updated_at') or a.get('created_at')
        if ts and hasattr(ts, 'strftime'):
            label = ts.strftime('%d/%m/%Y')
        elif ts and isinstance(ts, str):
            try:
                label = _dt.fromisoformat(ts.replace('Z', '')).strftime('%d/%m/%Y')
            except Exception:
                continue
        else:
            continue
        if label not in date_map:
            date_map[label] = {'chutes': 0, 'attroupements': 0, 'objets': 0}
        date_map[label]['chutes']        += a.get('falls_detected', 0)
        date_map[label]['attroupements'] += a.get('crowds_detected', 0)
        date_map[label]['objets']        += a.get('abandoned_objects', 0)
    # Keep last 14 days
    chart_data = [
        {'name': d, **v}
        for d, v in list(date_map.items())[-14:]
    ]

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
        except Exception:
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
    admin_u = db.user.find_one({'_id': ObjectId(request.user_id)})
    log_activity('CREATE_USER', f"Nouvel utilisateur: {username} ({role})", request.user_id, admin_u.get('username','?') if admin_u else '?')
    return jsonify({'message': 'Utilisateur créé', 'user_id': str(result.inserted_id)}), 201

@app.route('/api/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == request.user_id:
        return jsonify({'error': 'Impossible de supprimer votre propre compte'}), 400
    r = db.user.delete_one({'_id': ObjectId(user_id)})
    if r.deleted_count == 0:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    admin_u = db.user.find_one({'_id': ObjectId(request.user_id)})
    log_activity('DELETE_USER', f"Utilisateur supprimé: {user_id}", request.user_id, admin_u.get('username','?') if admin_u else '?')
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

@app.route('/api/users/<user_id>/password', methods=['PUT'])
@token_required
def change_password(user_id):
    """Changer le mot de passe — admin ou utilisateur lui-même."""
    if request.user_role != 'admin' and request.user_id != user_id:
        return jsonify({'error': 'Accès refusé'}), 403
    data = request.json or {}
    new_pwd = data.get('password', '').strip()
    if len(new_pwd) < 6:
        return jsonify({'error': 'Mot de passe trop court (minimum 6 caractères)'}), 400
    hashed = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt(10))
    db.user.update_one({'_id': ObjectId(user_id)}, {'$set': {'password': hashed}})
    actor = db.user.find_one({'_id': ObjectId(request.user_id)})
    target = db.user.find_one({'_id': ObjectId(user_id)})
    log_activity('CHANGE_PASSWORD', f"Mot de passe modifié pour: {target.get('username','?') if target else user_id}",
                 request.user_id, actor.get('username','?') if actor else '?')
    return jsonify({'message': 'Mot de passe modifié'}), 200

# ── Cameras (IP / RTSP / HTTP) ────────────────────────────────────────────────

@app.route('/api/cameras', methods=['GET'])
@token_required
def list_cameras():
    cameras = list(db.camera.find().sort('created_at', -1))
    for c in cameras:
        c['_id'] = str(c['_id'])
        c['created_at'] = str(c.get('created_at', ''))
        c.pop('created_by', None)  # Remove ObjectId field that can't be JSON serialized
    return jsonify({'cameras': cameras}), 200

@app.route('/api/cameras', methods=['POST'])
@token_required
def create_camera():
    data = request.json or {}
    name     = data.get('name', '').strip()
    url      = data.get('url', '').strip()
    location = data.get('location', '').strip()
    cam_type = data.get('type', 'http')
    if not name or not url:
        return jsonify({'error': 'Nom et URL sont requis'}), 400
    cam = {
        'name': name, 'url': url, 'location': location, 'type': cam_type,
        'created_at': datetime.utcnow(),
        'created_by': ObjectId(request.user_id),
    }
    res = db.camera.insert_one(cam)
    cam['_id'] = str(res.inserted_id)
    cam['created_at'] = str(cam['created_at'])
    cam.pop('created_by', None)
    return jsonify({'camera': cam, 'camera_id': str(res.inserted_id), 'message': 'Caméra ajoutée'}), 201

@app.route('/api/cameras/<cam_id>', methods=['DELETE'])
@token_required
def delete_camera(cam_id):
    db.camera.delete_one({'_id': ObjectId(cam_id)})
    return jsonify({'message': 'Caméra supprimée'}), 200

@app.route('/api/captures/<filename>', methods=['GET'])
def serve_capture(filename):
    # Light auth: accept Bearer header OR ?token= query param (for <img> tags)
    token_str = request.headers.get('Authorization', '').replace('Bearer ', '') \
                or request.args.get('token', '')
    if not token_str:
        return jsonify({'error': 'Missing token'}), 401
    try:
        jwt.decode(token_str, app.config['SECRET_KEY'], algorithms=['HS256'])
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401
    # Prevent path traversal
    safe_name = os.path.basename(filename)
    captures_dir = os.path.join(BASE_DIR, 'captures')
    path = os.path.join(captures_dir, safe_name)
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
@token_required
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


# ── Activity Logs ─────────────────────────────────────────────────────────────

@app.route('/api/activity-logs', methods=['GET'])
@token_required
def get_activity_logs():
    """Journal d'activité — admin: tout, user: son propre journal."""
    page  = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    skip  = (page - 1) * limit

    if request.user_role == 'admin':
        query = {}
    else:
        query = {'user_id': ObjectId(request.user_id)}

    total = db.activity_log.count_documents(query)
    logs  = list(db.activity_log.find(query).sort('created_at', -1).skip(skip).limit(limit))
    for l in logs:
        l['_id'] = str(l['_id'])
        l['user_id'] = str(l['user_id']) if l.get('user_id') else None
        l['created_at'] = l['created_at'].strftime('%Y-%m-%dT%H:%M:%S') if hasattr(l.get('created_at'), 'strftime') else str(l.get('created_at', ''))

    return jsonify({'logs': logs, 'total': total, 'page': page, 'limit': limit}), 200


# ── Alerts Export (all alerts) ────────────────────────────────────────────────

@app.route('/api/alerts/export', methods=['GET'])
@token_required
def export_alerts():
    """Retourne toutes les alertes pour export CSV/Excel/PDF — TOUT LE MONDE voit LES MÊMES alertes."""
    # EVERYONE sees ALL alerts (no user filtering)
    raw = list(db.alert.find({}).sort('created_at', -1).limit(500))
    result = []
    for al in raw:
        a_doc = db.analysis.find_one({'_id': al.get('analysis')}, {'video': 1})
        v_doc = db.video.find_one({'_id': a_doc.get('video')}, {'title': 1}) if a_doc else None
        created = al.get('created_at')
        result.append({
            '_id':        str(al['_id']),
            'event_type': al.get('event_type', ''),
            'risk_level': al.get('risk_level', 'low'),
            'frame_id':   al.get('frame_id', 0),
            'timestamp':  round(float(al.get('timestamp', 0)), 2),
            'capture':    al.get('capture'),
            'video_title': v_doc['title'] if v_doc else 'Inconnu',
            'created_at': created.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(created, 'strftime') else str(created or ''),
        })
    return jsonify({'alerts': result, 'total': len(result)}), 200


# ── Live Camera Analysis ───────────────────────────────────────────────────────

def _extract_youtube_id(url):
    m = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else None

def _get_live_stream_url(cam):
    """Retourne (stream_url, stream_type) en résolvant YouTube si nécessaire."""
    url = cam.get('url', '')
    cam_type = cam.get('type', 'http')

    if cam_type == 'youtube' or 'youtube' in url or 'youtu.be' in url:
        ytid = _extract_youtube_id(url)
        if not ytid:
            return None, None
        # Essaie yt-dlp pour récupérer l'URL HLS réelle
        for cmd in (['yt-dlp', '-g', '-f', 'best[ext=mp4]/best', url],
                     ['python', '-m', 'yt_dlp', '-g', '-f', 'best', url]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
                if r.returncode == 0:
                    stream_url = r.stdout.strip().split('\n')[0]
                    if stream_url:
                        return stream_url, 'hls'
            except Exception:
                continue
        return None, None

    return url, cam_type


def _draw_annotation(frame, event_type, box=None):
    """Ajoute une bannière colorée + rectangle sur la frame."""
    colors = {'fall': (0, 0, 220), 'crowding': (0, 140, 255), 'abandoned': (0, 200, 50)}
    labels = {'fall': 'CHUTE DETECTEE', 'crowding': 'ATTROUPEMENT', 'abandoned': 'OBJET ABANDONNE'}
    color = colors.get(event_type, (128, 128, 128))
    label = labels.get(event_type, event_type.upper())
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 36), color, -1)
    cv2.putText(frame, label, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    if box:
        x1, y1, x2, y2 = box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
    return frame


def _run_live_analysis(cam_id, analysis_id, user_id):
    """Thread principal d'analyse en direct — OpenCV + YOLOv8."""
    FRAME_SKIP        = 3
    FALL_COOLDOWN     = 300   # frames
    CROWD_COOLDOWN    = 90
    ABANDON_COOLDOWN  = 900
    CROWD_MIN         = 5
    FALL_RATIO        = 0.65
    STATIONARY_THR    = 22
    GRID_SZ           = 100
    CONF              = 0.35

    log.info(f"[LIVE] Démarrage analyse caméra {cam_id}")
    try:
        cam = db.camera.find_one({'_id': ObjectId(cam_id)})
        if not cam:
            db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
                {'$set': {'status': 'failed', 'error': 'Caméra introuvable'}})
            return

        stream_url, _ = _get_live_stream_url(cam)
        if not stream_url:
            db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
                {'$set': {'status': 'failed', 'error': 'Impossible de résoudre le flux (yt-dlp requis pour YouTube)'}})
            live_analyses.pop(cam_id, None)
            return

        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
                {'$set': {'status': 'failed', 'error': 'Flux inaccessible'}})
            live_analyses.pop(cam_id, None)
            return

        db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
            {'$set': {'status': 'running', 'started_at': datetime.utcnow()}})

        # Charger YOLOv8
        try:
            from ultralytics import YOLO
            model = YOLO('yolov8n.pt')
        except Exception as e:
            db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
                {'$set': {'status': 'failed', 'error': f'YOLOv8 non disponible: {e}'}})
            cap.release()
            live_analyses.pop(cam_id, None)
            return

        captures_dir = os.path.join(BASE_DIR, 'captures')
        os.makedirs(captures_dir, exist_ok=True)

        frame_count      = 0
        last_fall        = {}   # person_id -> frame
        last_crowd_frame = -CROWD_COOLDOWN
        last_abandon     = {}   # cell -> frame
        object_grid      = {}   # cell -> stationary_count
        total_events     = 0

        while live_analyses.get(cam_id, {}).get('running', False):
            ret, frame = cap.read()
            if not ret:
                # Flux coupé — attendre un peu et réessayer
                time.sleep(0.5)
                continue

            frame_count += 1
            if frame_count % FRAME_SKIP != 0:
                continue

            results = model(frame, conf=CONF, iou=0.45, verbose=False, classes=[0])
            persons = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    w_b, h_b = x2 - x1, y2 - y1
                    persons.append({'box': (x1, y1, x2, y2), 'cx': cx, 'cy': cy,
                                    'w': w_b, 'h': h_b, 'pid': f'{cx//20}_{cy//20}'})

            events = []

            # — Chute —
            for p in persons:
                ratio = p['h'] / (p['w'] + 1e-5)
                if ratio < FALL_RATIO:
                    pid = p['pid']
                    if frame_count - last_fall.get(pid, -FALL_COOLDOWN) >= FALL_COOLDOWN:
                        last_fall[pid] = frame_count
                        events.append({'event_type': 'fall', 'risk_level': 'high', 'box': p['box']})

            # — Attroupement —
            if len(persons) >= CROWD_MIN:
                if frame_count - last_crowd_frame >= CROWD_COOLDOWN:
                    last_crowd_frame = frame_count
                    events.append({'event_type': 'crowding', 'risk_level': 'medium',
                                   'box': None, 'count': len(persons)})

            # — Objet abandonné —
            occupied = set()
            for p in persons:
                occupied.add((p['cx'] // GRID_SZ, p['cy'] // GRID_SZ))
            for cell in list(object_grid.keys()):
                if cell not in occupied:
                    object_grid[cell] = object_grid.get(cell, 0) + 1
                    if object_grid[cell] >= STATIONARY_THR:
                        if frame_count - last_abandon.get(cell, -ABANDON_COOLDOWN) >= ABANDON_COOLDOWN:
                            last_abandon[cell] = frame_count
                            events.append({'event_type': 'abandoned', 'risk_level': 'high', 'box': None})
                else:
                    object_grid[cell] = 0
            for cell in occupied:
                object_grid.setdefault(cell, 0)

            # — Sauvegarder les alertes —
            for ev in events:
                ann = _draw_annotation(frame.copy(), ev['event_type'], ev.get('box'))
                ts_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
                fname  = f"live_{cam_id}_{ts_str}.jpg"
                cv2.imwrite(os.path.join(captures_dir, fname), ann,
                            [cv2.IMWRITE_JPEG_QUALITY, 82])

                db.live_alert.insert_one({
                    'live_analysis_id': ObjectId(analysis_id),
                    'camera_id':   ObjectId(cam_id),
                    'camera_name': cam.get('name', ''),
                    'event_type':  ev['event_type'],
                    'risk_level':  ev['risk_level'],
                    'frame_id':    frame_count,
                    'timestamp':   round(frame_count / 25.0, 1),
                    'capture':     fname,
                    'created_at':  datetime.utcnow(),
                    'user_id':     ObjectId(user_id),
                })
                total_events += 1

                inc = {'fall': 'falls_detected', 'crowding': 'crowds_detected',
                       'abandoned': 'abandoned_objects'}.get(ev['event_type'])
                if inc:
                    db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
                        {'$inc': {inc: 1, 'total_events': 1},
                         '$set': {'updated_at': datetime.utcnow(), 'frames_processed': frame_count}})

        cap.release()
        log.info(f"[LIVE] Analyse caméra {cam_id} terminée — {total_events} événements")

    except Exception as e:
        log.error(f"[LIVE] Erreur analyse {cam_id}: {e}")
        db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
            {'$set': {'status': 'failed', 'error': str(e)}})
    finally:
        live_analyses.pop(cam_id, None)
        db.live_analysis.update_one({'_id': ObjectId(analysis_id)},
            {'$set': {'status': 'stopped', 'stopped_at': datetime.utcnow()}})


@app.route('/api/cameras/<cam_id>/live/start', methods=['POST'])
@token_required
def start_live_analysis(cam_id):
    """Démarre l'analyse en direct d'une caméra."""
    if cam_id in live_analyses and live_analyses[cam_id].get('running'):
        return jsonify({'error': 'Analyse déjà en cours', 'analysis_id': live_analyses[cam_id]['analysis_id']}), 400

    cam = db.camera.find_one({'_id': ObjectId(cam_id)})
    if not cam:
        return jsonify({'error': 'Caméra introuvable'}), 404

    doc = {
        'camera_id': ObjectId(cam_id),
        'camera_name': cam.get('name', ''),
        'user_id': ObjectId(request.user_id),
        'status': 'pending',
        'total_events': 0,
        'falls_detected': 0,
        'crowds_detected': 0,
        'abandoned_objects': 0,
        'frames_processed': 0,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    }
    res = db.live_analysis.insert_one(doc)
    analysis_id = str(res.inserted_id)

    thread = threading.Thread(
        target=_run_live_analysis,
        args=(cam_id, analysis_id, request.user_id),
        daemon=True
    )
    live_analyses[cam_id] = {'running': True, 'analysis_id': analysis_id, 'thread': thread}
    thread.start()

    return jsonify({'message': 'Analyse démarrée', 'analysis_id': analysis_id}), 201


@app.route('/api/cameras/<cam_id>/live/stop', methods=['POST'])
@token_required
def stop_live_analysis(cam_id):
    """Arrête l'analyse en direct."""
    if cam_id not in live_analyses:
        return jsonify({'error': 'Aucune analyse en cours'}), 404
    live_analyses[cam_id]['running'] = False
    return jsonify({'message': 'Arrêt demandé'}), 200


@app.route('/api/cameras/<cam_id>/live/status', methods=['GET'])
@token_required
def get_live_status(cam_id):
    """Statut + alertes récentes de l'analyse en direct."""
    running_info = live_analyses.get(cam_id)
    analysis_id  = (running_info or {}).get('analysis_id')

    # Cherche aussi la dernière analyse (même stoppée)
    last_analysis = db.live_analysis.find_one(
        {'camera_id': ObjectId(cam_id)},
        sort=[('created_at', -1)]
    )
    if not analysis_id and last_analysis:
        analysis_id = str(last_analysis['_id'])

    since_str = request.args.get('since')  # ISO datetime — pour récupérer seulement les nouvelles alertes
    alert_query = {'camera_id': ObjectId(cam_id)}
    if analysis_id:
        alert_query['live_analysis_id'] = ObjectId(analysis_id)
    if since_str:
        try:
            since_dt = datetime.fromisoformat(since_str.replace('Z', ''))
            alert_query['created_at'] = {'$gt': since_dt}
        except Exception:
            pass

    alerts_raw = list(db.live_alert.find(alert_query).sort('created_at', -1).limit(20))
    alerts = [{
        '_id':        str(a['_id']),
        'event_type': a.get('event_type', ''),
        'risk_level': a.get('risk_level', 'low'),
        'frame_id':   a.get('frame_id', 0),
        'timestamp':  a.get('timestamp', 0),
        'capture':    a.get('capture'),
        'created_at': a['created_at'].strftime('%Y-%m-%dT%H:%M:%S') if hasattr(a.get('created_at'), 'strftime') else str(a.get('created_at', '')),
    } for a in alerts_raw]

    counters = last_analysis or {}
    return jsonify({
        'running':     bool(running_info and running_info.get('running')),
        'analysis_id': analysis_id,
        'status':      counters.get('status', 'idle'),
        'total_events':    counters.get('total_events', 0),
        'falls_detected':  counters.get('falls_detected', 0),
        'crowds_detected': counters.get('crowds_detected', 0),
        'abandoned_objects': counters.get('abandoned_objects', 0),
        'frames_processed':  counters.get('frames_processed', 0),
        'alerts': alerts,
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    log.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

def seed_demo_camera():
    """Insérer une caméra de rue de démonstration si aucune n'existe."""
    if db.camera.count_documents({}) == 0:
        db.camera.insert_one({
            'name': 'Caméra Rue de Démonstration',
            'url': 'http://77.222.181.11:8080/video',
            'location': 'Intersection principale — flux public test',
            'type': 'http',
            'created_at': datetime.utcnow(),
            'demo': True,
        })
        log.info("Caméra de démonstration insérée.")

if __name__ == '__main__':
    log.info("Demarrage de l'API Flask...")
    seed_demo_camera()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
