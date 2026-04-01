"""
backend/routes/payments.py
Dummy payment portal — simulates payment for completed treatments.

Real deployment: replace _process_payment() with Razorpay / Stripe SDK calls.
Endpoints:
  POST /api/payments/initiate          — create payment record
  POST /api/payments/<id>/confirm      — simulate payment success/failure
  GET  /api/payments/<id>              — payment status
  GET  /api/payments/history           — patient's payment history
  GET  /api/admin/payments             — all payments (admin)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from models import db, Appointment, Patient, User
from middleware.rbac import patient_required, admin_required
from datetime import datetime
import uuid, random

payments_bp = Blueprint('payments', __name__)

# ── In-memory payment store (replace with Payment SQLAlchemy model in production) ──
# Structure: { payment_id: { ...fields } }
_PAYMENTS = {}


def _fee_for_appointment(appt):
    """Calculate consultation fee based on specialization."""
    base_fees = {
        'Cardiology':       1500,
        'Oncology':         2000,
        'Neurology':        1800,
        'Orthopedics':      1200,
        'Gynecology':       1000,
        'Pediatrics':        800,
        'Dermatology':       700,
        'General Medicine':  500,
    }
    spec = appt.doctor.specialization if appt.doctor else 'General Medicine'
    return base_fees.get(spec, 800)


def _process_payment(method: str, amount: float):
    """
    Simulates payment processing.
    Returns (success: bool, transaction_id: str | None, message: str)
    Replace this function body with real gateway SDK calls.
    """
    # Simulate 95% success rate
    success = random.random() < 0.95
    if success:
        txn_id = f'TXN-{uuid.uuid4().hex[:12].upper()}'
        return True, txn_id, 'Payment processed successfully.'
    return False, None, 'Payment declined. Please try a different method or card.'


# ─────────────────────────────────────────────
# POST /api/payments/initiate
# Patient initiates payment for a completed appointment
# Body: { appointment_id, payment_method }
# ─────────────────────────────────────────────
@payments_bp.route('/initiate', methods=['POST'])
@patient_required
def initiate_payment():
    user_id = int(get_jwt_identity())
    patient = User.query.get(user_id).patient_profile
    data    = request.get_json() or {}

    appt_id = data.get('appointment_id')
    method  = data.get('payment_method', 'card')  # card | upi | netbanking | cash

    if not appt_id:
        return jsonify({'error': 'appointment_id is required.'}), 400
    if method not in ('card', 'upi', 'netbanking', 'cash'):
        return jsonify({'error': 'Invalid payment method.'}), 400

    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != patient.id:
        return jsonify({'error': 'Access denied.'}), 403
    if appt.status != 'Completed':
        return jsonify({'error': 'Payment is only available for completed appointments.'}), 400

    # Check already paid
    existing = next((p for p in _PAYMENTS.values()
                     if p['appointment_id'] == appt_id
                     and p['status'] == 'paid'), None)
    if existing:
        return jsonify({'error': 'This appointment has already been paid.',
                        'payment_id': existing['id']}), 409

    amount     = _fee_for_appointment(appt)
    payment_id = f'PAY-{uuid.uuid4().hex[:10].upper()}'

    _PAYMENTS[payment_id] = {
        'id':             payment_id,
        'appointment_id': appt_id,
        'patient_id':     patient.id,
        'patient_name':   patient.full_name,
        'doctor_name':    appt.doctor.full_name,
        'specialization': appt.doctor.specialization,
        'appt_date':      str(appt.date),
        'amount':         amount,
        'currency':       'INR',
        'payment_method': method,
        'status':         'pending',
        'transaction_id': None,
        'created_at':     datetime.utcnow().isoformat(),
        'paid_at':        None,
    }

    return jsonify({
        'payment_id':     payment_id,
        'amount':         amount,
        'currency':       'INR',
        'appointment_id': appt_id,
        'doctor_name':    appt.doctor.full_name,
        'status':         'pending',
        'message':        'Payment initiated. Proceed to confirm.',
    }), 201


# ─────────────────────────────────────────────
# POST /api/payments/<id>/confirm
# Patient confirms payment (submit card/UPI details)
# Body: { card_number?, card_holder?, expiry?, cvv?, upi_id? }
# ─────────────────────────────────────────────
@payments_bp.route('/<payment_id>/confirm', methods=['POST'])
@patient_required
def confirm_payment(payment_id):
    user_id = int(get_jwt_identity())
    patient = User.query.get(user_id).patient_profile
    payment = _PAYMENTS.get(payment_id)

    if not payment:
        return jsonify({'error': 'Payment not found.'}), 404
    if payment['patient_id'] != patient.id:
        return jsonify({'error': 'Access denied.'}), 403
    if payment['status'] == 'paid':
        return jsonify({'error': 'Already paid.', 'payment_id': payment_id}), 409
    if payment['status'] == 'failed':
        return jsonify({'error': 'Payment failed. Please initiate a new payment.'}), 400

    data   = request.get_json() or {}
    method = payment['payment_method']

    # Minimal frontend validation (real gateway handles actual validation)
    if method == 'card':
        card = data.get('card_number', '').replace(' ', '')
        if not card or len(card) < 12:
            return jsonify({'error': 'Enter a valid card number.'}), 400
        if not data.get('card_holder', '').strip():
            return jsonify({'error': 'Card holder name is required.'}), 400
        if not data.get('cvv', ''):
            return jsonify({'error': 'CVV is required.'}), 400
    elif method == 'upi':
        upi_id = data.get('upi_id', '')
        if not upi_id or '@' not in upi_id:
            return jsonify({'error': 'Enter a valid UPI ID (e.g. name@upi).'}), 400

    # Process payment
    success, txn_id, message = _process_payment(method, payment['amount'])

    payment['status']         = 'paid' if success else 'failed'
    payment['transaction_id'] = txn_id
    payment['paid_at']        = datetime.utcnow().isoformat() if success else None

    if success:
        return jsonify({
            'status':         'paid',
            'transaction_id': txn_id,
            'amount':         payment['amount'],
            'currency':       'INR',
            'message':        message,
            'receipt':        _build_receipt(payment),
        }), 200
    else:
        return jsonify({
            'status':  'failed',
            'message': message,
        }), 402


# ─────────────────────────────────────────────
# GET /api/payments/<id>
# ─────────────────────────────────────────────
@payments_bp.route('/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    verify_jwt_in_request()
    claims  = get_jwt()
    role    = claims.get('role')
    user_id = int(get_jwt_identity())

    payment = _PAYMENTS.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found.'}), 404

    if role == 'patient':
        patient = User.query.get(user_id).patient_profile
        if payment['patient_id'] != patient.id:
            return jsonify({'error': 'Access denied.'}), 403

    return jsonify(payment), 200


# ─────────────────────────────────────────────
# GET /api/payments/history
# Patient payment history
# ─────────────────────────────────────────────
@payments_bp.route('/history', methods=['GET'])
@patient_required
def patient_payment_history():
    user_id = int(get_jwt_identity())
    patient = User.query.get(user_id).patient_profile

    history = [p for p in _PAYMENTS.values()
               if p['patient_id'] == patient.id]
    history.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(history), 200


# ─────────────────────────────────────────────
# GET /api/admin/payments
# Admin view of all payments
# ─────────────────────────────────────────────
@payments_bp.route('/admin/all', methods=['GET'])
@admin_required
def admin_all_payments():
    status = request.args.get('status')
    data   = list(_PAYMENTS.values())
    if status:
        data = [p for p in data if p['status'] == status]
    data.sort(key=lambda x: x['created_at'], reverse=True)
    total_revenue = sum(p['amount'] for p in data if p['status'] == 'paid')
    return jsonify({'payments': data, 'total_revenue': total_revenue,
                    'count': len(data)}), 200


# ── Receipt builder ─────────────────────────────────────────

def _build_receipt(payment: dict) -> dict:
    return {
        'receipt_no':     f'RCP-{payment["id"]}',
        'payment_id':     payment['id'],
        'transaction_id': payment['transaction_id'],
        'patient_name':   payment['patient_name'],
        'doctor_name':    payment['doctor_name'],
        'specialization': payment['specialization'],
        'appt_date':      payment['appt_date'],
        'amount':         payment['amount'],
        'currency':       'INR',
        'payment_method': payment['payment_method'].upper(),
        'paid_at':        payment['paid_at'],
        'status':         'PAID',
    }
