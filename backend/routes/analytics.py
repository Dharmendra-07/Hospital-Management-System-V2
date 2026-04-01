"""
backend/routes/analytics.py
Analytics API — feeds Chart.js on the frontend.
All endpoints require admin role.

Charts provided:
  1. Appointments trend      — last 12 months (line chart)
  2. Status breakdown        — Booked/Completed/Cancelled (doughnut)
  3. Specialization demand   — appointment count per specialization (bar)
  4. Department load         — appointments per department (bar)
  5. Top doctors             — by completed appointments (horizontal bar)
  6. Daily appointments      — current month day-by-day (line)
  7. Patient registrations   — last 12 months (bar)
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import func, extract
from models import (db, Appointment, Patient, Doctor,
                    Department, User, Treatment)
from middleware.rbac import admin_required
from extensions import cache
from utils.cache_keys import TTL_MEDIUM
from utils.cache_helpers import get_or_set
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

analytics_bp = Blueprint('analytics', __name__)


# ── helpers ────────────────────────────────────

def _month_labels(n=12):
    """Return last n month labels like ['Jan 24', 'Feb 24', …]."""
    today  = date.today()
    labels = []
    for i in range(n - 1, -1, -1):
        d = today - relativedelta(months=i)
        labels.append(d.strftime('%b %y'))
    return labels


def _last_n_months(n=12):
    """Return list of (year, month) tuples for last n months."""
    today   = date.today()
    months  = []
    for i in range(n - 1, -1, -1):
        d = today - relativedelta(months=i)
        months.append((d.year, d.month))
    return months


# ─────────────────────────────────────────────
# GET /api/analytics/appointments-trend
# Line chart: total appointments per month (last 12 months)
# ─────────────────────────────────────────────
@analytics_bp.route('/appointments-trend', methods=['GET'])
@admin_required
def appointments_trend():
    def _build():
        months  = _last_n_months(12)
        labels  = _month_labels(12)
        booked_data    = []
        completed_data = []
        cancelled_data = []

        for year, month in months:
            base = Appointment.query.filter(
                extract('year',  Appointment.date) == year,
                extract('month', Appointment.date) == month,
            )
            booked_data.append(   base.filter_by(status='Booked').count())
            completed_data.append(base.filter_by(status='Completed').count())
            cancelled_data.append(base.filter_by(status='Cancelled').count())

        return {
            'labels': labels,
            'datasets': [
                {
                    'label':           'Booked',
                    'data':            booked_data,
                    'borderColor':     '#0d6efd',
                    'backgroundColor': 'rgba(13,110,253,.12)',
                    'tension':         0.4,
                    'fill':            True,
                },
                {
                    'label':           'Completed',
                    'data':            completed_data,
                    'borderColor':     '#198754',
                    'backgroundColor': 'rgba(25,135,84,.12)',
                    'tension':         0.4,
                    'fill':            True,
                },
                {
                    'label':           'Cancelled',
                    'data':            cancelled_data,
                    'borderColor':     '#dc3545',
                    'backgroundColor': 'rgba(220,53,69,.08)',
                    'tension':         0.4,
                    'fill':            True,
                },
            ],
        }

    return jsonify(get_or_set('analytics:appointments_trend', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/status-breakdown
# Doughnut: overall Booked / Completed / Cancelled
# ─────────────────────────────────────────────
@analytics_bp.route('/status-breakdown', methods=['GET'])
@admin_required
def status_breakdown():
    def _build():
        booked    = Appointment.query.filter_by(status='Booked').count()
        completed = Appointment.query.filter_by(status='Completed').count()
        cancelled = Appointment.query.filter_by(status='Cancelled').count()
        return {
            'labels': ['Booked', 'Completed', 'Cancelled'],
            'datasets': [{
                'data':            [booked, completed, cancelled],
                'backgroundColor': ['#0d6efd', '#198754', '#dc3545'],
                'borderWidth':     0,
                'hoverOffset':     6,
            }],
        }

    return jsonify(get_or_set('analytics:status_breakdown', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/specialization-demand
# Bar: appointments per doctor specialization
# ─────────────────────────────────────────────
@analytics_bp.route('/specialization-demand', methods=['GET'])
@admin_required
def specialization_demand():
    def _build():
        rows = (
            db.session.query(Doctor.specialization,
                             func.count(Appointment.id).label('cnt'))
            .join(Appointment, Appointment.doctor_id == Doctor.id)
            .group_by(Doctor.specialization)
            .order_by(func.count(Appointment.id).desc())
            .limit(10)
            .all()
        )
        labels = [r.specialization for r in rows]
        data   = [r.cnt for r in rows]

        colors = [
            '#0d6efd','#198754','#dc3545','#ffc107',
            '#0dcaf0','#6610f2','#fd7e14','#20c997',
            '#d63384','#6c757d',
        ]
        return {
            'labels': labels,
            'datasets': [{
                'label':           'Appointments',
                'data':            data,
                'backgroundColor': colors[:len(data)],
                'borderRadius':    6,
                'borderSkipped':   False,
            }],
        }

    return jsonify(get_or_set('analytics:spec_demand', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/department-load
# Bar: appointments per department
# ─────────────────────────────────────────────
@analytics_bp.route('/department-load', methods=['GET'])
@admin_required
def department_load():
    def _build():
        rows = (
            db.session.query(Department.name,
                             func.count(Appointment.id).label('cnt'))
            .join(Doctor,      Doctor.department_id == Department.id)
            .join(Appointment, Appointment.doctor_id == Doctor.id)
            .group_by(Department.name)
            .order_by(func.count(Appointment.id).desc())
            .all()
        )
        return {
            'labels': [r.name for r in rows],
            'datasets': [{
                'label':           'Appointments',
                'data':            [r.cnt for r in rows],
                'backgroundColor': 'rgba(13,110,253,.75)',
                'borderRadius':    6,
            }],
        }

    return jsonify(get_or_set('analytics:dept_load', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/top-doctors
# Horizontal bar: top 8 doctors by completed appointments
# ─────────────────────────────────────────────
@analytics_bp.route('/top-doctors', methods=['GET'])
@admin_required
def top_doctors():
    def _build():
        rows = (
            db.session.query(Doctor.full_name,
                             func.count(Appointment.id).label('cnt'))
            .join(Appointment, Appointment.doctor_id == Doctor.id)
            .filter(Appointment.status == 'Completed')
            .group_by(Doctor.full_name)
            .order_by(func.count(Appointment.id).desc())
            .limit(8)
            .all()
        )
        return {
            'labels': [r.full_name for r in rows],
            'datasets': [{
                'label':           'Completed Appointments',
                'data':            [r.cnt for r in rows],
                'backgroundColor': 'rgba(25,135,84,.8)',
                'borderRadius':    6,
            }],
        }

    return jsonify(get_or_set('analytics:top_doctors', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/daily-appointments
# Line: this month day-by-day appointment count
# ─────────────────────────────────────────────
@analytics_bp.route('/daily-appointments', methods=['GET'])
@admin_required
def daily_appointments():
    def _build():
        today       = date.today()
        first_day   = today.replace(day=1)
        days_so_far = today.day
        labels      = [str(d) for d in range(1, days_so_far + 1)]
        data        = []

        for day in range(1, days_so_far + 1):
            d   = first_day.replace(day=day)
            cnt = Appointment.query.filter(Appointment.date == d).count()
            data.append(cnt)

        return {
            'labels': labels,
            'datasets': [{
                'label':           f'Appointments — {today.strftime("%B %Y")}',
                'data':            data,
                'borderColor':     '#0dcaf0',
                'backgroundColor': 'rgba(13,202,240,.15)',
                'tension':         0.3,
                'fill':            True,
                'pointRadius':     4,
            }],
        }

    return jsonify(get_or_set('analytics:daily_appointments', _build, 60)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/patient-registrations
# Bar: new patients per month (last 12 months)
# ─────────────────────────────────────────────
@analytics_bp.route('/patient-registrations', methods=['GET'])
@admin_required
def patient_registrations():
    def _build():
        months = _last_n_months(12)
        labels = _month_labels(12)
        data   = []

        for year, month in months:
            cnt = (
                db.session.query(func.count(Patient.id))
                .join(User, User.id == Patient.user_id)
                .filter(
                    extract('year',  User.created_at) == year,
                    extract('month', User.created_at) == month,
                )
                .scalar() or 0
            )
            data.append(cnt)

        return {
            'labels': labels,
            'datasets': [{
                'label':           'New Patients',
                'data':            data,
                'backgroundColor': 'rgba(108,117,125,.7)',
                'borderRadius':    6,
            }],
        }

    return jsonify(get_or_set('analytics:patient_reg', _build, TTL_MEDIUM)), 200


# ─────────────────────────────────────────────
# GET /api/analytics/summary
# All KPI numbers in one call (admin dashboard cards)
# ─────────────────────────────────────────────
@analytics_bp.route('/summary', methods=['GET'])
@admin_required
def analytics_summary():
    def _build():
        today     = date.today()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - relativedelta(months=1))
        last_month_end   = this_month_start - timedelta(days=1)

        this_month_appts = Appointment.query.filter(
            Appointment.date >= this_month_start).count()
        last_month_appts = Appointment.query.filter(
            Appointment.date >= last_month_start,
            Appointment.date <= last_month_end).count()

        growth = 0
        if last_month_appts > 0:
            growth = round((this_month_appts - last_month_appts)
                           / last_month_appts * 100, 1)

        return {
            'total_appointments': Appointment.query.count(),
            'this_month':        this_month_appts,
            'last_month':        last_month_appts,
            'growth_pct':        growth,
            'total_doctors':     Doctor.query.join(User).filter(User.is_active==True).count(),
            'total_patients':    Patient.query.join(User).filter(User.is_active==True).count(),
            'completed_today':   Appointment.query.filter(
                Appointment.date == today, Appointment.status == 'Completed').count(),
            'booked_today':      Appointment.query.filter(
                Appointment.date == today, Appointment.status == 'Booked').count(),
        }

    return jsonify(get_or_set('analytics:summary', _build, 60)), 200
