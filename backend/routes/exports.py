"""
backend/routes/exports.py
Patient CSV export endpoints:
  POST /api/patient/export           → trigger async Celery job
  GET  /api/patient/export/<task_id> → poll job status / result
  POST /api/admin/reports/trigger    → admin triggers monthly report on-demand
  POST /api/admin/reminders/trigger  → admin triggers daily reminder on-demand
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from celery.result import AsyncResult
from middleware.rbac import patient_required, admin_required
from models import User
from celery_worker import celery

export_bp = Blueprint('exports', __name__)


# ─────────────────────────────────────────────
# PATIENT — Trigger CSV export
# POST /api/patient/export
# ─────────────────────────────────────────────
@export_bp.route('/patient/export', methods=['POST'])
@patient_required
def trigger_csv_export():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    patient = user.patient_profile

    if not patient:
        return jsonify({'error': 'Patient profile not found.'}), 404

    # Dispatch async task
    task = celery.send_task(
        'tasks.exports.generate_csv_export',
        args=[patient.id],
    )

    return jsonify({
        'message': (
            'Your export has started. You will receive an email with '
            'the CSV once it is ready.'
        ),
        'task_id': task.id,
    }), 202


# ─────────────────────────────────────────────
# PATIENT — Poll export job status
# GET /api/patient/export/<task_id>
# ─────────────────────────────────────────────
@export_bp.route('/patient/export/<task_id>', methods=['GET'])
@patient_required
def csv_export_status(task_id):
    result = AsyncResult(task_id, app=celery)

    state    = result.state
    response = {'task_id': task_id, 'state': state}

    if state == 'PENDING':
        response['message']  = 'Job is queued, waiting for a worker…'
        response['progress'] = 0

    elif state == 'PROGRESS':
        meta = result.info or {}
        response['message']  = meta.get('status',   'Processing…')
        response['progress'] = meta.get('progress', 50)

    elif state == 'SUCCESS':
        info = result.result or {}
        response['message']      = 'Export complete! Check your email.'
        response['progress']     = 100
        response['filename']     = info.get('filename')
        response['rows']         = info.get('rows')
        response['completed_at'] = info.get('completed_at')

    elif state == 'FAILURE':
        response['message']  = 'Export failed. Please try again.'
        response['progress'] = 0
        response['error']    = str(result.info)

    else:
        response['message'] = f'Job state: {state}'

    return jsonify(response), 200


# ─────────────────────────────────────────────
# ADMIN — Trigger daily reminders manually
# POST /api/admin/jobs/reminders
# ─────────────────────────────────────────────
@export_bp.route('/admin/jobs/reminders', methods=['POST'])
@admin_required
def trigger_reminders():
    task = celery.send_task('tasks.reminders.send_daily_reminders')
    return jsonify({
        'message': 'Daily reminder job triggered.',
        'task_id': task.id,
    }), 202


# ─────────────────────────────────────────────
# ADMIN — Trigger monthly report manually
# POST /api/admin/jobs/reports
# Body: { year: 2025, month: 1 }  (optional; defaults to last month)
# ─────────────────────────────────────────────
@export_bp.route('/admin/jobs/reports', methods=['POST'])
@admin_required
def trigger_reports():
    from datetime import date
    from dateutil.relativedelta import relativedelta

    data  = request.get_json() or {}
    today = date.today()
    prev  = today - relativedelta(months=1)

    year  = data.get('year',  prev.year)
    month = data.get('month', prev.month)

    task = celery.send_task('tasks.reports.send_monthly_reports')
    return jsonify({
        'message': f'Monthly report job triggered for {month}/{year}.',
        'task_id': task.id,
    }), 202


# ─────────────────────────────────────────────
# ADMIN — Poll any job status
# GET /api/admin/jobs/<task_id>
# ─────────────────────────────────────────────
@export_bp.route('/admin/jobs/<task_id>', methods=['GET'])
@admin_required
def admin_job_status(task_id):
    result = AsyncResult(task_id, app=celery)
    return jsonify({
        'task_id': task_id,
        'state':   result.state,
        'result':  result.result if result.state == 'SUCCESS' else None,
        'error':   str(result.info) if result.state == 'FAILURE' else None,
    }), 200
