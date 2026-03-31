"""
backend/routes/doctor.py  —  Doctor routes with Redis caching
Cache strategy:
  GET /dashboard        TTL 60 s   (today's appointments change during the day)
  GET /availability     TTL 60 s   (slots can be booked by patients any time)
  GET /patients         TTL 300 s
  GET /profile          TTL 1800 s
  All writes invalidate related keys immediately.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import db, User, Doctor, Patient, Appointment, Treatment, DoctorAvailability
from middleware.rbac import doctor_required
from extensions import cache
from utils.cache_keys import CK, Invalidate, TTL_SHORT, TTL_MEDIUM, TTL_LONG
from utils.cache_helpers import get_or_set
from datetime import date, timedelta
import json

doctor_bp = Blueprint('doctor', __name__)


def _current_doctor():
    user_id = int(get_jwt_identity())
    return User.query.get_or_404(user_id).doctor_profile


# ─────────────────────────────────────────────
# GET /api/doctor/dashboard  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@doctor_bp.route('/dashboard', methods=['GET'])
@doctor_required
def dashboard():
    doctor = _current_doctor()

    def _build():
        today    = date.today()
        week_end = today + timedelta(days=7)

        def fmt(a):
            return {
                'id': a.id, 'patient_name': a.patient.full_name,
                'patient_id': a.patient_id, 'date': str(a.date),
                'time_slot': a.time_slot, 'visit_type': a.visit_type,
                'status': a.status, 'has_treatment': a.treatment is not None,
            }

        today_appts = Appointment.query.filter_by(
            doctor_id=doctor.id, status='Booked'
        ).filter(Appointment.date == today).order_by(Appointment.time_slot).all()

        week_appts = Appointment.query.filter_by(
            doctor_id=doctor.id, status='Booked'
        ).filter(Appointment.date > today,
                 Appointment.date <= week_end
        ).order_by(Appointment.date, Appointment.time_slot).all()

        total_patients = db.session.query(Appointment.patient_id).filter_by(
            doctor_id=doctor.id).distinct().count()

        return {
            'doctor': {
                'id': doctor.id, 'full_name': doctor.full_name,
                'specialization': doctor.specialization,
                'department': doctor.department.name if doctor.department else None,
            },
            'today_appointments': [fmt(a) for a in today_appts],
            'week_appointments':  [fmt(a) for a in week_appts],
            'stats': {
                'today_count': len(today_appts),
                'week_count':  len(week_appts),
                'total_patients': total_patients,
            },
        }

    return jsonify(get_or_set(CK.doctor_dashboard(doctor.id), _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# GET /api/doctor/appointments
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments', methods=['GET'])
@doctor_required
def list_appointments():
    doctor   = _current_doctor()
    view     = request.args.get('view', 'upcoming')
    status   = request.args.get('status', '')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 15))
    today    = date.today()

    q = Appointment.query.filter_by(doctor_id=doctor.id)
    if view == 'upcoming':
        q = q.filter(Appointment.date >= today)
    elif view == 'past':
        q = q.filter(Appointment.date < today)
    if status:
        q = q.filter_by(status=status)

    pg = q.order_by(Appointment.date.asc(),
                    Appointment.time_slot.asc()
                    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'appointments': [{
            'id': a.id, 'patient_name': a.patient.full_name,
            'patient_id': a.patient_id, 'date': str(a.date),
            'time_slot': a.time_slot, 'visit_type': a.visit_type,
            'status': a.status, 'notes': a.notes,
            'has_treatment': a.treatment is not None,
        } for a in pg.items],
        'total': pg.total, 'pages': pg.pages, 'page': page,
    }), 200


# ─────────────────────────────────────────────
# PATCH /api/doctor/appointments/<id>/status
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments/<int:appt_id>/status', methods=['PATCH'])
@doctor_required
def update_status(appt_id):
    doctor = _current_doctor()
    appt   = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        return jsonify({'error': 'Access denied.'}), 403

    new_status = request.get_json().get('status')
    if new_status not in ('Completed', 'Cancelled'):
        return jsonify({'error': 'Status must be Completed or Cancelled.'}), 400
    if appt.status == 'Completed':
        return jsonify({'error': 'Already completed.'}), 400

    if new_status == 'Cancelled':
        avail = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id, date=appt.date, slot=appt.time_slot).first()
        if avail:
            avail.is_booked = False

    appt.status = new_status
    db.session.commit()
    Invalidate.appointment(cache, doctor.id, appt.patient_id)
    return jsonify({'message': f'Marked {new_status}.', 'status': new_status}), 200


# ─────────────────────────────────────────────
# POST /api/doctor/appointments/<id>/treatment
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments/<int:appt_id>/treatment', methods=['POST'])
@doctor_required
def save_treatment(appt_id):
    doctor = _current_doctor()
    appt   = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doctor.id:
        return jsonify({'error': 'Access denied.'}), 403

    data      = request.get_json()
    treatment = appt.treatment or Treatment(appointment_id=appt.id)
    treatment.diagnosis    = data.get('diagnosis', '')
    treatment.prescription = data.get('prescription', '')
    treatment.medicines    = json.dumps(data.get('medicines', []))
    treatment.tests_done   = data.get('tests_done', '')
    treatment.doctor_notes = data.get('doctor_notes', '')
    treatment.next_visit   = data.get('next_visit') or None
    if not appt.treatment:
        db.session.add(treatment)

    appt.status = 'Completed'
    db.session.commit()
    Invalidate.appointment(cache, doctor.id, appt.patient_id)
    return jsonify({'message': 'Treatment saved.'}), 200


# ─────────────────────────────────────────────
# GET /api/doctor/patients  (cached TTL_MEDIUM)
# ─────────────────────────────────────────────
@doctor_bp.route('/patients', methods=['GET'])
@doctor_required
def list_patients():
    doctor = _current_doctor()

    def _build():
        subq     = db.session.query(Appointment.patient_id).filter_by(
            doctor_id=doctor.id).distinct().subquery()
        patients = Patient.query.filter(Patient.id.in_(subq)).all()
        result   = []
        for p in patients:
            last = Appointment.query.filter_by(
                doctor_id=doctor.id, patient_id=p.id
            ).order_by(Appointment.date.desc()).first()
            result.append({
                'id': p.id, 'full_name': p.full_name,
                'gender': p.gender, 'blood_group': p.blood_group,
                'contact_number': p.contact_number,
                'last_visit': str(last.date) if last else None,
                'last_status': last.status if last else None,
                'total_visits': Appointment.query.filter_by(
                    doctor_id=doctor.id, patient_id=p.id).count(),
            })
        return result

    return jsonify(get_or_set(CK.doctor_patients(doctor.id), _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/doctor/patients/<id>/history
# ─────────────────────────────────────────────
@doctor_bp.route('/patients/<int:patient_id>/history', methods=['GET'])
@doctor_required
def patient_history(patient_id):
    doctor  = _current_doctor()
    patient = Patient.query.get_or_404(patient_id)

    def _build():
        appts   = Appointment.query.filter_by(
            doctor_id=doctor.id, patient_id=patient_id
        ).order_by(Appointment.date.desc()).all()
        history = []
        for a in appts:
            entry = {
                'appointment_id': a.id, 'date': str(a.date),
                'time_slot': a.time_slot, 'visit_type': a.visit_type,
                'status': a.status, 'treatment': None,
            }
            if a.treatment:
                t = a.treatment
                entry['treatment'] = {
                    'diagnosis': t.diagnosis, 'prescription': t.prescription,
                    'medicines': json.loads(t.medicines) if t.medicines else [],
                    'tests_done': t.tests_done,
                    'next_visit': str(t.next_visit) if t.next_visit else None,
                    'doctor_notes': t.doctor_notes,
                }
            history.append(entry)
        return {
            'patient': {
                'id': patient.id, 'full_name': patient.full_name,
                'gender': patient.gender, 'blood_group': patient.blood_group,
                'date_of_birth': str(patient.date_of_birth) if patient.date_of_birth else None,
                'contact_number': patient.contact_number,
            },
            'doctor': {
                'id': doctor.id, 'full_name': doctor.full_name,
                'department': doctor.department.name if doctor.department else None,
            },
            'history': history,
        }

    key  = f'doctor:patient_history:{doctor.id}:{patient_id}'
    return jsonify(get_or_set(key, _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/doctor/availability  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@doctor_bp.route('/availability', methods=['GET'])
@doctor_required
def get_availability():
    doctor = _current_doctor()

    def _build():
        today  = date.today()
        result = []
        for i in range(7):
            d     = today + timedelta(days=i)
            slots = DoctorAvailability.query.filter_by(
                doctor_id=doctor.id, date=d).all()
            result.append({
                'date': str(d),
                'slots': [{'id': s.id, 'slot': s.slot, 'is_booked': s.is_booked}
                          for s in slots],
            })
        return result

    return jsonify(get_or_set(CK.doctor_availability(doctor.id), _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# POST /api/doctor/availability
# ─────────────────────────────────────────────
@doctor_bp.route('/availability', methods=['POST'])
@doctor_required
def set_availability():
    doctor   = _current_doctor()
    data     = request.get_json()
    today    = date.today()
    max_date = today + timedelta(days=7)

    for entry in data:
        try:
            slot_date = date.fromisoformat(entry['date'])
        except (KeyError, ValueError):
            continue
        if not (today <= slot_date <= max_date):
            continue

        DoctorAvailability.query.filter_by(
            doctor_id=doctor.id, date=slot_date, is_booked=False
        ).delete()

        for slot_str in entry.get('slots', []):
            if not DoctorAvailability.query.filter_by(
                doctor_id=doctor.id, date=slot_date,
                slot=slot_str, is_booked=True
            ).first():
                db.session.add(DoctorAvailability(
                    doctor_id=doctor.id, date=slot_date,
                    slot=slot_str, is_booked=False,
                ))

    db.session.commit()
    # Invalidate availability cache so patients see fresh slots immediately
    Invalidate.availability(cache, doctor.id)
    return jsonify({'message': 'Availability updated.'}), 200


# ─────────────────────────────────────────────
# GET /api/doctor/profile  (cached TTL_LONG)
# ─────────────────────────────────────────────
@doctor_bp.route('/profile', methods=['GET'])
@doctor_required
def get_profile():
    doctor = _current_doctor()

    def _build():
        return {
            'id': doctor.id, 'full_name': doctor.full_name,
            'specialization': doctor.specialization,
            'qualification': doctor.qualification,
            'experience_years': doctor.experience_years,
            'contact_number': doctor.contact_number,
            'bio': doctor.bio,
            'department': doctor.department.name if doctor.department else None,
            'email': doctor.user.email, 'username': doctor.user.username,
        }

    return jsonify(get_or_set(CK.doctor_profile(doctor.id), _build, TTL_LONG)), 200
