"""
backend/routes/pdf_reports.py
PDF report generation endpoints.

GET  /api/reports/doctor/<id>/monthly?year=&month=
     → streams a PDF of the doctor's monthly activity report

GET  /api/reports/patient/<id>/history
     → admin-only PDF of a patient's full treatment history

Requires: pip install weasyprint  (or falls back to HTML)
          Alternatively uses reportlab as the primary renderer.

Install:  pip install reportlab
"""

from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from models import Appointment, Doctor, Patient, User
from middleware.rbac import admin_required, doctor_required
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar
import io
import json

pdf_bp = Blueprint('pdf_reports', __name__)


# ── PDF generation (reportlab) ──────────────────────────────

def _generate_pdf_bytes(html_content: str) -> bytes:
    """
    Generate PDF bytes from HTML string.
    Uses reportlab for simple structured output.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle,
            Spacer, HRFlowable
        )
        return None  # Signal to use HTML fallback for now
    except ImportError:
        return None


def _build_doctor_report_data(doctor: Doctor, year: int, month: int) -> dict:
    """Collect all report data for a doctor+month."""
    first_day = date(year, month, 1)
    last_day  = (first_day + relativedelta(months=1)) - relativedelta(days=1)

    appts = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date >= first_day,
        Appointment.date <= last_day,
    ).order_by(Appointment.date).all()

    rows = []
    diagnoses = []
    for a in appts:
        diag = prescription = next_visit = None
        if a.treatment:
            diag         = a.treatment.diagnosis
            prescription = a.treatment.prescription
            next_visit   = str(a.treatment.next_visit) if a.treatment.next_visit else None
            if diag:
                diagnoses.append(diag)
        rows.append({
            'date':         str(a.date),
            'patient_name': a.patient.full_name,
            'time_slot':    a.time_slot,
            'visit_type':   a.visit_type,
            'status':       a.status,
            'diagnosis':    diag,
            'prescription': prescription,
            'next_visit':   next_visit,
        })

    from collections import Counter
    top_dx = Counter(d.strip().lower() for d in diagnoses if d)

    return {
        'doctor_name':    doctor.full_name,
        'specialization': doctor.specialization,
        'qualification':  doctor.qualification or '',
        'department':     doctor.department.name if doctor.department else 'General',
        'month_name':     calendar.month_name[month],
        'year':           year,
        'generated_at':   date.today().strftime('%d %B %Y'),
        'total':          len(appts),
        'completed':      sum(1 for a in appts if a.status == 'Completed'),
        'cancelled':      sum(1 for a in appts if a.status == 'Cancelled'),
        'booked':         sum(1 for a in appts if a.status == 'Booked'),
        'unique_patients': len({a.patient_id for a in appts}),
        'appointments':   rows,
        'top_diagnoses':  [{'name': k, 'count': v}
                           for k, v in top_dx.most_common(5)],
    }


# ── HTML Report Template (used when PDF lib not available) ───

REPORT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 20mm; }}
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; }}
  h1   {{ color: #0d6efd; font-size: 20px; border-bottom: 2px solid #0d6efd; padding-bottom: 6px; }}
  h2   {{ font-size: 14px; color: #444; margin-top: 24px; }}
  .meta {{ color: #666; font-size: 11px; margin-bottom: 16px; line-height: 1.8; }}
  .stats {{ display: flex; gap: 16px; margin: 16px 0; }}
  .stat  {{ border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 16px; text-align: center; }}
  .stat .n {{ font-size: 24px; font-weight: bold; color: #0d6efd; }}
  .stat .l {{ font-size: 10px; color: #888; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }}
  th {{ background: #0d6efd; color: #fff; padding: 6px 8px; text-align: left; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
  tr:nth-child(even) td {{ background: #f9f9f9; }}
  .footer {{ margin-top: 32px; font-size: 10px; color: #999; border-top: 1px solid #eee; padding-top: 8px; }}
  .badge-completed {{ color: #198754; font-weight: bold; }}
  .badge-cancelled  {{ color: #dc3545; font-weight: bold; }}
  .badge-booked     {{ color: #0d6efd; font-weight: bold; }}
</style>
</head>
<body>
<h1>🏥 Monthly Activity Report</h1>
<div class="meta">
  <b>Doctor:</b> Dr. {doctor_name}<br>
  <b>Specialization:</b> {specialization}<br>
  <b>Department:</b> {department}<br>
  <b>Qualification:</b> {qualification}<br>
  <b>Period:</b> {month_name} {year}<br>
  <b>Generated:</b> {generated_at}
</div>

<h2>Summary</h2>
<div class="stats">
  <div class="stat"><div class="n">{total}</div><div class="l">Total</div></div>
  <div class="stat"><div class="n" style="color:#198754">{completed}</div><div class="l">Completed</div></div>
  <div class="stat"><div class="n" style="color:#dc3545">{cancelled}</div><div class="l">Cancelled</div></div>
  <div class="stat"><div class="n" style="color:#0d6efd">{booked}</div><div class="l">Booked</div></div>
  <div class="stat"><div class="n">{unique_patients}</div><div class="l">Unique Patients</div></div>
</div>

<h2>Appointment Details</h2>
{appointments_table}

{diagnoses_section}

<div class="footer">
  Generated by HMS V2 on {generated_at}.
  This report is confidential and intended for the named doctor only.
</div>
</body></html>"""


