"""
backend/routes/patient.py
Patient-only API routes:
  - Profile view & update
  - Search / list doctors
  - Doctor detail + 7-day availability
  - Book / cancel / reschedule appointments
  - View upcoming & past appointments (with treatment)
  - List departments
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_
from models import (db, User, Patient, Doctor, Department,
                    Appointment, Treatment, DoctorAvailability)
from middleware.rbac import patient_required
from datetime import date, timedelta
import json

patient_bp = Blueprint('patient', __name__)


def get_current_patient():
    user_id = int(get_jwt_identity())
    user    = User.query.get_or_404(user_id)
    return user.patient_profile


# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────
@patient_bp.route('/profile', methods=['GET'])
@patient_required
def get_profile():
    p = get_current_patient()
    return jsonify({
        'id':                p.id,
        'full_name':         p.full_name,
        'gender':            p.gender,
        'date_of_birth':     str(p.date_of_birth) if p.date_of_birth else None,
        'blood_group':       p.blood_group,
        'contact_number':    p.contact_number,
        'address':           p.address,
        'emergency_contact': p.emergency_contact,
        'email':             p.user.email,
        'username':          p.user.username,
    }), 200


@patient_bp.route('/profile', methods=['PUT'])
@patient_required
def update_profile():
    p    = get_current_patient()
    data = request.get_json()

    for field in ['full_name', 'gender', 'date_of_birth', 'blood_group',
                  'contact_number', 'address', 'emergency_contact']:
        if field in data:
            setattr(p, field, data[field] or None)

    if 'email' in data and data['email']:
        conflict = User.query.filter(
            User.email == data['email'].lower(), User.id != p.user_id
        ).first()
        if conflict:
            return jsonify({'error': 'Email already in use.'}), 409
        p.user.email = data['email'].strip().lower()

    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters.'}), 400
        p.user.set_password(data['password'])

    db.session.commit()
    return jsonify({'message': 'Profile updated.'}), 200


# ─────────────────────────────────────────────
# DEPARTMENTS
# ─────────────────────────────────────────────
@patient_bp.route('/departments', methods=['GET'])
@patient_required
def list_departments():
    depts = Department.query.all()
    return jsonify([{
        'id':          d.id,
        'name':        d.name,
        'description': d.description,
    } for d in depts]), 200


# ─────────────────────────────────────────────
# DOCTORS — Search / list
# GET /api/patient/doctors?q=&specialization=&department_id=
# ─────────────────────────────────────────────
@patient_bp.route('/doctors', methods=['GET'])
@patient_required
def list_doctors():
    q             = request.args.get('q', '').strip()
    spec          = request.args.get('specialization', '').strip()
    dept_id       = request.args.get('department_id', type=int)
    today         = date.today()

    query = Doctor.query.join(User).filter(User.is_active == True)
    if q:
        like  = f'%{q}%'
        query = query.filter(or_(Doctor.full_name.ilike(like),
                                 Doctor.specialization.ilike(like)))
    if spec:
        query = query.filter(Doctor.specialization.ilike(f'%{spec}%'))
    if dept_id:
        query = query.filter(Doctor.department_id == dept_id)

    doctors = query.all()
    result  = []
    for d in doctors:
        free_slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == d.id,
            DoctorAvailability.date      >= today,
            DoctorAvailability.date      <= today + timedelta(days=7),
            DoctorAvailability.is_booked == False,
        ).count()
        result.append({
            'id':               d.id,
            'full_name':        d.full_name,
            'specialization':   d.specialization,
            'qualification':    d.qualification,
            'experience_years': d.experience_years,
            'bio':              d.bio,
            'department':       d.department.name if d.department else None,
            'department_id':    d.department_id,
            'available_slots':  free_slots,
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# DOCTORS — Detail + availability
# GET /api/patient/doctors/<id>
# ─────────────────────────────────────────────
@patient_bp.route('/doctors/<int:doctor_id>', methods=['GET'])
@patient_required
def doctor_detail(doctor_id):
    d     = Doctor.query.get_or_404(doctor_id)
    today = date.today()

    avail = []
    for i in range(7):
        day   = today + timedelta(days=i)
        slots = DoctorAvailability.query.filter_by(doctor_id=d.id, date=day).all()
        avail.append({
            'date':  str(day),
            'slots': [{'id': s.id, 'slot': s.slot, 'is_booked': s.is_booked}
                      for s in slots],
        })

    return jsonify({
        'id':               d.id,
        'full_name':        d.full_name,
        'specialization':   d.specialization,
        'qualification':    d.qualification,
        'experience_years': d.experience_years,
        'bio':              d.bio,
        'contact_number':   d.contact_number,
        'department':       d.department.name if d.department else None,
        'availability':     avail,
    }), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — Book
# POST /api/patient/appointments
# Body: { doctor_id, date, time_slot, visit_type, notes }
# ─────────────────────────────────────────────
@patient_bp.route('/appointments', methods=['POST'])
@patient_required
def book_appointment():
    patient = get_current_patient()
    data    = request.get_json()

    for f in ['doctor_id', 'date', 'time_slot']:
        if not data.get(f):
            return jsonify({'error': f'Missing field: {f}'}), 400

    try:
        appt_date = date.fromisoformat(data['date'])
    except ValueError:
        return jsonify({'error': 'Invalid date. Use YYYY-MM-DD.'}), 400

    if appt_date < date.today():
        return jsonify({'error': 'Cannot book in the past.'}), 400

    doctor    = Doctor.query.get_or_404(data['doctor_id'])
    time_slot = data['time_slot']

    # 1. Slot must exist and be free
    avail = DoctorAvailability.query.filter_by(
        doctor_id=doctor.id, date=appt_date,
        slot=time_slot, is_booked=False
    ).first()
    if not avail:
        return jsonify({'error': 'Slot not available. Choose another.'}), 409

    # 2. No duplicate appointment for doctor
    if Appointment.query.filter_by(
        doctor_id=doctor.id, date=appt_date,
        time_slot=time_slot, status='Booked'
    ).first():
        return jsonify({'error': 'Slot already booked.'}), 409

    # 3. Patient not double-booked at same time
    if Appointment.query.filter_by(
        patient_id=patient.id, date=appt_date,
        time_slot=time_slot, status='Booked'
    ).first():
        return jsonify({'error': 'You already have an appointment at this time.'}), 409

    appt = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        date=appt_date,
        time_slot=time_slot,
        visit_type=data.get('visit_type', 'In-person'),
        notes=data.get('notes', ''),
        status='Booked',
    )
    db.session.add(appt)
    avail.is_booked = True
    db.session.commit()

    return jsonify({'message': 'Appointment booked!', 'appointment_id': appt.id}), 201


# ─────────────────────────────────────────────
# APPOINTMENTS — List
# GET /api/patient/appointments?view=upcoming|past|all
# ─────────────────────────────────────────────
@patient_bp.route('/appointments', methods=['GET'])
@patient_required
def list_appointments():
    patient = get_current_patient()
    view    = request.args.get('view', 'upcoming')
    today   = date.today()

    query = Appointment.query.filter_by(patient_id=patient.id)
    if view == 'upcoming':
        query = query.filter(Appointment.date >= today, Appointment.status == 'Booked')
    elif view == 'past':
        query = query.filter(
            or_(Appointment.date < today,
                Appointment.status.in_(['Completed', 'Cancelled']))
        )
    appts  = query.order_by(Appointment.date.asc()).all()
    result = []

    for a in appts:
        entry = {
            'id':             a.id,
            'doctor_name':    a.doctor.full_name,
            'doctor_id':      a.doctor_id,
            'specialization': a.doctor.specialization,
            'department':     a.doctor.department.name if a.doctor.department else None,
            'date':           str(a.date),
            'time_slot':      a.time_slot,
            'visit_type':     a.visit_type,
            'status':         a.status,
            'notes':          a.notes,
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
        result.append(entry)

    return jsonify(result), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — Cancel
# DELETE /api/patient/appointments/<id>
# ─────────────────────────────────────────────
@patient_bp.route('/appointments/<int:appt_id>', methods=['DELETE'])
@patient_required
def cancel_appointment(appt_id):
    patient = get_current_patient()
    appt    = Appointment.query.get_or_404(appt_id)

    if appt.patient_id != patient.id:
        return jsonify({'error': 'Access denied.'}), 403
    if appt.status != 'Booked':
        return jsonify({'error': f'Cannot cancel a {appt.status.lower()} appointment.'}), 400
    if appt.date < date.today():
        return jsonify({'error': 'Cannot cancel a past appointment.'}), 400

    avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot
    ).first()
    if avail:
        avail.is_booked = False

    appt.status = 'Cancelled'
    db.session.commit()
    return jsonify({'message': 'Appointment cancelled.'}), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — Reschedule
# PUT /api/patient/appointments/<id>/reschedule
# Body: { date, time_slot }
# ─────────────────────────────────────────────
@patient_bp.route('/appointments/<int:appt_id>/reschedule', methods=['PUT'])
@patient_required
def reschedule_appointment(appt_id):
    patient = get_current_patient()
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
        slot=new_slot, is_booked=False
    ).first()
    if not new_avail:
        return jsonify({'error': 'New slot not available.'}), 409

    if Appointment.query.filter_by(
        doctor_id=appt.doctor_id, date=new_date,
        time_slot=new_slot, status='Booked'
    ).first():
        return jsonify({'error': 'New slot already booked.'}), 409

    # Free old slot
    old_avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot
    ).first()
    if old_avail:
        old_avail.is_booked = False

    appt.date      = new_date
    appt.time_slot = new_slot
    new_avail.is_booked = True
    db.session.commit()
    return jsonify({'message': 'Appointment rescheduled.'}), 200
