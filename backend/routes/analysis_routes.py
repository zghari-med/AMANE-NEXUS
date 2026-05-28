"""Routes de gestion des analyses."""

from flask import Blueprint, request, jsonify, send_file
from ..services.auth_service import token_required, admin_required
from ..services.analysis_service import AnalysisService
from ..services.export_service import ExportService

analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analyses')


@analysis_bp.route('/create', methods=['POST'])
@token_required
def create_analysis():
    """Crée une nouvelle analyse pour une vidéo."""
    data = request.get_json()

    if not data or 'video_id' not in data:
        return jsonify({'error': 'Missing video_id'}), 400

    result = AnalysisService.create_analysis(data['video_id'], request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'message': 'Analysis created successfully',
        'analysis': result['analysis']
    }), result['code']


@analysis_bp.route('/<analysis_id>', methods=['GET'])
@token_required
def get_analysis(analysis_id):
    """Récupère une analyse."""
    result = AnalysisService.get_analysis(analysis_id, request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'analysis': result['analysis']
    }), result['code']


@analysis_bp.route('', methods=['GET'])
@token_required
def list_analyses():
    """Liste les analyses."""
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 20, type=int)

    result = AnalysisService.list_analyses(request.user, skip, limit)

    return jsonify({
        'analyses': result['analyses'],
        'total': result['total']
    }), result['code']


@analysis_bp.route('/<analysis_id>/alerts', methods=['GET'])
@token_required
def get_analysis_alerts(analysis_id):
    """Récupère les alertes d'une analyse."""
    result = AnalysisService.get_analysis_alerts(analysis_id, request.user)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'alerts': result['alerts'],
        'total': result['total']
    }), result['code']


@analysis_bp.route('/statistics', methods=['GET'])
@token_required
def get_statistics():
    """Récupère les statistiques."""
    result = AnalysisService.get_statistics(request.user)

    return jsonify(result['statistics']), result['code']


@analysis_bp.route('/<analysis_id>/export/csv', methods=['GET'])
@token_required
def export_to_csv(analysis_id):
    """Exporte une analyse en CSV."""
    result = ExportService.export_to_csv(analysis_id)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    from io import StringIO
    return send_file(
        StringIO(result['content']),
        mimetype='text/csv',
        as_attachment=True,
        download_name=result['filename']
    )


@analysis_bp.route('/<analysis_id>/export/json', methods=['GET'])
@token_required
def export_to_json(analysis_id):
    """Exporte une analyse en JSON."""
    result = ExportService.export_to_json(analysis_id)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    from io import StringIO
    return send_file(
        StringIO(result['content']),
        mimetype='application/json',
        as_attachment=True,
        download_name=result['filename']
    )


@analysis_bp.route('/<analysis_id>/export/pdf', methods=['GET'])
@token_required
def export_to_pdf(analysis_id):
    """Exporte une analyse en PDF."""
    result = ExportService.export_to_pdf(analysis_id)

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    from io import BytesIO
    return send_file(
        BytesIO(result['content']),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=result['filename']
    )
