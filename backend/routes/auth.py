"""
routes/auth.py
Handles: Patient Register, Login (all roles), Token Refresh, Logout, /me
JWT-based authentication using Flask-JWT-Extended
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from models import db, User, Patient, Doctor
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)


# ─────────────────────────────────────────────
# POST /api/auth/register   → Patients only
# ─────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # ── Validation ──
    required = ['username', 'email', 'password', 'full_name']
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken.'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered.'}), 409

    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400

    # ── Create User ──
    user = User(
        username  = data['username'].strip(),
        email     = data['email'].strip().lower(),
        role      = 'patient',
        is_active = True,
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()   # get user.id before commit

    # ── Create Patient Profile ──
    patient = Patient(
        user_id        = user.id,
        full_name      = data['full_name'].strip(),
        contact_number = data.get('contact_number', ''),
        gender         = data.get('gender', ''),
        date_of_birth  = data.get('date_of_birth'),
        address        = data.get('address', ''),
    )
    db.session.add(patient)
    db.session.commit()

    return jsonify({'message': 'Registration successful. Please log in.'}), 201


# ─────────────────────────────────────────────
# POST /api/auth/login   → All roles
# ─────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    if not user.is_active:
        return jsonify({'error': 'Your account has been suspended. Contact admin.'}), 403

    # ── Build identity payload ──
    identity = str(user.id)
    additional_claims = {
        'role':     user.role,
        'username': user.username,
        'email':    user.email,
    }

    access_token  = create_access_token(
        identity          = identity,
        additional_claims = additional_claims,
        expires_delta     = timedelta(hours=8)
    )
    refresh_token = create_refresh_token(
        identity          = identity,
        additional_claims = additional_claims,
        expires_delta     = timedelta(days=7)
    )

    # ── Role-specific dashboard route ──
    dashboard_map = {
        'admin':   '/admin/dashboard',
        'doctor':  '/doctor/dashboard',
        'patient': '/patient/dashboard',
    }

    return jsonify({
        'access_token':  access_token,
        'refresh_token': refresh_token,
        'role':          user.role,
        'username':      user.username,
        'user_id':       user.id,
        'redirect':      dashboard_map.get(user.role, '/'),
    }), 200


# ─────────────────────────────────────────────
# POST /api/auth/refresh   → Get new access token
# ─────────────────────────────────────────────
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    claims   = get_jwt()

    new_access = create_access_token(
        identity          = identity,
        additional_claims = {
            'role':     claims.get('role'),
            'username': claims.get('username'),
            'email':    claims.get('email'),
        },
        expires_delta = timedelta(hours=8)
    )
    return jsonify({'access_token': new_access}), 200


# ─────────────────────────────────────────────
# GET /api/auth/me   → Current user info
# ─────────────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    claims  = get_jwt()
    role    = claims.get('role')

    user = User.query.get_or_404(user_id)

    profile = {}
    if role == 'patient' and user.patient_profile:
        p = user.patient_profile
        profile = {
            'id':             p.id,
            'full_name':      p.full_name,
            'contact_number': p.contact_number,
            'gender':         p.gender,
            'date_of_birth':  str(p.date_of_birth) if p.date_of_birth else None,
            'blood_group':    p.blood_group,
            'address':        p.address,
        }
    elif role == 'doctor' and user.doctor_profile:
        d = user.doctor_profile
        profile = {
            'id':               d.id,
            'full_name':        d.full_name,
            'specialization':   d.specialization,
            'qualification':    d.qualification,
            'experience_years': d.experience_years,
            'department':       d.department.name if d.department else None,
        }

    return jsonify({
        'user_id':  user.id,
        'username': user.username,
        'email':    user.email,
        'role':     role,
        'profile':  profile,
    }), 200


# ─────────────────────────────────────────────
# POST /api/auth/logout   → Client drops token
# ─────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # JWT is stateless; client must delete the token.
    # For token blocklisting, add jti to a Redis set here.
    return jsonify({'message': 'Logged out successfully.'}), 200
