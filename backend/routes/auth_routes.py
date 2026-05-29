"""Routes d'authentification."""

from flask import Blueprint, request, jsonify
from ..services.auth_service import AuthService, token_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Enregistre un nouvel utilisateur."""
    data = request.get_json()

    if not data or not all(k in data for k in ['email', 'password', 'username']):
        return jsonify({'error': 'Missing fields'}), 400

    result = AuthService.register_user(
        email=data['email'],
        password=data['password'],
        username=data['username'],
        full_name=data.get('full_name', '')
    )

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'message': 'User registered successfully',
        'user': result['user']
    }), result['code']


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authentifie un utilisateur."""
    data = request.get_json()

    if not data or not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing email or password'}), 400

    result = AuthService.login_user(
        email=data['email'],
        password=data['password']
    )

    if 'error' in result:
        return jsonify({'error': result['error']}), result['code']

    return jsonify({
        'message': 'Login successful',
        'user': result['user'],
        'token': result['token']
    }), result['code']


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Récupère l'utilisateur courant."""
    return jsonify({
        'user': request.user.to_dict()
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """Change le mot de passe de l'utilisateur."""
    data = request.get_json()

    if not data or not all(k in data for k in ['old_password', 'new_password']):
        return jsonify({'error': 'Missing fields'}), 400

    # Vérifier l'ancien mot de passe
    if not AuthService.verify_password(data['old_password'], request.user.password):
        return jsonify({'error': 'Invalid current password'}), 401

    # Mettre à jour le mot de passe
    request.user.password = AuthService.hash_password(data['new_password'])
    request.user.save()

    return jsonify({
        'message': 'Password changed successfully'
    }), 200
