"""
backend/routes/appointments.py
Centralised appointment milestone routes:
  - Shared history view  (admin / doctor / patient scoped)
  - Conflict-check utility  (used at booking & reschedule)
  - Status transitions with full audit trail
  - Treatment upsert with validation
  - Admin-level full history report per patient
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from sqlalchemy import or_
from models import (db, User, Patient, Doctor,
                    Appointment, Treatment, DoctorAvailability)
from middleware.rbac import admin_required, doctor_required, patient_required
from datetime import date
import json

appt_bp = Blueprint('appointments', __name__)


# ═══════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════

def _serialize_treatment(t):
    """Return treatment dict or None."""
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


def _serialize_appointment(a, include_treatment=True):
    """Full appointment dict with optional treatment."""
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
        entry['treatment'] = _serialize_treatment(a.treatment)
    return entry


def _check_slot_conflict(doctor_id, appt_date, time_slot,
                          exclude_appt_id=None):
    """
    Returns an error string if the slot is already taken, else None.
    exclude_appt_id — pass current appt ID when rescheduling to skip self.
    """
    # 1. Check DoctorAvailability slot exists
    avail = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=appt_date,
        slot=time_slot,
    ).first()

    if not avail:
        return 'Selected slot does not exist in doctor availability.'

    if avail.is_booked:
        # Allow if the booked slot belongs to the appointment being rescheduled
        if exclude_appt_id:
            owner = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=appt_date,
                time_slot=time_slot,
                status='Booked',
            ).first()
            if owner and owner.id == exclude_appt_id:
                return None   # same slot, same appointment — let reschedule decide
        return 'This slot is already booked.'

    # 2. Double-check Appointment table (DB constraint backup)
    q = Appointment.query.filter_by(
        doctor_id=doctor_id,
        date=appt_date,
        time_slot=time_slot,
        status='Booked',
    )
    if exclude_appt_id:
        q = q.filter(Appointment.id != exclude_appt_id)
    if q.first():
        return 'Slot conflict: another appointment already exists at this time.'

    return None


def _status_transition_allowed(current, new_status):
    """
    Valid transitions:
      Booked     → Completed | Cancelled
      Completed  → (none)
      Cancelled  → (none)
    """
    allowed = {
        'Booked':    {'Completed', 'Cancelled'},
        'Completed': set(),
        'Cancelled': set(),
    }
    return new_status in allowed.get(current, set())


# ═══════════════════════════════════════════════
# CONFLICT CHECK ENDPOINT
# POST /api/appointments/check-conflict
# Body: { doctor_id, date, time_slot }
# Public (JWT required) — used by frontend before booking
# ═══════════════════════════════════════════════
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

    err = _check_slot_conflict(doctor_id, appt_date, slot)
    if err:
        return jsonify({'conflict': True,  'reason': err}), 200
    return     jsonify({'conflict': False, 'reason': None}), 200


# ═══════════════════════════════════════════════
# STATUS UPDATE
# PATCH /api/appointments/<id>/status
# Admin or Doctor only
# Body: { status: "Completed" | "Cancelled" }
# ═══════════════════════════════════════════════
@appt_bp.route('/<int:appt_id>/status', methods=['PATCH'])
def update_status(appt_id):
    verify_jwt_in_request()
    claims    = get_jwt()
    role      = claims.get('role')
    user_id   = int(get_jwt_identity())

    if role not in ('admin', 'doctor'):
        return jsonify({'error': 'Only Admin or Doctor can update status.'}), 403

    appt       = Appointment.query.get_or_404(appt_id)
    new_status = request.get_json().get('status')

    # Doctor can only modify their own appointments
    if role == 'doctor':
        user   = User.query.get(user_id)
        doctor = user.doctor_profile
        if not doctor or appt.doctor_id != doctor.id:
            return jsonify({'error': 'Access denied.'}), 403

    if not _status_transition_allowed(appt.status, new_status):
        return jsonify({
            'error': f"Cannot transition from '{appt.status}' to '{new_status}'."
        }), 400

    # Free the availability slot if cancelling
    if new_status == 'Cancelled':
        avail = DoctorAvailability.query.filter_by(
            doctor_id=appt.doctor_id,
            date=appt.date,
            slot=appt.time_slot,
        ).first()
        if avail:
            avail.is_booked = False

    appt.status = new_status
    db.session.commit()
    return jsonify({
        'message':    f'Appointment marked as {new_status}.',
        'status':     new_status,
        'appt_id':    appt_id,
    }), 200


# ═══════════════════════════════════════════════
# TREATMENT UPSERT
# POST /api/appointments/<id>/treatment
# Doctor only — creates or updates treatment for an appointment
# ═══════════════════════════════════════════════
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

    # Validate medicines list
    medicines = data.get('medicines', [])
    if not isinstance(medicines, list):
        return jsonify({'error': 'medicines must be a list.'}), 400
    for m in medicines:
        if not isinstance(m, dict) or 'name' not in m:
            return jsonify({'error': "Each medicine must have a 'name' field."}), 400

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
    return jsonify({
        'message':   'Treatment saved. Appointment marked Completed.',
        'treatment': _serialize_treatment(treatment),
    }), 200


# ═══════════════════════════════════════════════
# HISTORY — PATIENT (own records only)
# GET /api/appointments/history/me?view=all|past|upcoming
# ═══════════════════════════════════════════════
@appt_bp.route('/history/me', methods=['GET'])
@patient_required
def patient_own_history():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    patient = user.patient_profile
    view    = request.args.get('view', 'all')
    today   = date.today()

    q = Appointment.query.filter_by(patient_id=patient.id)
    if view == 'upcoming':
        q = q.filter(Appointment.date >= today, Appointment.status == 'Booked')
    elif view == 'past':
        q = q.filter(or_(
            Appointment.date < today,
            Appointment.status.in_(['Completed', 'Cancelled'])
        ))
    appts = q.order_by(Appointment.date.desc()).all()
    return jsonify([_serialize_appointment(a) for a in appts]), 200


# ═══════════════════════════════════════════════
# HISTORY — DOCTOR views a patient's history
# GET /api/appointments/history/patient/<id>
# Doctor or Admin
# ═══════════════════════════════════════════════
@appt_bp.route('/history/patient/<int:patient_id>', methods=['GET'])
def patient_history_for_doctor(patient_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())

    if role not in ('admin', 'doctor'):
        return jsonify({'error': 'Access denied.'}), 403

    patient = Patient.query.get_or_404(patient_id)

    # Doctors see only their own appointments with this patient
    q = Appointment.query.filter_by(patient_id=patient_id)
    if role == 'doctor':
        user   = User.query.get(user_id)
        doctor = user.doctor_profile
        if not doctor:
            return jsonify({'error': 'Doctor profile not found.'}), 404
        q = q.filter_by(doctor_id=doctor.id)

    appts = q.order_by(Appointment.date.desc()).all()

    return jsonify({
        'patient': {
            'id':             patient.id,
            'full_name':      patient.full_name,
            'gender':         patient.gender,
            'blood_group':    patient.blood_group,
            'date_of_birth':  str(patient.date_of_birth) if patient.date_of_birth else None,
            'contact_number': patient.contact_number,
        },
        'history':       [_serialize_appointment(a) for a in appts],
        'total_visits':  len(appts),
        'completed':     sum(1 for a in appts if a.status == 'Completed'),
        'cancelled':     sum(1 for a in appts if a.status == 'Cancelled'),
    }), 200


# ═══════════════════════════════════════════════
# HISTORY — ADMIN full report for any patient
# GET /api/appointments/history/admin/<patient_id>
# Admin only — all doctors, all statuses
# ═══════════════════════════════════════════════
@appt_bp.route('/history/admin/<int:patient_id>', methods=['GET'])
@admin_required
def admin_patient_full_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appts   = Appointment.query.filter_by(patient_id=patient_id)\
                               .order_by(Appointment.date.desc()).all()

    # Group by doctor
    by_doctor = {}
    for a in appts:
        key = a.doctor.full_name
        by_doctor.setdefault(key, []).append(_serialize_appointment(a))

    return jsonify({
        'patient': {
            'id':             patient.id,
            'full_name':      patient.full_name,
            'gender':         patient.gender,
            'blood_group':    patient.blood_group,
            'date_of_birth':  str(patient.date_of_birth) if patient.date_of_birth else None,
            'contact_number': patient.contact_number,
            'email':          patient.user.email,
        },
        'summary': {
            'total':     len(appts),
            'booked':    sum(1 for a in appts if a.status == 'Booked'),
            'completed': sum(1 for a in appts if a.status == 'Completed'),
            'cancelled': sum(1 for a in appts if a.status == 'Cancelled'),
        },
        'by_doctor': by_doctor,
        'all':       [_serialize_appointment(a) for a in appts],
    }), 200


# ═══════════════════════════════════════════════
# SINGLE APPOINTMENT DETAIL
# GET /api/appointments/<id>
# Admin sees all; Doctor sees own; Patient sees own
# ═══════════════════════════════════════════════
@appt_bp.route('/<int:appt_id>', methods=['GET'])
def appointment_detail(appt_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)

    appt = Appointment.query.get_or_404(appt_id)

    if role == 'patient':
        if not user.patient_profile or appt.patient_id != user.patient_profile.id:
            return jsonify({'error': 'Access denied.'}), 403
    elif role == 'doctor':
        if not user.doctor_profile or appt.doctor_id != user.doctor_profile.id:
            return jsonify({'error': 'Access denied.'}), 403
    # admin sees all

    return jsonify(_serialize_appointment(appt)), 200


# ═══════════════════════════════════════════════
# CONFLICT STATS (Admin dashboard helper)
# GET /api/appointments/stats
# Admin only
# ═══════════════════════════════════════════════
@appt_bp.route('/stats', methods=['GET'])
@admin_required
def appointment_stats():
    total     = Appointment.query.count()
    booked    = Appointment.query.filter_by(status='Booked').count()
    completed = Appointment.query.filter_by(status='Completed').count()
    cancelled = Appointment.query.filter_by(status='Cancelled').count()

    # Appointments per department
    from models import Department, Doctor
    dept_stats = []
    for dept in Department.query.all():
        doctor_ids = [d.id for d in dept.doctors.all()]
        count = Appointment.query.filter(
            Appointment.doctor_id.in_(doctor_ids)
        ).count() if doctor_ids else 0
        dept_stats.append({'department': dept.name, 'appointments': count})

    return jsonify({
        'total': total, 'booked': booked,
        'completed': completed, 'cancelled': cancelled,
        'by_department': dept_stats,
    }), 200
