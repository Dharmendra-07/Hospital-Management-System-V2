"""
backend/utils/validators.py
Server-side validation helpers — mirror of frontend/src/utils/validators.js.
Always validate on the server even when frontend validation exists.

Usage:
    from utils.validators import validate_form, schemas, ValidationError

    errors = validate_form(request.get_json(), schemas.patient_register)
    if errors:
        return jsonify({'errors': errors}), 422
"""

import re
from datetime import date as _date


# ── Error collector ─────────────────────────────────────────

class ValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


# ── Primitive validators ────────────────────────────────────

def required(label='This field'):
    def _check(v):
        if v is None or str(v).strip() == '':
            return f'{label} is required.'
        return None
    return _check


def min_len(n, label='Value'):
    def _check(v):
        if v and len(str(v).strip()) < n:
            return f'{label} must be at least {n} characters.'
        return None
    return _check


def max_len(n, label='Value'):
    def _check(v):
        if v and len(str(v).strip()) > n:
            return f'{label} must be at most {n} characters.'
        return None
    return _check


def is_email(v):
    if v and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', str(v)):
        return 'Enter a valid email address.'
    return None


def is_phone(v):
    if v and not re.match(r'^[+\d\s\-()\[\]]{7,20}$', str(v)):
        return 'Enter a valid phone number.'
    return None


def no_spaces(v):
    if v and ' ' in str(v):
        return 'No spaces allowed.'
    return None


def is_number(label='Value'):
    def _check(v):
        if v is not None and v != '':
            try:
                float(v)
            except (ValueError, TypeError):
                return f'{label} must be a number.'
        return None
    return _check


def min_val(n, label='Value'):
    def _check(v):
        if v is not None and v != '':
            try:
                if float(v) < n:
                    return f'{label} must be at least {n}.'
            except (ValueError, TypeError):
                pass
        return None
    return _check


def is_future_date(v):
    if not v:
        return None
    try:
        d = _date.fromisoformat(str(v))
        if d < _date.today():
            return 'Date must be today or in the future.'
    except ValueError:
        return 'Enter a valid date (YYYY-MM-DD).'
    return None


def is_valid_date(v):
    if not v:
        return None
    try:
        _date.fromisoformat(str(v))
    except ValueError:
        return 'Enter a valid date (YYYY-MM-DD).'
    return None


def one_of(choices, label='Value'):
    def _check(v):
        if v not in choices:
            return f'{label} must be one of: {", ".join(str(c) for c in choices)}.'
        return None
    return _check


# ── Form-level runner ───────────────────────────────────────

def validate_form(data: dict, schema: dict) -> dict:
    """
    Run all validators in schema against data.
    Returns a dict of { field: error_message } for any failing fields.
    Empty dict means all valid.

    schema = {
        'email':    [required('Email'), is_email],
        'password': [required('Password'), min_len(6, 'Password')],
    }
    """
    errors = {}
    for field, rules in schema.items():
        value = data.get(field)
        for rule in rules:
            err = rule(value)
            if err:
                errors[field] = err
                break   # first error per field only
    return errors


# ── Pre-built schemas ────────────────────────────────────────

class schemas:

    patient_register = {
        'full_name': [required('Full name')],
        'username':  [required('Username'), min_len(3, 'Username'), no_spaces],
        'email':     [required('Email'), is_email],
        'password':  [required('Password'), min_len(6, 'Password')],
    }

    patient_profile_update = {
        'full_name':      [required('Full name')],
        'email':          [is_email],
        'contact_number': [is_phone],
    }

    add_doctor = {
        'full_name':        [required('Full name')],
        'username':         [required('Username'), min_len(3, 'Username'), no_spaces],
        'email':            [required('Email'), is_email],
        'password':         [required('Password'), min_len(6, 'Password')],
        'specialization':   [required('Specialization')],
        'experience_years': [is_number('Experience'), min_val(0, 'Experience')],
    }

    update_doctor = {
        'full_name':        [required('Full name')],
        'specialization':   [required('Specialization')],
        'experience_years': [is_number('Experience'), min_val(0, 'Experience')],
    }

    book_appointment = {
        'doctor_id':  [required('Doctor')],
        'date':       [required('Date'), is_future_date],
        'time_slot':  [required('Time slot')],
        'visit_type': [one_of(['In-person', 'Online'], 'Visit type')],
    }

    reschedule_appointment = {
        'date':      [required('Date'), is_future_date],
        'time_slot': [required('Time slot')],
    }

    treatment = {
        'diagnosis': [required('Diagnosis'), min_len(5, 'Diagnosis')],
    }

    login = {
        'username': [required('Username')],
        'password': [required('Password')],
    }

    availability_entry = {
        'date': [required('Date'), is_valid_date],
    }
