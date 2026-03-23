"""
backend/routes/doctor.py
Doctor-only API routes:
  - Dashboard (upcoming appointments today/week)
  - Assigned patients list
  - Mark appointment completed / cancelled
  - Enter / update treatment (diagnosis, prescription, notes)
  - Set availability for next 7 days
  - View full patient medical history
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from models import db, User, Doctor, Patient, Appointment, Treatment, DoctorAvailability
from middleware.rbac import doctor_required
from datetime import date, timedelta
import json

doctor_bp = Blueprint('doctor', __name__)


def get_current_doctor():
    """Returns Doctor object for the logged-in user."""
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    return user.doctor_profile


# ─────────────────────────────────────────────
# GET /api/doctor/dashboard
# ─────────────────────────────────────────────
@doctor_bp.route('/dashboard', methods=['GET'])
@doctor_required
def dashboard():
    doctor   = get_current_doctor()
    today    = date.today()
    week_end = today + timedelta(days=7)

    today_appts = Appointment.query.filter_by(
        doctor_id=doctor.id, status='Booked'
    ).filter(Appointment.date == today).order_by(Appointment.time_slot).all()

    week_appts = Appointment.query.filter_by(
        doctor_id=doctor.id, status='Booked'
    ).filter(
        Appointment.date > today,
        Appointment.date <= week_end
    ).order_by(Appointment.date, Appointment.time_slot).all()

    def fmt(a):
        return {
            'id':            a.id,
            'patient_name':  a.patient.full_name,
            'patient_id':    a.patient_id,
            'date':          str(a.date),
            'time_slot':     a.time_slot,
            'visit_type':    a.visit_type,
            'status':        a.status,
            'has_treatment': a.treatment is not None,
        }

    total_patients = db.session.query(Appointment.patient_id).filter_by(
        doctor_id=doctor.id
    ).distinct().count()

    return jsonify({
        'doctor': {
            'id':             doctor.id,
            'full_name':      doctor.full_name,
            'specialization': doctor.specialization,
            'department':     doctor.department.name if doctor.department else None,
        },
        'today_appointments': [fmt(a) for a in today_appts],
        'week_appointments':  [fmt(a) for a in week_appts],
        'stats': {
            'today_count':    len(today_appts),
            'week_count':     len(week_appts),
            'total_patients': total_patients,
        },
    }), 200


# ─────────────────────────────────────────────
# GET /api/doctor/appointments?view=upcoming|past|all&status=
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments', methods=['GET'])
@doctor_required
def list_appointments():
    doctor   = get_current_doctor()
    status   = request.args.get('status')
    view     = request.args.get('view', 'upcoming')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 15))
    today    = date.today()

    query = Appointment.query.filter_by(doctor_id=doctor.id)
    if view == 'upcoming':
        query = query.filter(Appointment.date >= today)
    elif view == 'past':
        query = query.filter(Appointment.date < today)
    if status:
        query = query.filter_by(status=status)

    query     = query.order_by(Appointment.date.asc(), Appointment.time_slot.asc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    result = [{
        'id':            a.id,
        'patient_name':  a.patient.full_name,
        'patient_id':    a.patient_id,
        'date':          str(a.date),
        'time_slot':     a.time_slot,
        'visit_type':    a.visit_type,
        'status':        a.status,
        'notes':         a.notes,
        'has_treatment': a.treatment is not None,
    } for a in paginated.items]

    return jsonify({
        'appointments': result,
        'total': paginated.total,
        'pages': paginated.pages,
        'page':  page,
    }), 200


# ─────────────────────────────────────────────
# PATCH /api/doctor/appointments/<id>/status
# Mark Completed or Cancelled
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments/<int:appt_id>/status', methods=['PATCH'])
@doctor_required
def update_status(appt_id):
    doctor = get_current_doctor()
    appt   = Appointment.query.get_or_404(appt_id)

    if appt.doctor_id != doctor.id:
        return jsonify({'error': 'Access denied.'}), 403

    new_status = request.get_json().get('status')
    if new_status not in ('Completed', 'Cancelled'):
        return jsonify({'error': 'Status must be Completed or Cancelled.'}), 400
    if appt.status == 'Completed':
        return jsonify({'error': 'Already completed.'}), 400

    appt.status = new_status
    db.session.commit()
    return jsonify({'message': f'Marked as {new_status}.', 'status': new_status}), 200


# ─────────────────────────────────────────────
# POST /api/doctor/appointments/<id>/treatment
# Add / update treatment record
# ─────────────────────────────────────────────
@doctor_bp.route('/appointments/<int:appt_id>/treatment', methods=['POST'])
@doctor_required
def save_treatment(appt_id):
    doctor = get_current_doctor()
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
    return jsonify({'message': 'Treatment saved.'}), 200


# ─────────────────────────────────────────────
# GET /api/doctor/patients
# All unique patients assigned to this doctor
# ─────────────────────────────────────────────
@doctor_bp.route('/patients', methods=['GET'])
@doctor_required
def list_patients():
    doctor  = get_current_doctor()
    subq    = db.session.query(Appointment.patient_id).filter_by(
        doctor_id=doctor.id
    ).distinct().subquery()
    patients = Patient.query.filter(Patient.id.in_(subq)).all()

    result = []
    for p in patients:
        last_appt = Appointment.query.filter_by(
            doctor_id=doctor.id, patient_id=p.id
        ).order_by(Appointment.date.desc()).first()
        result.append({
            'id':             p.id,
            'full_name':      p.full_name,
            'gender':         p.gender,
            'blood_group':    p.blood_group,
            'contact_number': p.contact_number,
            'last_visit':     str(last_appt.date) if last_appt else None,
            'last_status':    last_appt.status if last_appt else None,
            'total_visits':   Appointment.query.filter_by(
                                  doctor_id=doctor.id, patient_id=p.id).count(),
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# GET /api/doctor/patients/<id>/history
# Full treatment history of a patient
# ─────────────────────────────────────────────
@doctor_bp.route('/patients/<int:patient_id>/history', methods=['GET'])
@doctor_required
def patient_history(patient_id):
    doctor  = get_current_doctor()
    patient = Patient.query.get_or_404(patient_id)

    appts = Appointment.query.filter_by(
        doctor_id=doctor.id, patient_id=patient_id
    ).order_by(Appointment.date.desc()).all()

    history = []
    for a in appts:
        entry = {
            'appointment_id': a.id,
            'date':           str(a.date),
            'time_slot':      a.time_slot,
            'visit_type':     a.visit_type,
            'status':         a.status,
            'treatment':      None,
        }
        if a.treatment:
            t = a.treatment
            entry['treatment'] = {
                'diagnosis':    t.diagnosis,
                'prescription': t.prescription,
                'medicines':    json.loads(t.medicines) if t.medicines else [],
                'tests_done':   t.tests_done,
                'next_visit':   str(t.next_visit) if t.next_visit else None,
                'doctor_notes': t.doctor_notes,
            }
        history.append(entry)

    return jsonify({
        'patient': {
            'id':             patient.id,
            'full_name':      patient.full_name,
            'gender':         patient.gender,
            'blood_group':    patient.blood_group,
            'date_of_birth':  str(patient.date_of_birth) if patient.date_of_birth else None,
            'contact_number': patient.contact_number,
        },
        'doctor': {
            'id':         doctor.id,
            'full_name':  doctor.full_name,
            'department': doctor.department.name if doctor.department else None,
        },
        'history': history,
    }), 200


# ─────────────────────────────────────────────
# GET /api/doctor/availability
# ─────────────────────────────────────────────
@doctor_bp.route('/availability', methods=['GET'])
@doctor_required
def get_availability():
    doctor = get_current_doctor()
    today  = date.today()
    result = []
    for i in range(7):
        d     = today + timedelta(days=i)
        slots = DoctorAvailability.query.filter_by(doctor_id=doctor.id, date=d).all()
        result.append({
            'date':  str(d),
            'slots': [{'id': s.id, 'slot': s.slot, 'is_booked': s.is_booked} for s in slots],
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# POST /api/doctor/availability
# Body: [{ "date": "YYYY-MM-DD", "slots": ["08:00-12:00", "16:00-21:00"] }]
# ─────────────────────────────────────────────
@doctor_bp.route('/availability', methods=['POST'])
@doctor_required
def set_availability():
    doctor   = get_current_doctor()
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

        # Delete only unbooked slots for that day
        DoctorAvailability.query.filter_by(
            doctor_id=doctor.id, date=slot_date, is_booked=False
        ).delete()

        for slot_str in entry.get('slots', []):
            booked_exists = DoctorAvailability.query.filter_by(
                doctor_id=doctor.id, date=slot_date, slot=slot_str, is_booked=True
            ).first()
            if not booked_exists:
                db.session.add(DoctorAvailability(
                    doctor_id=doctor.id,
                    date=slot_date,
                    slot=slot_str,
                    is_booked=False,
                ))

    db.session.commit()
    return jsonify({'message': 'Availability updated.'}), 200


# ─────────────────────────────────────────────
# GET /api/doctor/profile
# ─────────────────────────────────────────────
@doctor_bp.route('/profile', methods=['GET'])
@doctor_required
def get_profile():
    doctor = get_current_doctor()
    return jsonify({
        'id':               doctor.id,
        'full_name':        doctor.full_name,
        'specialization':   doctor.specialization,
        'qualification':    doctor.qualification,
        'experience_years': doctor.experience_years,
        'contact_number':   doctor.contact_number,
        'bio':              doctor.bio,
        'department':       doctor.department.name if doctor.department else None,
        'email':            doctor.user.email,
        'username':         doctor.user.username,
    }), 200
