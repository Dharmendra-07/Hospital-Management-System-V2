"""
backend/routes/admin.py  —  Admin routes with Redis caching
Cache strategy:
  GET  /dashboard          TTL 60 s   (frequent reads, low data change)
  GET  /doctors            TTL 300 s
  GET  /patients           TTL 300 s
  GET  /appointments       TTL 60 s   (status changes frequently)
  GET  /departments        TTL 1800 s (rarely changes)
  Writes always invalidate the relevant cache keys.
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from models import db, User, Doctor, Patient, Appointment, Treatment, Department, DoctorAvailability
from middleware.rbac import admin_required
from extensions import cache
from utils.cache_keys import CK, Invalidate, TTL_SHORT, TTL_MEDIUM, TTL_LONG
from utils.cache_helpers import get_or_set
import json

admin_bp = Blueprint('admin', __name__)


# ── helpers ────────────────────────────────────

def _fmt_doctor(d):
    return {
        'id': d.id, 'user_id': d.user_id,
        'full_name': d.full_name, 'username': d.user.username,
        'email': d.user.email, 'specialization': d.specialization,
        'qualification': d.qualification, 'experience_years': d.experience_years,
        'contact_number': d.contact_number, 'bio': d.bio,
        'department': d.department.name if d.department else None,
        'department_id': d.department_id, 'is_active': d.user.is_active,
    }

def _fmt_patient(p):
    return {
        'id': p.id, 'user_id': p.user_id,
        'full_name': p.full_name, 'username': p.user.username,
        'email': p.user.email, 'contact_number': p.contact_number,
        'gender': p.gender, 'blood_group': p.blood_group,
        'is_active': p.user.is_active,
        'total_appointments': p.appointments.count(),
    }

def _fmt_appt(a):
    return {
        'id': a.id, 'patient_name': a.patient.full_name,
        'patient_id': a.patient_id, 'doctor_name': a.doctor.full_name,
        'doctor_id': a.doctor_id,
        'department': a.doctor.department.name if a.doctor.department else None,
        'date': str(a.date), 'time_slot': a.time_slot,
        'visit_type': a.visit_type, 'status': a.status,
        'has_treatment': a.treatment is not None,
    }


# ─────────────────────────────────────────────
# GET /api/admin/dashboard  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    def _build():
        booked    = Appointment.query.filter_by(status='Booked').count()
        completed = Appointment.query.filter_by(status='Completed').count()
        cancelled = Appointment.query.filter_by(status='Cancelled').count()
        return {
            'total_doctors':      Doctor.query.join(User).filter(User.is_active == True).count(),
            'total_patients':     Patient.query.join(User).filter(User.is_active == True).count(),
            'total_appointments': Appointment.query.count(),
            'appointments_by_status': {
                'booked': booked, 'completed': completed, 'cancelled': cancelled,
            },
        }

    data = get_or_set(CK.ADMIN_DASHBOARD, _build, TTL_SHORT)
    return jsonify(data), 200


# ─────────────────────────────────────────────
# GET /api/admin/doctors  (cached TTL_MEDIUM)
# ─────────────────────────────────────────────
@admin_bp.route('/doctors', methods=['GET'])
@admin_required
def list_doctors():
    data = get_or_set(
        CK.ADMIN_DOCTOR_LIST,
        lambda: [_fmt_doctor(d) for d in Doctor.query.join(User).all()],
        TTL_MEDIUM,
    )
    return jsonify(data), 200


# ─────────────────────────────────────────────
# POST /api/admin/doctors
# ─────────────────────────────────────────────
@admin_bp.route('/doctors', methods=['POST'])
@admin_required
def add_doctor():
    data = request.get_json()
    required = ['username', 'email', 'password', 'full_name', 'specialization']
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing: {', '.join(missing)}"}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username taken.'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered.'}), 409

    user = User(username=data['username'].strip(),
                email=data['email'].strip().lower(),
                role='doctor', is_active=True)
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()

    doctor = Doctor(
        user_id=user.id, full_name=data['full_name'].strip(),
        specialization=data['specialization'].strip(),
        qualification=data.get('qualification', ''),
        experience_years=data.get('experience_years', 0),
        contact_number=data.get('contact_number', ''),
        bio=data.get('bio', ''), department_id=data.get('department_id'),
    )
    db.session.add(doctor)
    db.session.commit()
    Invalidate.admin_dashboard(cache)
    Invalidate.doctor(cache, doctor.id)
    return jsonify({'message': 'Doctor added.', 'doctor_id': doctor.id}), 201


# ─────────────────────────────────────────────
# PUT /api/admin/doctors/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>', methods=['PUT'])
@admin_required
def update_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    data   = request.get_json()
    for f in ['full_name', 'specialization', 'qualification',
              'experience_years', 'contact_number', 'bio', 'department_id']:
        if f in data:
            setattr(doctor, f, data[f])
    if 'email' in data:
        existing = User.query.filter(User.email == data['email'],
                                     User.id != doctor.user_id).first()
        if existing:
            return jsonify({'error': 'Email in use.'}), 409
        doctor.user.email = data['email'].strip().lower()
    if 'password' in data and data['password']:
        doctor.user.set_password(data['password'])
    db.session.commit()
    Invalidate.doctor(cache, doctor_id)
    return jsonify({'message': 'Doctor updated.'}), 200


# ─────────────────────────────────────────────
# PATCH /api/admin/doctors/<id>/blacklist
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>/blacklist', methods=['PATCH'])
@admin_required
def blacklist_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.user.is_active = not doctor.user.is_active
    db.session.commit()
    Invalidate.doctor(cache, doctor_id)
    Invalidate.admin_dashboard(cache)
    status = 'activated' if doctor.user.is_active else 'blacklisted'
    return jsonify({'message': f'Doctor {status}.', 'is_active': doctor.user.is_active}), 200


# ─────────────────────────────────────────────
# DELETE /api/admin/doctors/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/doctors/<int:doctor_id>', methods=['DELETE'])
@admin_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user   = doctor.user
    db.session.delete(user)
    db.session.commit()
    Invalidate.doctor(cache, doctor_id)
    Invalidate.admin_dashboard(cache)
    return jsonify({'message': 'Doctor deleted.'}), 200


# ─────────────────────────────────────────────
# GET /api/admin/patients  (cached TTL_MEDIUM)
# ─────────────────────────────────────────────
@admin_bp.route('/patients', methods=['GET'])
@admin_required
def list_patients():
    data = get_or_set(
        CK.ADMIN_PATIENT_LIST,
        lambda: [_fmt_patient(p) for p in Patient.query.join(User).all()],
        TTL_MEDIUM,
    )
    return jsonify(data), 200


# ─────────────────────────────────────────────
# PUT /api/admin/patients/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@admin_required
def update_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    data    = request.get_json()
    for f in ['full_name', 'contact_number', 'gender', 'blood_group', 'address']:
        if f in data:
            setattr(patient, f, data[f])
    if 'email' in data:
        patient.user.email = data['email'].strip().lower()
    db.session.commit()
    Invalidate.patient(cache, patient_id)
    return jsonify({'message': 'Patient updated.'}), 200


# ─────────────────────────────────────────────
# PATCH /api/admin/patients/<id>/blacklist
# ─────────────────────────────────────────────
@admin_bp.route('/patients/<int:patient_id>/blacklist', methods=['PATCH'])
@admin_required
def blacklist_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.user.is_active = not patient.user.is_active
    db.session.commit()
    Invalidate.patient(cache, patient_id)
    Invalidate.admin_dashboard(cache)
    status = 'activated' if patient.user.is_active else 'blacklisted'
    return jsonify({'message': f'Patient {status}.', 'is_active': patient.user.is_active}), 200


# ─────────────────────────────────────────────
# GET /api/admin/appointments  (cached TTL_SHORT)
# ─────────────────────────────────────────────
@admin_bp.route('/appointments', methods=['GET'])
@admin_required
def list_appointments():
    status   = request.args.get('status', '')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    def _build():
        q = Appointment.query
        if status:
            q = q.filter_by(status=status)
        q = q.order_by(Appointment.date.desc(), Appointment.time_slot.asc())
        pg = q.paginate(page=page, per_page=per_page, error_out=False)
        return {
            'appointments': [_fmt_appt(a) for a in pg.items],
            'total': pg.total, 'pages': pg.pages, 'page': page,
        }

    data = get_or_set(CK.admin_appt_page(status, page), _build, TTL_SHORT)
    return jsonify(data), 200


# ─────────────────────────────────────────────
# GET /api/admin/appointments/<id>
# ─────────────────────────────────────────────
@admin_bp.route('/appointments/<int:appt_id>', methods=['GET'])
@admin_required
def view_appointment(appt_id):
    a    = Appointment.query.get_or_404(appt_id)
    data = _fmt_appt(a)
    if a.treatment:
        t = a.treatment
        data['treatment'] = {
            'diagnosis': t.diagnosis, 'prescription': t.prescription,
            'medicines': json.loads(t.medicines) if t.medicines else [],
            'tests_done': t.tests_done,
            'next_visit': str(t.next_visit) if t.next_visit else None,
            'doctor_notes': t.doctor_notes,
        }
    return jsonify(data), 200


# ─────────────────────────────────────────────
# PATCH /api/admin/appointments/<id>/cancel
# ─────────────────────────────────────────────
@admin_bp.route('/appointments/<int:appt_id>/cancel', methods=['PATCH'])
@admin_required
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.status == 'Completed':
        return jsonify({'error': 'Cannot cancel a completed appointment.'}), 400
    appt.status = 'Cancelled'
    avail = DoctorAvailability.query.filter_by(
        doctor_id=appt.doctor_id, date=appt.date, slot=appt.time_slot).first()
    if avail:
        avail.is_booked = False
    db.session.commit()
    Invalidate.appointment(cache, appt.doctor_id, appt.patient_id)
    return jsonify({'message': 'Appointment cancelled.'}), 200


# ─────────────────────────────────────────────
# GET /api/admin/search  (no cache — dynamic)
# ─────────────────────────────────────────────
@admin_bp.route('/search', methods=['GET'])
@admin_required
def search():
    q           = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    if not q:
        return jsonify({'doctors': [], 'patients': []}), 200

    like    = f'%{q}%'
    results = {'doctors': [], 'patients': []}

    if search_type in ('doctor', 'all'):
        doctors = Doctor.query.join(User).filter(or_(
            Doctor.full_name.ilike(like), Doctor.specialization.ilike(like),
            User.username.ilike(like), User.email.ilike(like),
        )).all()
        results['doctors'] = [{
            'id': d.id, 'full_name': d.full_name,
            'specialization': d.specialization,
            'department': d.department.name if d.department else None,
            'is_active': d.user.is_active,
        } for d in doctors]

    if search_type in ('patient', 'all'):
        patients = Patient.query.join(User).filter(or_(
            Patient.full_name.ilike(like), Patient.contact_number.ilike(like),
            User.username.ilike(like), User.email.ilike(like),
            User.id.cast(db.String).ilike(like),
        )).all()
        results['patients'] = [{
            'id': p.id, 'full_name': p.full_name,
            'contact_number': p.contact_number,
            'email': p.user.email, 'is_active': p.user.is_active,
        } for p in patients]

    return jsonify(results), 200


# ─────────────────────────────────────────────
# GET /api/admin/departments  (cached TTL_LONG)
# ─────────────────────────────────────────────
@admin_bp.route('/departments', methods=['GET'])
@admin_required
def list_departments():
    def _build():
        return [{'id': d.id, 'name': d.name,
                 'description': d.description,
                 'doctor_count': d.doctors.count()}
                for d in Department.query.all()]

    return jsonify(get_or_set(CK.DEPT_LIST, _build, TTL_LONG)), 200
