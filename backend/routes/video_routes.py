"""Routes de gestion des vidéos."""

from flask import Blueprint, request, jsonify
from ..services.auth_service import token_required
from ..services.video_service import VideoService

video_bp = Blueprint('video', __name__, url_prefix='/api/videos')


@video_bp.route('/upload', methods=['POST'])
@token_required
def upload_video():
    """Upload une vidéo."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    title = request.form.get('title', '')
    description = request.form.get('description', '')

    result = VideoService.upload_video(file, request.user, title, description)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'message': 'Video uploaded successfully',
        'video': result['video']
    }), result['code']


@video_bp.route('/<video_id>', methods=['GET'])
@token_required
def get_video(video_id):
    """Récupère une vidéo."""
    result = VideoService.get_video(video_id, request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'video': result['video']
    }), result['code']


@video_bp.route('', methods=['GET'])
@token_required
def list_videos():
    """Liste les vidéos."""
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 20, type=int)

    result = VideoService.list_videos(request.user, skip, limit)

    return jsonify({
        'videos': result['videos'],
        'total': result['total']
    }), result['code']


@video_bp.route('/<video_id>', methods=['DELETE'])
@token_required
def delete_video(video_id):
    """Supprime une vidéo."""
    result = VideoService.delete_video(video_id, request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'message': result['message']
    }), result['code']


@video_bp.route('/<video_id>/file', methods=['GET'])
@token_required
def download_video_file(video_id):
    """Télécharge le fichier vidéo."""
    from flask import send_file
    result = VideoService.get_video(video_id, request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    video = result['video']
    filepath = video.get('filepath')

    if not filepath:
        return jsonify({'error': 'File not found'}), 404

    return send_file(filepath, as_attachment=True)
