"""
backend/tasks/reminders.py
Scheduled Job — Daily Appointment Reminders
  Runs every morning at 07:00 (configured in celery_worker.py beat schedule).
  For every patient with a Booked appointment today, sends a reminder email.

  Supports:
    • Email (Flask-Mail)        — default
    • Google Chat Webhook       — set GCHAT_WEBHOOK_URL in .env
    • SMS via Twilio            — set TWILIO_* vars in .env (optional)
"""

import os
import logging
from datetime import date, datetime
from celery_worker import celery
from flask_mail import Message
from models import Appointment, Patient, Doctor

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────

def _get_mail():
    """Lazy import to avoid circular imports."""
    from app import create_app
    from flask_mail import Mail
    app  = create_app()
    mail = Mail(app)
    return app, mail


def _send_email_reminder(patient_email: str, patient_name: str,
                          doctor_name: str, specialization: str,
                          appt_date: str, time_slot: str,
                          department: str) -> bool:
    """Send a single reminder email. Returns True on success."""
    from flask_mail import Message
    from flask import current_app
    from extensions import mail   # see extensions.py below

    subject = f"🏥 Appointment Reminder — {appt_date}"
    body    = f"""
Dear {patient_name},

This is a friendly reminder that you have a hospital appointment scheduled for TODAY.

  🩺 Doctor       : Dr. {doctor_name}
  🏥 Specialization : {specialization}
  🏢 Department   : {department or 'General'}
  📅 Date         : {appt_date}
  🕐 Time Slot    : {time_slot}

Please arrive 10–15 minutes early and carry any previous prescriptions or reports.

If you need to cancel or reschedule, please do so through the HMS portal.

Stay healthy,
HMS Team
    """.strip()

    try:
        msg = Message(
            subject    = subject,
            recipients = [patient_email],
            body       = body,
            sender     = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@hms.com'),
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Email send failed to {patient_email}: {e}")
        return False


def _send_gchat_reminder(webhook_url: str, patient_name: str,
                          doctor_name: str, time_slot: str,
                          appt_date: str) -> bool:
    """Post a Google Chat card reminder to a webhook."""
    import requests
    payload = {
        "text": (
            f"🏥 *Appointment Reminder*\n"
            f"Patient: *{patient_name}*\n"
            f"Doctor : Dr. *{doctor_name}*\n"
            f"Date   : {appt_date} at {time_slot}"
        )
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"GChat webhook failed: {e}")
        return False


# ── Celery Task ─────────────────────────────────

@celery.task(name='tasks.reminders.send_daily_reminders',
             bind=True, max_retries=3, default_retry_delay=300)
def send_daily_reminders(self):
    """
    Scheduled daily at 07:00.
    Finds all Booked appointments for today and sends reminders.
    """
    today         = date.today()
    gchat_webhook = os.getenv('GCHAT_WEBHOOK_URL', '')
    sent          = 0
    failed        = 0

    appointments = Appointment.query.filter_by(
        date=today, status='Booked'
    ).all()

    logger.info(f"[Reminders] {today} — found {len(appointments)} appointment(s).")

    for appt in appointments:
        patient = appt.patient
        doctor  = appt.doctor

        if not patient or not patient.user:
            continue

        patient_email = patient.user.email
        patient_name  = patient.full_name
        doctor_name   = doctor.full_name
        spec          = doctor.specialization
        dept          = doctor.department.name if doctor.department else 'General'
        time_slot     = appt.time_slot
        appt_date_str = str(today)

        # Email reminder
        ok = _send_email_reminder(
            patient_email, patient_name,
            doctor_name, spec,
            appt_date_str, time_slot, dept
        )
        if ok:
            sent += 1
            logger.info(f"  ✓ Email sent → {patient_email}")
        else:
            failed += 1

        # GChat webhook (optional)
        if gchat_webhook:
            _send_gchat_reminder(
                gchat_webhook, patient_name,
                doctor_name, time_slot, appt_date_str
            )

    result = {
        'date':        appt_date_str,
        'total':       len(appointments),
        'sent':        sent,
        'failed':      failed,
        'completed_at': datetime.utcnow().isoformat(),
    }
    logger.info(f"[Reminders] Done. Sent: {sent}, Failed: {failed}")
    return result


# ── Manual trigger (testing) ────────────────────

@celery.task(name='tasks.reminders.send_reminder_to_patient')
def send_reminder_to_patient(appointment_id: int):
    """
    Trigger a one-off reminder for a specific appointment.
    Useful for testing or manual admin triggers.
    """
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return {'error': f'Appointment {appointment_id} not found.'}

    ok = _send_email_reminder(
        patient_email = appt.patient.user.email,
        patient_name  = appt.patient.full_name,
        doctor_name   = appt.doctor.full_name,
        specialization= appt.doctor.specialization,
        appt_date     = str(appt.date),
        time_slot     = appt.time_slot,
        department    = appt.doctor.department.name if appt.doctor.department else 'General',
    )
    return {'appointment_id': appointment_id, 'sent': ok}