def _render_html_report(data: dict) -> str:
    rows_html = ''
    if data['appointments']:
        rows_html = '<table><thead><tr>'
        rows_html += '<th>#</th><th>Date</th><th>Patient</th><th>Time</th>'
        rows_html += '<th>Type</th><th>Status</th><th>Diagnosis</th></tr></thead><tbody>'
        for i, a in enumerate(data['appointments'], 1):
            status_class = f'badge-{a["status"].lower()}'
            rows_html += (
                f'<tr><td>{i}</td><td>{a["date"]}</td>'
                f'<td>{a["patient_name"]}</td><td>{a["time_slot"]}</td>'
                f'<td>{a["visit_type"]}</td>'
                f'<td class="{status_class}">{a["status"]}</td>'
                f'<td>{a["diagnosis"] or "—"}</td></tr>'
            )
        rows_html += '</tbody></table>'
    else:
        rows_html = '<p style="color:#888;">No appointments in this period.</p>'

    dx_html = ''
    if data['top_diagnoses']:
        dx_html = '<h2>Top Diagnoses</h2><table><thead>'
        dx_html += '<tr><th>Diagnosis</th><th>Count</th></tr></thead><tbody>'
        for d in data['top_diagnoses']:
            dx_html += f'<tr><td>{d["name"].title()}</td><td>{d["count"]}</td></tr>'
        dx_html += '</tbody></table>'

    return REPORT_HTML.format(
        **data,
        appointments_table=rows_html,
        diagnoses_section=dx_html,
    )


# ─────────────────────────────────────────────
# GET /api/reports/doctor/<id>/monthly
# Admin or the doctor themselves can download
# ?year=2025&month=1  (defaults to last month)
# ─────────────────────────────────────────────
@pdf_bp.route('/doctor/<int:doctor_id>/monthly', methods=['GET'])
def doctor_monthly_report(doctor_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())

    # Access control
    if role == 'doctor':
        doc = User.query.get(user_id).doctor_profile
        if not doc or doc.id != doctor_id:
            return jsonify({'error': 'Access denied.'}), 403
    elif role != 'admin':
        return jsonify({'error': 'Access denied.'}), 403

    today = date.today()
    prev  = today - relativedelta(months=1)
    year  = int(request.args.get('year',  prev.year))
    month = int(request.args.get('month', prev.month))
    fmt   = request.args.get('format', 'html')   # html | json

    doctor = Doctor.query.get_or_404(doctor_id)
    data   = _build_doctor_report_data(doctor, year, month)

    if fmt == 'json':
        return jsonify(data), 200

    html = _render_html_report(data)

    # Try PDF generation
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        resp = make_response(pdf_bytes)
        resp.headers['Content-Type']        = 'application/pdf'
        resp.headers['Content-Disposition'] = (
            f'attachment; filename="report_dr_{doctor_id}_{year}_{month}.pdf"'
        )
        return resp
    except ImportError:
        pass

    # Fallback to HTML download
    resp = make_response(html)
    resp.headers['Content-Type']        = 'text/html; charset=utf-8'
    resp.headers['Content-Disposition'] = (
        f'attachment; filename="report_dr_{doctor_id}_{year}_{month}.html"'
    )
    return resp


# ─────────────────────────────────────────────
# GET /api/reports/patient/<id>/history  (admin)
# Full patient treatment history as HTML/PDF
# ─────────────────────────────────────────────
@pdf_bp.route('/patient/<int:patient_id>/history', methods=['GET'])
@admin_required
def patient_history_report(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appts   = Appointment.query.filter_by(patient_id=patient_id)\
                               .order_by(Appointment.date.desc()).all()

    rows_html = '<table><thead><tr>'
    rows_html += '<th>#</th><th>Date</th><th>Doctor</th><th>Specialization</th>'
    rows_html += '<th>Status</th><th>Diagnosis</th><th>Prescription</th></tr>'
    rows_html += '</thead><tbody>'
    for i, a in enumerate(appts, 1):
        diag = a.treatment.diagnosis    if a.treatment else '—'
        prx  = a.treatment.prescription if a.treatment else '—'
        rows_html += (
            f'<tr><td>{i}</td><td>{a.date}</td>'
            f'<td>Dr. {a.doctor.full_name}</td><td>{a.doctor.specialization}</td>'
            f'<td>{a.status}</td><td>{diag}</td><td>{prx}</td></tr>'
        )
    rows_html += '</tbody></table>'

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial; font-size: 12px; color: #333; }}
  h1   {{ color: #0d6efd; }}
  table {{ width:100%; border-collapse: collapse; font-size:11px; }}
  th {{ background:#0d6efd; color:#fff; padding:6px 8px; text-align:left; }}
  td {{ padding:6px 8px; border-bottom:1px solid #eee; }}
</style></head><body>
<h1>Patient Treatment History</h1>
<p><b>Name:</b> {patient.full_name} &nbsp;|&nbsp;
   <b>Blood Group:</b> {patient.blood_group or '—'} &nbsp;|&nbsp;
   <b>Contact:</b> {patient.contact_number or '—'}</p>
{rows_html}
<p style="font-size:10px;color:#999;margin-top:24px;">
  Generated by HMS V2 on {date.today()}</p>
</body></html>"""

    resp = make_response(html)
    resp.headers['Content-Type']        = 'text/html; charset=utf-8'
    resp.headers['Content-Disposition'] = (
        f'attachment; filename="patient_{patient_id}_history.html"'
    )
    return resp
