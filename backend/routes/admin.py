"""
backend/routes/admin.py
All admin-only API routes:
  - Dashboard stats
  - Doctor CRUD (add, update, delete/blacklist)
  - Patient management (view, blacklist)
  - Appointment management (view all, cancel)
  - Search (doctors & patients)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, func
from models import db, User, Doctor, Patient, Appointment, Treatment, Department, DoctorAvailability
from middleware.rbac import admin_required
from app import cache
import json

admin_bp = Blueprint('admin', __name__)


# ─────────────────────────────────────────────
# GET /api/admin/dashboard
# Returns counts: doctors, patients, appointments
# ─────────────────────────────────────────────
@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
@cache.cached(timeout=60, key_prefix='admin_dashboard')
def dashboard():
    total_doctors      = Doctor.query.join(User).filter(User.is_active == True).count()
    total_patients     = Patient.query.join(User).filter(User.is_active == True).count()
    total_appointments = Appointment.query.count()
    booked             = Appointment.query.filter_by(status='Booked').count()
    completed          = Appointment.query.filter_by(status='Completed').count()
    cancelled          = Appointment.query.filter_by(status='Cancelled').count()

    return jsonify({
        'total_doctors':      total_doctors,
        'total_patients':     total_patients,
        'total_appointments': total_appointments,
        'appointments_by_status': {
            'booked':    booked,
            'completed': completed,
            'cancelled': cancelled,
        }
    }), 200


# ─────────────────────────────────────────────
# DOCTORS — List all
# GET /api/admin/doctors
# ─────────────────────────────────────────────
@admin_bp.route('/doctors', methods=['GET'])
@admin_required
def list_doctors():
    doctors = Doctor.query.join(User).all()
    result  = []
    for d in doctors:
        result.append({
            'id':               d.id,
            'user_id':          d.user_id,
            'full_name':        d.full_name,
            'username':         d.user.username,
            'email':            d.user.email,
            'specialization':   d.specialization,
            'qualification':    d.qualification,
            'experience_years': d.experience_years,
            'contact_number':   d.contact_number,
            'bio':              d.bio,
            'department':       d.department.name if d.department else None,
            'department_id':    d.department_id,
            'is_active':        d.user.is_active,
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# DOCTORS — Add new doctor
# POST /api/admin/doctors
# ─────────────────────────────────────────────
@admin_bp.route('/doctors', methods=['POST'])
@admin_required
def add_doctor():
    data = request.get_json()

    required = ['username', 'email', 'password', 'full_name', 'specialization']
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken.'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered.'}), 409

    # Create user
    user = User(
        username  = data['username'].strip(),
        email     = data['email'].strip().lower(),
        role      = 'doctor',
        is_active = True,
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()

    # Create doctor profile
    doctor = Doctor(
        user_id           = user.id,
        full_name         = data['full_name'].strip(),
        specialization    = data['specialization'].strip(),
        qualification     = data.get('qualification', ''),
        experience_years  = data.get('experience_years', 0),
        contact_number    = data.get('contact_number', ''),
        bio               = data.get('bio', ''),
        department_id     = data.get('department_id'),
    )
    db.session.add(doctor)
    db.session.commit()
    cache.delete('admin_dashboard')

    return jsonify({'message': 'Doctor added successfully.', 'doctor_id': doctor.id}), 201


# ─────────────────────────────────────────────
# DOCTORS — Update
# PUT /api/admin/doctors/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>', methods=['PUT'])
@admin_required
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    data   = request.get_json()

    # Update doctor profile fields
    for field in ['full_name', 'specialization', 'qualification',
                  'experience_years', 'contact_number', 'bio', 'department_id']:
        if field in data:
            setattr(doctor, field, data[field])

    # Update user account fields
    if 'email' in data:
        existing = User.query.filter(
            User.email == data['email'], User.id != doctor.user_id
        ).first()
        if existing:
            return jsonify({'error': 'Email already in use.'}), 409
        doctor.user.email = data['email'].strip().lower()

    if 'password' in data and data['password']:
        doctor.user.set_password(data['password'])

    db.session.commit()
    cache.delete('admin_dashboard')
    return jsonify({'message': 'Doctor updated successfully.'}), 200


# ─────────────────────────────────────────────
# DOCTORS — Blacklist / Re-activate
# PATCH /api/admin/doctors/<id>/blacklist
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>/blacklist', methods=['PATCH'])
@admin_required
def blacklist_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.user.is_active = not doctor.user.is_active
    db.session.commit()
    cache.delete('admin_dashboard')
    status = 'activated' if doctor.user.is_active else 'blacklisted'
    return jsonify({'message': f'Doctor {status} successfully.', 'is_active': doctor.user.is_active}), 200


# ─────────────────────────────────────────────
# DOCTORS — Delete permanently
# DELETE /api/admin/doctors/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>', methods=['DELETE'])
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user   = doctor.user
    db.session.delete(user)   # cascades to doctor
    db.session.commit()
    cache.delete('admin_dashboard')
    return jsonify({'message': 'Doctor deleted permanently.'}), 200


# ─────────────────────────────────────────────
# PATIENTS — List all
# GET /api/admin/patients
# ─────────────────────────────────────────────
@admin_bp.route('/patients', methods=['GET'])
@admin_required
def list_patients():
    patients = Patient.query.join(User).all()
    result   = []
    for p in patients:
        result.append({
            'id':             p.id,
            'user_id':        p.user_id,
            'full_name':      p.full_name,
            'username':       p.user.username,
            'email':          p.user.email,
            'contact_number': p.contact_number,
            'gender':         p.gender,
            'blood_group':    p.blood_group,
            'is_active':      p.user.is_active,
            'total_appointments': p.appointments.count(),
        })
    return jsonify(result), 200


# ─────────────────────────────────────────────
# PATIENTS — Blacklist / Re-activate
# PATCH /api/admin/patients/<id>/blacklist
# ─────────────────────────────────────────────
@admin_bp.route('/patients/<int:patient_id>/blacklist', methods=['PATCH'])
@admin_required
def blacklist_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.user.is_active = not patient.user.is_active
    db.session.commit()
    cache.delete('admin_dashboard')
    status = 'activated' if patient.user.is_active else 'blacklisted'
    return jsonify({'message': f'Patient {status} successfully.', 'is_active': patient.user.is_active}), 200


# ─────────────────────────────────────────────
# PATIENTS — Update info
# PUT /api/admin/patients/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@admin_required
def update_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    data    = request.get_json()
    for field in ['full_name', 'contact_number', 'gender', 'blood_group', 'address']:
        if field in data:
            setattr(patient, field, data[field])
    if 'email' in data:
        patient.user.email = data['email'].strip().lower()
    db.session.commit()
    return jsonify({'message': 'Patient updated successfully.'}), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — List all (upcoming & past)
# GET /api/admin/appointments?status=Booked&page=1
# ─────────────────────────────────────────────
@admin_bp.route('/appointments', methods=['GET'])
@admin_required
def list_appointments():
    status  = request.args.get('status')
    page    = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    query = Appointment.query
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(Appointment.date.desc(), Appointment.time_slot.asc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    result    = []
    for a in paginated.items:
        result.append({
            'id':           a.id,
            'patient_name': a.patient.full_name,
            'patient_id':   a.patient_id,
            'doctor_name':  a.doctor.full_name,
            'doctor_id':    a.doctor_id,
            'department':   a.doctor.department.name if a.doctor.department else None,
            'date':         str(a.date),
            'time_slot':    a.time_slot,
            'visit_type':   a.visit_type,
            'status':       a.status,
            'has_treatment':a.treatment is not None,
        })
    return jsonify({
        'appointments': result,
        'total':        paginated.total,
        'pages':        paginated.pages,
        'page':         page,
    }), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — View single with treatment
# GET /api/admin/appointments/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/appointments/<int:appt_id>', methods=['GET'])
@admin_required
def view_appointment(appt_id):
    a = Appointment.query.get_or_404(appt_id)
    data = {
        'id':           a.id,
        'patient_name': a.patient.full_name,
        'doctor_name':  a.doctor.full_name,
        'date':         str(a.date),
        'time_slot':    a.time_slot,
        'status':       a.status,
        'notes':        a.notes,
        'treatment':    None,
    }
    if a.treatment:
        t = a.treatment
        data['treatment'] = {
            'diagnosis':    t.diagnosis,
            'prescription': t.prescription,
            'medicines':    json.loads(t.medicines) if t.medicines else [],
            'tests_done':   t.tests_done,
            'next_visit':   str(t.next_visit) if t.next_visit else None,
            'doctor_notes': t.doctor_notes,
        }
    return jsonify(data), 200


# ─────────────────────────────────────────────
# APPOINTMENTS — Cancel
# PATCH /api/admin/appointments/<id>/cancel
# ─────────────────────────────────────────────
@admin_bp.route('/appointments/<int:appt_id>/cancel', methods=['PATCH'])
@admin_required
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.status == 'Completed':
        return jsonify({'error': 'Cannot cancel a completed appointment.'}), 400
    appt.status = 'Cancelled'
    db.session.commit()
    return jsonify({'message': 'Appointment cancelled.'}), 200


# ─────────────────────────────────────────────
# SEARCH — doctors & patients
# GET /api/admin/search?q=john&type=doctor
# ─────────────────────────────────────────────
@admin_bp.route('/search', methods=['GET'])
@admin_required
def search():
    q         = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')   # doctor | patient | all
    if not q:
        return jsonify({'doctors': [], 'patients': []}), 200

    like = f'%{q}%'
    results = {'doctors': [], 'patients': []}

    if search_type in ('doctor', 'all'):
        doctors = Doctor.query.join(User).filter(
            or_(
                Doctor.full_name.ilike(like),
                Doctor.specialization.ilike(like),
                User.username.ilike(like),
                User.email.ilike(like),
            )
        ).all()
        results['doctors'] = [{
            'id':             d.id,
            'full_name':      d.full_name,
            'specialization': d.specialization,
            'department':     d.department.name if d.department else None,
            'is_active':      d.user.is_active,
        } for d in doctors]

    if search_type in ('patient', 'all'):
        patients = Patient.query.join(User).filter(
            or_(
                Patient.full_name.ilike(like),
                Patient.contact_number.ilike(like),
                User.username.ilike(like),
                User.email.ilike(like),
                User.id.cast(db.String).ilike(like),
            )
        ).all()
        results['patients'] = [{
            'id':             p.id,
            'full_name':      p.full_name,
            'contact_number': p.contact_number,
            'email':          p.user.email,
            'is_active':      p.user.is_active,
        } for p in patients]

    return jsonify(results), 200


# ─────────────────────────────────────────────
# DEPARTMENTS — List all
# GET /api/admin/departments
# ─────────────────────────────────────────────
@admin_bp.route('/departments', methods=['GET'])
@admin_required
def list_departments():
    from models import Department
    depts = Department.query.all()
    return jsonify([{
        'id':          d.id,
        'name':        d.name,
        'description': d.description,
        'doctor_count': d.doctors.count(),
    } for d in depts]), 200
