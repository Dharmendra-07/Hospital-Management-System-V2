"""
backend/routes/auth.py  —  Authentication with full backend validation
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from models import db, User, Patient
from utils.validators import validate_form, schemas
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data   = request.get_json() or {}
    errors = validate_form(data, schemas.patient_register)
    if errors:
        return jsonify({'errors': errors}), 422

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'errors': {'username': 'Username already taken.'}}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'errors': {'email': 'Email already registered.'}}), 409

    user = User(username=data['username'].strip(),
                email=data['email'].strip().lower(),
                role='patient', is_active=True)
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()

    patient = Patient(
        user_id=user.id, full_name=data['full_name'].strip(),
        contact_number=data.get('contact_number', ''),
        gender=data.get('gender', ''),
        date_of_birth=data.get('date_of_birth'),
        address=data.get('address', ''),
    )
    db.session.add(patient)
    db.session.commit()
    return jsonify({'message': 'Registration successful. Please log in.'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data   = request.get_json() or {}
    errors = validate_form(data, schemas.login)
    if errors:
        return jsonify({'errors': errors}), 422

    user = User.query.filter_by(username=data['username'].strip()).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password.'}), 401
    if not user.is_active:
        return jsonify({'error': 'Account suspended. Contact admin.'}), 403

    claims = {'role': user.role, 'username': user.username, 'email': user.email}
    access  = create_access_token(identity=str(user.id),
                                   additional_claims=claims,
                                   expires_delta=timedelta(hours=8))
    refresh = create_refresh_token(identity=str(user.id),
                                    additional_claims=claims,
                                    expires_delta=timedelta(days=7))
    return jsonify({
        'access_token': access, 'refresh_token': refresh,
        'role': user.role, 'username': user.username, 'user_id': user.id,
        'redirect': {'admin': '/admin/dashboard', 'doctor': '/doctor/dashboard',
                     'patient': '/patient/dashboard'}.get(user.role, '/'),
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims   = get_jwt()
    new_access = create_access_token(
        identity=identity,
        additional_claims={'role': claims.get('role'),
                           'username': claims.get('username'),
                           'email': claims.get('email')},
        expires_delta=timedelta(hours=8)
    )
    return jsonify({'access_token': new_access}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    claims  = get_jwt()
    role    = claims.get('role')
    user    = User.query.get_or_404(user_id)
    profile = {}

    if role == 'patient' and user.patient_profile:
        p = user.patient_profile
        profile = {'id': p.id, 'full_name': p.full_name,
                   'gender': p.gender, 'blood_group': p.blood_group,
                   'date_of_birth': str(p.date_of_birth) if p.date_of_birth else None,
                   'contact_number': p.contact_number, 'address': p.address}
    elif role == 'doctor' and user.doctor_profile:
        d = user.doctor_profile
        profile = {'id': d.id, 'full_name': d.full_name,
                   'specialization': d.specialization,
                   'department': d.department.name if d.department else None}

    return jsonify({'user_id': user.id, 'username': user.username,
                    'email': user.email, 'role': role, 'profile': profile}), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logged out successfully.'}), 200
