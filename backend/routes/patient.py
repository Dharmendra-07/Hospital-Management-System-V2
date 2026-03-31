"""
backend/routes/patient.py  —  Patient routes with Redis caching
Cache strategy:
  GET /profile           TTL 1800 s
  GET /departments       TTL 86400 s  (very stable)
  GET /doctors           TTL 300 s    (search results)
  GET /doctors/<id>      TTL 60 s     (availability changes frequently)
  GET /appointments      TTL 60 s     (status updates are real-time)
  Writes always invalidate the relevant keys.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_
from models import (db, User, Patient, Doctor, Department,
                    Appointment, DoctorAvailability)
from middleware.rbac import patient_required
from extensions import cache
from utils.cache_keys import CK, Invalidate, TTL_SHORT, TTL_MEDIUM, TTL_LONG, TTL_DAY
from utils.cache_helpers import get_or_set
from datetime import date, timedelta
import json

patient_bp = Blueprint('patient', __name__)


def _current_patient():
    user_id = int(get_jwt_identity())
    return User.query.get_or_404(user_id).patient_profile


# ─────────────────────────────────────────────
# GET /api/patient/profile  (cached TTL_LONG)
# ─────────────────────────────────────────────
@patient_bp.route('/profile', methods=['GET'])
@patient_required
def get_profile():
    p = _current_patient()

    def _build():
        return {
            'id': p.id, 'full_name': p.full_name, 'gender': p.gender,
            'date_of_birth': str(p.date_of_birth) if p.date_of_birth else None,
            'blood_group': p.blood_group, 'contact_number': p.contact_number,
            'address': p.address, 'emergency_contact': p.emergency_contact,
            'email': p.user.email, 'username': p.user.username,
        }

    return jsonify(get_or_set(CK.patient_profile(p.id), _build, TTL_LONG)), 200


# ─────────────────────────────────────────────
# PUT /api/patient/profile
# ─────────────────────────────────────────────
@patient_bp.route('/profile', methods=['PUT'])
@patient_required
def update_profile():
    p    = _current_patient()
    data = request.get_json()

    for f in ['full_name', 'gender', 'date_of_birth', 'blood_group',
              'contact_number', 'address', 'emergency_contact']:
        if f in data:
            setattr(p, f, data[f] or None)

    if 'email' in data and data['email']:
        conflict = User.query.filter(User.email == data['email'].lower(),
                                     User.id != p.user_id).first()
        if conflict:
            return jsonify({'error': 'Email already in use.'}), 409
        p.user.email = data['email'].strip().lower()

    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400
        p.user.set_password(data['password'])

    db.session.commit()
    Invalidate.patient(cache, p.id)
    return jsonify({'message': 'Profile updated.'}), 200


# ─────────────────────────────────────────────
# GET /api/patient/departments  (cached TTL_DAY)
# ─────────────────────────────────────────────
@patient_bp.route('/departments', methods=['GET'])
@patient_required
def list_departments():
    def _build():
        return [{'id': d.id, 'name': d.name, 'description': d.description}
                for d in Department.query.all()]

    return jsonify(get_or_set(CK.DEPT_LIST, _build, TTL_DAY)), 200


# ─────────────────────────────────────────────
# GET /api/patient/doctors  (cached TTL_MEDIUM)
# ─────────────────────────────────────────────
@patient_bp.route('/doctors', methods=['GET'])
@patient_required
def list_doctors():
    q       = request.args.get('q', '').strip()
    spec    = request.args.get('specialization', '').strip()
    dept_id = request.args.get('department_id', type=int) or 0

    cache_key = CK.doctor_list(q, spec, dept_id)

    def _build():
        today = date.today()
        query = Doctor.query.join(User).filter(User.is_active == True)
        if q:
            like  = f'%{q}%'
            query = query.filter(or_(Doctor.full_name.ilike(like),
                                     Doctor.specialization.ilike(like)))
        if spec:
            query = query.filter(Doctor.specialization.ilike(f'%{spec}%'))
        if dept_id:
            query = query.filter(Doctor.department_id == dept_id)

        result = []
        for d in query.all():
            free = DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == d.id,
                DoctorAvailability.date >= today,
                DoctorAvailability.date <= today + timedelta(days=7),
                DoctorAvailability.is_booked == False,
            ).count()
            result.append({
                'id': d.id, 'full_name': d.full_name,
                'specialization': d.specialization,
                'qualification': d.qualification,
                'experience_years': d.experience_years,
                'bio': d.bio,
                'department': d.department.name if d.department else None,
                'department_id': d.department_id,
                'available_slots': free,
            })
        return result

    return jsonify(get_or_set(cache_key, _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/patient/doctors/<id>  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@patient_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@patient_required
def doctor_detail(doctor_id):
    def _build():
        d     = Doctor.query.get_or_404(doctor_id)
        today = date.today()
        avail = []
        for i in range(7):
            day   = today + timedelta(days=i)
            slots = DoctorAvailability.query.filter_by(
                doctor_id=d.id, date=day).all()
            avail.append({
                'date': str(day),
                'slots': [{'id': s.id, 'slot': s.slot, 'is_booked': s.is_booked}
                          for s in slots],
            })
        return {
            'id': d.id, 'full_name': d.full_name,
            'specialization': d.specialization,
            'qualification': d.qualification,
            'experience_years': d.experience_years,
            'bio': d.bio, 'contact_number': d.contact_number,
            'department': d.department.name if d.department else None,
            'availability': avail,
        }

    return jsonify(get_or_set(CK.doctor_availability(doctor_id), _build, TTL_SHORT)), 200


# ─────────────────────────────────────────────
# POST /api/patient/appointments  (book)
# ─────────────────────────────────────────────
@patient_bp.route('/appointments', methods=['POST'])
@patient_required
def book_appointment():
    patient = _current_patient()
    data    = request.get_json()

    for f in ['doctor_id', 'date', 'time_slot']:
        if not data.get(f):
            return jsonify({'error': f'Missing: {f}'}), 400

    try:
        appt_date = date.fromisoformat(data['date'])
    except ValueError:
        return jsonify({'error': 'Invalid date. Use YYYY-MM-DD.'}), 400

    if appt_date < date.today():
        return jsonify({'error': 'Cannot book in the past.'}), 400

    doctor    = Doctor.query.get_or_404(data['doctor_id'])
    time_slot = data['time_slot']

    avail = DoctorAvailability.query.filter_by(
        doctor_id=doctor.id, date=appt_date,
        slot=time_slot, is_booked=False).first()
    if not avail:
        return jsonify({'error': 'Slot not available.'}), 409

    if Appointment.query.filter_by(
        doctor_id=doctor.id, date=appt_date,
        time_slot=time_slot, status='Booked').first():
        return jsonify({'error': 'Slot already booked.'}), 409

    if Appointment.query.filter_by(
        patient_id=patient.id, date=appt_date,
        time_slot=time_slot, status='Booked').first():
        return jsonify({'error': 'You already have an appointment at this time.'}), 409

    appt = Appointment(
        patient_id=patient.id, doctor_id=doctor.id,
        date=appt_date, time_slot=time_slot,
        visit_type=data.get('visit_type', 'In-person'),
        notes=data.get('notes', ''), status='Booked',
    )
    db.session.add(appt)
    avail.is_booked = True
    db.session.commit()

    # Bust availability cache so other patients see slot as taken immediately
    Invalidate.appointment(cache, doctor.id, patient.id)
    return jsonify({'message': 'Appointment booked!', 'appointment_id': appt.id}), 201


# ─────────────────────────────────────────────
# GET /api/patient/appointments  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@patient_bp.route('/appointments', methods=['GET'])
@patient_required
def list_appointments():
    patient = _current_patient()
    view    = request.args.get('view', 'upcoming')
    today   = date.today()

    def _build():
        q = Appointment.query.filter_by(patient_id=patient.id)
        if view == 'upcoming':
            q = q.filter(Appointment.date >= today, Appointment.status == 'Booked')
        elif view == 'past':
            q = q.filter(or_(Appointment.date < today,
                             Appointment.status.in_(['Completed', 'Cancelled'])))
        result = []
        for a in q.order_by(Appointment.date.asc()).all():
            entry = {
                'id': a.id, 'doctor_name': a.doctor.full_name,
                'doctor_id': a.doctor_id,
                'specialization': a.doctor.specialization,
                'department': a.doctor.department.name if a.doctor.department else None,
                'date': str(a.date), 'time_slot': a.time_slot,
                'visit_type': a.visit_type, 'status': a.status,
                'notes': a.notes, 'treatment': None,
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
            result.append(entry)
        return result

    return jsonify(
        get_or_set(CK.patient_appointments(patient.id, view), _build, TTL_SHORT)
    ), 200


# ─────────────────────────────────────────────
# DELETE /api/patient/appointments/<id>
# ─────────────────────────────────────────────
@patient_bp.route('/appointments/<int:appt_id>', methods=['DELETE'])
@patient_required
def cancel_appointment(appt_id):
    patient = _current_patient()
    appt    = Appointment.query.get_or_404(appt_id)

    if appt.patient_id != patient.id:
        return jsonify({'error': 'Access denied.'}), 403
    if appt.status != 'Booked':
        return jsonify({'error': f'Cannot cancel a {appt.status.lower()} appointment.'}), 400
    if appt.date < date.today():
        return jsonify({'error': 'Cannot cancel a past appointment.'}), 400

    avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot).first()
    if avail:
        avail.is_booked = False

    appt.status = 'Cancelled'
    db.session.commit()
    Invalidate.appointment(cache, appt.doctor_id, patient.id)
    return jsonify({'message': 'Appointment cancelled.'}), 200


# ─────────────────────────────────────────────
# PUT /api/patient/appointments/<id>/reschedule
# ─────────────────────────────────────────────
@patient_bp.route('/appointments/<int:appt_id>/reschedule', methods=['PUT'])
@patient_required
def reschedule_appointment(appt_id):
    patient = _current_patient()
    appt    = Appointment.query.get_or_404(appt_id)

    if appt.patient_id != patient.id:
        return jsonify({'error': 'Access denied.'}), 403
    if appt.status != 'Booked':
        return jsonify({'error': 'Only booked appointments can be rescheduled.'}), 400

    data = request.get_json()
    try:
        new_date = date.fromisoformat(data['date'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid or missing date.'}), 400

    if new_date < date.today():
        return jsonify({'error': 'Cannot reschedule to a past date.'}), 400

    new_slot = data.get('time_slot')
    if not new_slot:
        return jsonify({'error': 'time_slot is required.'}), 400
    if str(appt.date) == str(new_date) and appt.time_slot == new_slot:
        return jsonify({'error': 'New slot is same as current.'}), 400

    new_avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=new_date,
        slot=new_slot, is_booked=False).first()
    if not new_avail:
        return jsonify({'error': 'New slot not available.'}), 409

    if Appointment.query.filter_by(
        doctor_id=appt.doctor_id, date=new_date,
        time_slot=new_slot, status='Booked').first():
        return jsonify({'error': 'New slot already booked.'}), 409

    old_avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot).first()
    if old_avail:
        old_avail.is_booked = False

    appt.date      = new_date
    appt.time_slot = new_slot
    new_avail.is_booked = True
    db.session.commit()
    Invalidate.appointment(cache, appt.doctor_id, patient.id)
    return jsonify({'message': 'Appointment rescheduled.'}), 200
