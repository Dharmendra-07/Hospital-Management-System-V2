from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ─────────────────────────────────────────────
# USER (Base for Admin / Doctor / Patient)
# ─────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'user'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  nullable=False)   # 'admin' | 'doctor' | 'patient'
    is_active     = db.Column(db.Boolean, default=True)         # blacklist flag
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # back-references
    doctor_profile  = db.relationship('Doctor',  back_populates='user', uselist=False, cascade='all, delete-orphan')
    patient_profile = db.relationship('Patient', back_populates='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'


# ─────────────────────────────────────────────
# DEPARTMENT / SPECIALIZATION
# ─────────────────────────────────────────────
class Department(db.Model):
    __tablename__ = 'department'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

    # one department → many doctors
    doctors = db.relationship('Doctor', back_populates='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name}>'


# ─────────────────────────────────────────────
# DOCTOR
# ─────────────────────────────────────────────
class Doctor(db.Model):
    __tablename__ = 'doctor'

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    department_id     = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    full_name         = db.Column(db.String(120), nullable=False)
    specialization    = db.Column(db.String(120), nullable=False)
    qualification     = db.Column(db.String(200))           # e.g. MBBS, MD
    experience_years  = db.Column(db.Integer, default=0)
    contact_number    = db.Column(db.String(20))
    bio               = db.Column(db.Text)
    profile_image_url = db.Column(db.String(300))

    user              = db.relationship('User',       back_populates='doctor_profile')
    department        = db.relationship('Department', back_populates='doctors')
    appointments      = db.relationship('Appointment', back_populates='doctor', lazy='dynamic')
    availabilities    = db.relationship('DoctorAvailability', back_populates='doctor', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Doctor {self.full_name}>'


# ─────────────────────────────────────────────
# DOCTOR AVAILABILITY  (next 7 days slots)
# ─────────────────────────────────────────────
class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'

    id         = db.Column(db.Integer, primary_key=True)
    doctor_id  = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date       = db.Column(db.Date,    nullable=False)
    slot       = db.Column(db.String(50), nullable=False)   # e.g. '08:00-12:00' | '16:00-21:00'
    is_booked  = db.Column(db.Boolean, default=False)

    doctor     = db.relationship('Doctor', back_populates='availabilities')

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'date', 'slot', name='uq_doctor_date_slot'),
    )

    def __repr__(self):
        return f'<Availability Dr#{self.doctor_id} {self.date} {self.slot}>'


# ─────────────────────────────────────────────
# PATIENT
# ─────────────────────────────────────────────
class Patient(db.Model):
    __tablename__ = 'patient'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    full_name      = db.Column(db.String(120), nullable=False)
    date_of_birth  = db.Column(db.Date)
    gender         = db.Column(db.String(20))
    blood_group    = db.Column(db.String(10))
    contact_number = db.Column(db.String(20))
    address        = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))

    user         = db.relationship('User',        back_populates='patient_profile')
    appointments = db.relationship('Appointment', back_populates='patient', lazy='dynamic')

    def __repr__(self):
        return f'<Patient {self.full_name}>'


# ─────────────────────────────────────────────
# APPOINTMENT
# ─────────────────────────────────────────────
class Appointment(db.Model):
    __tablename__ = 'appointment'

    id           = db.Column(db.Integer, primary_key=True)
    patient_id   = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id    = db.Column(db.Integer, db.ForeignKey('doctor.id'),  nullable=False)
    date         = db.Column(db.Date,    nullable=False)
    time_slot    = db.Column(db.String(50), nullable=False)   # e.g. '08:00-12:00'
    visit_type   = db.Column(db.String(30), default='In-person')  # In-person | Online
    status       = db.Column(db.String(20), default='Booked')     # Booked | Completed | Cancelled
    notes        = db.Column(db.Text)                             # patient notes at booking
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient      = db.relationship('Patient', back_populates='appointments')
    doctor       = db.relationship('Doctor',  back_populates='appointments')
    treatment    = db.relationship('Treatment', back_populates='appointment', uselist=False, cascade='all, delete-orphan')

    # Prevent double-booking: same doctor, date, time_slot
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'date', 'time_slot', name='uq_doctor_date_timeslot'),
    )

    def __repr__(self):
        return f'<Appointment #{self.id} [{self.status}]>'


# ─────────────────────────────────────────────
# TREATMENT  (1:1 with Appointment)
# ─────────────────────────────────────────────
class Treatment(db.Model):
    __tablename__ = 'treatment'

    id             = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False)
    diagnosis      = db.Column(db.Text)
    prescription   = db.Column(db.Text)
    medicines      = db.Column(db.Text)      # JSON string: [{"name":"Med1","dosage":"1-0-1"}, ...]
    tests_done     = db.Column(db.Text)      # e.g. 'ECG, Blood Test'
    next_visit     = db.Column(db.Date)      # suggested follow-up date
    doctor_notes   = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointment    = db.relationship('Appointment', back_populates='treatment')

    def __repr__(self):
        return f'<Treatment for Appointment #{self.appointment_id}>'
