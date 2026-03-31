"""
backend/tasks/exports.py
User-Triggered Async Job — Patient Treatment History CSV Export.

Flow:
  1. Patient clicks "Export as CSV" on their dashboard.
  2. Frontend calls POST /api/patient/export  → returns task_id immediately.
  3. Celery worker runs generate_csv_export() in background.
  4. On completion, sends email with CSV attachment to patient.
  5. Frontend polls GET /api/patient/export/<task_id>/status → shows result.
"""

import csv
import io
import json
import logging
from datetime import datetime

from celery_worker import celery
from models import Patient, Appointment

logger = logging.getLogger(__name__)


def _build_csv(patient: Patient) -> str:
    """Build full treatment CSV string for a patient."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'Visit #',
        'Date',
        'Time Slot',
        'Visit Type',
        'Status',
        'Doctor Name',
        'Specialization',
        'Department',
        'Diagnosis',
        'Prescription',
        'Medicines',
        'Tests Done',
        'Next Visit',
        'Doctor Notes',
    ])

    appointments = Appointment.query.filter_by(
        patient_id=patient.id
    ).order_by(Appointment.date.desc()).all()

    for idx, a in enumerate(appointments, 1):
        medicines_str = ''
        diagnosis     = ''
        prescription  = ''
        tests_done    = ''
        next_visit    = ''
        doctor_notes  = ''

        if a.treatment:
            t             = a.treatment
            diagnosis     = t.diagnosis    or ''
            prescription  = t.prescription or ''
            tests_done    = t.tests_done   or ''
            next_visit    = str(t.next_visit) if t.next_visit else ''
            doctor_notes  = t.doctor_notes or ''

            if t.medicines:
                try:
                    meds          = json.loads(t.medicines)
                    medicines_str = '; '.join(
                        f"{m.get('name','')} ({m.get('dosage','')})"
                        for m in meds if m.get('name')
                    )
                except Exception:
                    medicines_str = t.medicines

        writer.writerow([
            idx,
            str(a.date),
            a.time_slot,
            a.visit_type,
            a.status,
            a.doctor.full_name,
            a.doctor.specialization,
            a.doctor.department.name if a.doctor.department else '',
            diagnosis,
            prescription,
            medicines_str,
            tests_done,
            next_visit,
            doctor_notes,
        ])

    return output.getvalue()


def _send_csv_email(patient_email: str, patient_name: str,
                    csv_content: str):
    """Email the CSV as an attachment."""
    from flask_mail import Message
    from flask import current_app
    from extensions import mail

    filename = (
        f"treatment_history_{patient_name.replace(' ', '_')}_"
        f"{datetime.utcnow().strftime('%Y%m%d')}.csv"
    )
    msg = Message(
        subject    = '📋 Your Treatment History Export — HMS',
        recipients = [patient_email],
        body       = (
            f"Dear {patient_name},\n\n"
            "Your treatment history CSV export is ready.\n"
            "Please find it attached to this email.\n\n"
            "Stay healthy,\nHMS Team"
        ),
        sender     = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@hms.com'),
    )
    msg.attach(
        filename    = filename,
        content_type= 'text/csv',
        data        = csv_content.encode('utf-8'),
    )
    mail.send(msg)
    return filename


# ── Celery Task ─────────────────────────────────

@celery.task(name='tasks.exports.generate_csv_export',
             bind=True, max_retries=2, default_retry_delay=60,
             track_started=True)
def generate_csv_export(self, patient_id: int):
    """
    User-triggered async task.
    Generates treatment history CSV and emails it to the patient.

    Returns:
        { patient_name, filename, rows, completed_at }
    """
    self.update_state(state='PROGRESS',
                      meta={'status': 'Building CSV…', 'progress': 10})

    patient = Patient.query.get(patient_id)
    if not patient:
        raise ValueError(f'Patient {patient_id} not found.')

    self.update_state(state='PROGRESS',
                      meta={'status': 'Fetching appointments…', 'progress': 40})

    csv_content = _build_csv(patient)
    row_count   = csv_content.count('\n') - 1   # exclude header

    self.update_state(state='PROGRESS',
                      meta={'status': 'Sending email…', 'progress': 75})

    try:
        filename = _send_csv_email(
            patient_email = patient.user.email,
            patient_name  = patient.full_name,
            csv_content   = csv_content,
        )
        logger.info(f"[CSV Export] Sent to {patient.user.email} — {row_count} rows.")
    except Exception as e:
        logger.error(f"[CSV Export] Email failed for patient {patient_id}: {e}")
        raise self.retry(exc=e)

    return {
        'patient_name': patient.full_name,
        'email':        patient.user.email,
        'filename':     filename,
        'rows':         row_count,
        'completed_at': datetime.utcnow().isoformat(),
    }
