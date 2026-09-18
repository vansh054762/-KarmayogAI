"""
Auth Routes — Register, Login, Profile
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from models.database import db, User
from utils.passwords import hash_password, verify_password, needs_rehash
from utils.security import sanitize_dict, validate_email, validate_password, rate_limit
from utils.audit import log_auth, log_data, log_security

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=3600)  # 10 registrations/hour per IP
def register():
    raw = request.get_json(silent=True) or {}

    try:
        data = sanitize_dict(raw, {
            'name':        {'type': str, 'required': True,  'min_length': 2, 'max_length': 100},
            'email':       {'type': str, 'required': True,  'max_length': 120},
            'password':    {'type': str, 'required': True},
            'department':  {'type': str, 'required': False, 'max_length': 100, 'default': ''},
            'designation': {'type': str, 'required': False, 'max_length': 100, 'default': ''},
        })
        email = validate_email(raw.get('email', ''))
        validate_password(raw.get('password', ''))
    except ValueError as e:
        log_security('invalid_input', details={'action': 'register', 'error': str(e)})
        return jsonify({'error': str(e)}), 400

    if User.query.filter_by(email=email).first():
        log_auth('register', details={'email': email, 'reason': 'duplicate'}, success=False)
        return jsonify({'error': 'Email already registered'}), 409

    user = User(
        name=data['name'],
        email=email,
        password_hash=hash_password(raw['password']),
        department=data['department'],
        designation=data['designation'],
        role='employee'
    )
    db.session.add(user)
    db.session.commit()

    log_auth('register', user_id=user.id, details={'email': email})
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=300)  # 10 attempts per 5 minutes per IP
def login():
    raw = request.get_json(silent=True) or {}

    try:
        email = validate_email(raw.get('email', ''))
    except ValueError as e:
        log_security('invalid_input', details={'action': 'login', 'error': str(e)})
        return jsonify({'error': 'Invalid email or password'}), 401

    user = User.query.filter_by(email=email).first()

    # Constant-time check regardless of whether user exists (prevents user enumeration)
    password = raw.get('password', '')
    if not user or not verify_password(password, user.password_hash):
        log_auth('login', user_id=user.id if user else None,
                 details={'email': email, 'reason': 'invalid_credentials'}, success=False)
        return jsonify({'error': 'Invalid email or password'}), 401

    # Transparent bcrypt rehash: if stored hash is legacy Werkzeug, upgrade it now
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.session.commit()
        log_auth('password_rehash', user_id=user.id, details={'email': email})

    log_auth('login', user_id=user.id, details={'email': email})
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    raw = request.get_json(silent=True) or {}

    try:
        data = sanitize_dict(raw, {
            'name':        {'type': str, 'required': False, 'min_length': 2, 'max_length': 100},
            'department':  {'type': str, 'required': False, 'max_length': 100},
            'designation': {'type': str, 'required': False, 'max_length': 100},
        })
    except ValueError as e:
        log_security('invalid_input', user_id=user_id, details={'action': 'update_profile', 'error': str(e)})
        return jsonify({'error': str(e)}), 400

    if data.get('name') is not None:
        user.name = data['name']
    if data.get('department') is not None:
        user.department = data['department']
    if data.get('designation') is not None:
        user.designation = data['designation']

    # Password change
    if raw.get('new_password'):
        if not verify_password(raw.get('current_password', ''), user.password_hash):
            log_auth('password_change', user_id=user_id,
                     details={'reason': 'wrong_current_password'}, success=False)
            return jsonify({'error': 'Current password is incorrect'}), 400
        try:
            validate_password(raw['new_password'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        user.password_hash = hash_password(raw['new_password'])
        log_auth('password_change', user_id=user_id)

    db.session.commit()
    log_data('profile_update', user_id=user_id)
    return jsonify(user.to_dict()), 200
