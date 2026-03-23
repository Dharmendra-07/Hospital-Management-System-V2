"""
middleware/rbac.py
Role-based access decorators — wrap any route that needs role restriction.

Usage:
    @admin_required
    @doctor_required
    @patient_required
    @roles_required('admin', 'doctor')   ← allows multiple roles
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt, verify_jwt_in_request


def roles_required(*roles):
    """Allow access only to users whose role is in the given list."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role not in roles:
                return jsonify({
                    'error': f"Access denied. Required role(s): {', '.join(roles)}."
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Convenience decorators ──────────────────

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Admin access required.'}), 403
        return fn(*args, **kwargs)
    return wrapper


def doctor_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'doctor':
            return jsonify({'error': 'Doctor access required.'}), 403
        return fn(*args, **kwargs)
    return wrapper


def patient_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'patient':
            return jsonify({'error': 'Patient access required.'}), 403
        return fn(*args, **kwargs)
    return wrapper


def active_user_required(fn):
    """Reject blacklisted (is_active=False) users even with a valid token."""
    from models import User
    from flask_jwt_extended import get_jwt_identity
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())
        user    = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({'error': 'Account suspended. Contact admin.'}), 403
        return fn(*args, **kwargs)
    return wrapper
