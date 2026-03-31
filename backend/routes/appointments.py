"""
backend/routes/appointments.py  —  Appointment history + conflict + stats
Cache strategy:
  GET /stats                 TTL 60 s   (changes with every booking/completion)
  GET /history/me            TTL 60 s   (patient's own history)
  GET /history/patient/<id>  TTL 60 s   (doctor/admin viewing patient)
  GET /history/admin/<id>    TTL 60 s
  Writes (status, treatment) always call Invalidate.appointment().
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from sqlalchemy import or_
from models import (db, User, Patient, Doctor, Department,
                    Appointment, Treatment, DoctorAvailability)
from middleware.rbac import admin_required, doctor_required, patient_required
from extensions import cache
from utils.cache_keys import CK, Invalidate, TTL_SHORT, TTL_MEDIUM
from utils.cache_helpers import get_or_set
from datetime import date
import json

appt_bp = Blueprint('appointments', __name__)


# ── serialisers ────────────────────────────────

def _ser_treatment(t):
    if not t:
        return None
    return {
        'id':           t.id,
        'diagnosis':    t.diagnosis,
        'prescription': t.prescription,
        'medicines':    json.loads(t.medicines) if t.medicines else [],
        'tests_done':   t.tests_done,
        'next_visit':   str(t.next_visit) if t.next_visit else None,
        'doctor_notes': t.doctor_notes,
        'created_at':   str(t.created_at)[:10] if t.created_at else None,
        'updated_at':   str(t.updated_at)[:10] if t.updated_at else None,
    }


def _ser_appt(a, include_treatment=True):
    entry = {
        'id':             a.id,
        'patient_id':     a.patient_id,
        'patient_name':   a.patient.full_name,
        'doctor_id':      a.doctor_id,
        'doctor_name':    a.doctor.full_name,
        'specialization': a.doctor.specialization,
        'department':     a.doctor.department.name if a.doctor.department else None,
        'date':           str(a.date),
        'time_slot':      a.time_slot,
        'visit_type':     a.visit_type,
        'status':         a.status,
        'notes':          a.notes,
        'created_at':     str(a.created_at)[:10] if a.created_at else None,
    }
    if include_treatment:
        entry['treatment'] = _ser_treatment(a.treatment)
    return entry


def _status_ok(current, new_status):
    return new_status in {'Booked': {'Completed', 'Cancelled'},
                          'Completed': set(), 'Cancelled': set()
                         }.get(current, set())


# ─────────────────────────────────────────────
# POST /api/appointments/check-conflict
# ─────────────────────────────────────────────
@appt_bp.route('/check-conflict', methods=['POST'])
def check_conflict():
    verify_jwt_in_request()
    data      = request.get_json()
    doctor_id = data.get('doctor_id')
    slot      = data.get('time_slot')
    try:
        appt_date = date.fromisoformat(data.get('date', ''))
    except ValueError:
        return jsonify({'conflict': True, 'reason': 'Invalid date.'}), 400

    avail = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id, date=appt_date, slot=slot).first()

    if not avail:
        return jsonify({'conflict': True, 'reason': 'Slot does not exist.'}), 200
    if avail.is_booked:
        return jsonify({'conflict': True, 'reason': 'Slot already taken.'}), 200

    clash = Appointment.query.filter_by(
        doctor_id=doctor_id, date=appt_date,
        time_slot=slot, status='Booked').first()
    if clash:
        return jsonify({'conflict': True, 'reason': 'Slot already booked.'}), 200

    return jsonify({'conflict': False, 'reason': None}), 200


# ─────────────────────────────────────────────
# PATCH /api/appointments/<id>/status
# ─────────────────────────────────────────────
@appt_bp.route('/<int:appt_id>/status', methods=['PATCH'])
def update_status(appt_id):
    verify_jwt_in_request()
    claims    = get_jwt()
    role      = claims.get('role')
    user_id   = int(get_jwt_identity())

    if role not in ('admin', 'doctor'):
        return jsonify({'error': 'Access denied.'}), 403

    appt       = Appointment.query.get_or_404(appt_id)
    new_status = request.get_json().get('status')

    if role == 'doctor':
        user   = User.query.get(user_id)
        doctor = user.doctor_profile
        if not doctor or appt.doctor_id != doctor.id:
            return jsonify({'error': 'Access denied.'}), 403

    if not _status_ok(appt.status, new_status):
        return jsonify({'error': f"Cannot go from '{appt.status}' to '{new_status}'."}), 400

    if new_status == 'Cancelled':
        avail = DoctorAvailability.query.filter_by(
            doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot).first()
        if avail:
            avail.is_booked = False

    appt.status = new_status
    db.session.commit()
    Invalidate.appointment(cache, appt.doctor_id, appt.patient_id)
    return jsonify({'message': f'Marked {new_status}.', 'status': new_status,
                    'appt_id': appt_id}), 200


# ─────────────────────────────────────────────
# POST /api/appointments/<id>/treatment
# ─────────────────────────────────────────────
@appt_bp.route('/<int:appt_id>/treatment', methods=['POST'])
@doctor_required
def upsert_treatment(appt_id):
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    doctor  = user.doctor_profile

    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        return jsonify({'error': 'Access denied.'}), 403

    data = request.get_json()
    if not data.get('diagnosis', '').strip():
        return jsonify({'error': 'Diagnosis is required.'}), 400

    medicines = data.get('medicines', [])
    if not isinstance(medicines, list):
        return jsonify({'error': 'medicines must be a list.'}), 400

    treatment = appt.treatment or Treatment(appointment_id=appt.id)
    treatment.diagnosis    = data['diagnosis'].strip()
    treatment.prescription = data.get('prescription', '').strip()
    treatment.medicines    = json.dumps(medicines)
    treatment.tests_done   = data.get('tests_done', '').strip()
    treatment.doctor_notes = data.get('doctor_notes', '').strip()
    treatment.next_visit   = data.get('next_visit') or None

    if not appt.treatment:
        db.session.add(treatment)

    appt.status = 'Completed'
    db.session.commit()
    Invalidate.appointment(cache, doctor.id, appt.patient_id)
    return jsonify({'message': 'Treatment saved. Appointment Completed.',
                    'treatment': _ser_treatment(treatment)}), 200


# ─────────────────────────────────────────────
# GET /api/appointments/history/me  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@appt_bp.route('/history/me', methods=['GET'])
@patient_required
def patient_own_history():
    user_id = int(get_jwt_identity())
    patient = User.query.get(user_id).patient_profile
    view    = request.args.get('view', 'all')
    today   = date.today()

    def _build():
        q = Appointment.query.filter_by(patient_id=patient.id)
        if view == 'upcoming':
            q = q.filter(Appointment.date >= today, Appointment.status == 'Booked')
        elif view == 'past':
            q = q.filter(or_(Appointment.date < today,
                             Appointment.status.in_(['Completed', 'Cancelled'])))
        return [_ser_appt(a) for a in q.order_by(Appointment.date.desc()).all()]

    key = CK.patient_appointments(patient.id, f'history_{view}')
    return jsonify(get_or_set(key, _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# GET /api/appointments/history/patient/<id>  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@appt_bp.route('/history/patient/<int:patient_id>', methods=['GET'])
def patient_history_for_doctor(patient_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())

    if role not in ('admin', 'doctor'):
        return jsonify({'error': 'Access denied.'}), 403

    patient = Patient.query.get_or_404(patient_id)

    def _build():
        q = Appointment.query.filter_by(patient_id=patient_id)
        if role == 'doctor':
            doctor = User.query.get(user_id).doctor_profile
            if not doctor:
                return {'error': 'Doctor profile not found.'}
            q = q.filter_by(doctor_id=doctor.id)
        appts = q.order_by(Appointment.date.desc()).all()
        return {
            'patient': {
                'id': patient.id, 'full_name': patient.full_name,
                'gender': patient.gender, 'blood_group': patient.blood_group,
                'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
                'contact_number': patient.contact_number,
            },
            'history':      [_ser_appt(a) for a in appts],
            'total_visits': len(appts),
            'completed':    sum(1 for a in appts if a.status == 'Completed'),
            'cancelled':    sum(1 for a in appts if a.status == 'Cancelled'),
        }

    scope = f'doctor_{user_id}' if role == 'doctor' else 'admin'
    key   = f'appointments:history:patient:{patient_id}:{scope}'
    return jsonify(get_or_set(key, _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# GET /api/appointments/history/admin/<id>  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@appt_bp.route('/history/admin/<int:patient_id>', methods=['GET'])
@admin_required
def admin_patient_full_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    def _build():
        appts    = Appointment.query.filter_by(patient_id=patient_id)\
                                    .order_by(Appointment.date.desc()).all()
        by_doctor = {}
        for a in appts:
            by_doctor.setdefault(a.doctor.full_name, []).append(_ser_appt(a))
        return {
            'patient': {
                'id': patient.id, 'full_name': patient.full_name,
                'gender': patient.gender, 'blood_group': patient.blood_group,
                'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
                'contact_number': patient.contact_number, 'email': patient.user.email,
            },
            'summary': {
                'total':     len(appts),
                'booked':    sum(1 for a in appts if a.status == 'Booked'),
                'completed': sum(1 for a in appts if a.status == 'Completed'),
                'cancelled': sum(1 for a in appts if a.status == 'Cancelled'),
            },
            'by_doctor': by_doctor,
            'all':       [_ser_appt(a) for a in appts],
        }

    key = f'appointments:history:admin:{patient_id}'
    return jsonify(get_or_set(key, _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# GET /api/appointments/<id>
# ─────────────────────────────────────────────
@appt_bp.route('/<int:appt_id>', methods=['GET'])
def appointment_detail(appt_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    appt    = Appointment.query.get_or_404(appt_id)

    if role == 'patient':
        if not user.patient_profile or appt.patient_id != user.patient_profile.id:
            return jsonify({'error': 'Access denied.'}), 403
    elif role == 'doctor':
        if not user.doctor_profile or appt.doctor_id != user.doctor_profile.id:
            return jsonify({'error': 'Access denied.'}), 403

    return jsonify(_ser_appt(appt)), 200


# ─────────────────────────────────────────────
# GET /api/appointments/stats  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@appt_bp.route('/stats', methods=['GET'])
@admin_required
def appointment_stats():
    def _build():
        dept_stats = []
        for dept in Department.query.all():
            ids   = [d.id for d in dept.doctors.all()]
            count = Appointment.query.filter(
                Appointment.doctor_id.in_(ids)
            ).count() if ids else 0
            dept_stats.append({'department': dept.name, 'appointments': count})

        return {
            'total':        Appointment.query.count(),
            'booked':       Appointment.query.filter_by(status='Booked').count(),
            'completed':    Appointment.query.filter_by(status='Completed').count(),
            'cancelled':    Appointment.query.filter_by(status='Cancelled').count(),
            'by_department': dept_stats,
        }

    return jsonify(get_or_set(CK.APPT_STATS, _build, TTL_SHORT)), 200
