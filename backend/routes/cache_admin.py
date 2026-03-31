"""
backend/routes/cache_admin.py
Admin-only cache management endpoints:
  GET  /api/admin/cache/stats   → Redis memory + key count
  POST /api/admin/cache/flush   → Flush entire cache (dev/emergency)
  POST /api/admin/cache/invalidate  → Invalidate a specific group
"""

from flask import Blueprint, request, jsonify
from middleware.rbac import admin_required
from extensions import cache
from utils.cache_keys import Invalidate, CK

cache_admin_bp = Blueprint('cache_admin', __name__)


@cache_admin_bp.route('/stats', methods=['GET'])
@admin_required
def cache_stats():
    """Return Redis INFO memory + dbsize."""
    try:
        client = cache.cache._write_client
        info   = client.info('memory')
        dbsize = client.dbsize()

        # Count HMS keys by prefix
        def count_prefix(prefix):
            try:
                return sum(1 for _ in client.scan_iter(f'{prefix}*'))
            except Exception:
                return 0

        return jsonify({
            'redis_connected':      True,
            'total_keys':           dbsize,
            'used_memory_human':    info.get('used_memory_human', 'N/A'),
            'peak_memory_human':    info.get('used_memory_peak_human', 'N/A'),
            'key_counts': {
                'admin':        count_prefix('admin:'),
                'doctor':       count_prefix('doctor:'),
                'patient':      count_prefix('patient:'),
                'departments':  count_prefix('departments:'),
                'appointments': count_prefix('appointments:'),
                'doctors_list': count_prefix('doctors:list:'),
            },
            'ttl_policy': {
                'TTL_SHORT':  '60 s  — dashboard, availability, appointments',
                'TTL_MEDIUM': '300 s — doctor/patient lists, patient history',
                'TTL_LONG':   '1800 s — doctor/patient profiles',
                'TTL_DAY':    '86400 s — department catalog',
            },
        }), 200
    except Exception as e:
        return jsonify({'redis_connected': False, 'error': str(e)}), 500


@cache_admin_bp.route('/flush', methods=['POST'])
@admin_required
def flush_cache():
    """Flush all cached keys (use only in emergencies)."""
    try:
        cache.clear()
        return jsonify({'message': 'Cache flushed successfully.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cache_admin_bp.route('/invalidate', methods=['POST'])
@admin_required
def invalidate_group():
    """
    Invalidate a named cache group.
    Body: { "group": "doctor", "id": 42 }
          { "group": "patient", "id": 7 }
          { "group": "admin" }
          { "group": "departments" }
    """
    data  = request.get_json()
    group = data.get('group', '')
    obj_id = data.get('id')

    try:
        if group == 'admin':
            Invalidate.admin_dashboard(cache)
        elif group == 'doctor' and obj_id:
            Invalidate.doctor(cache, int(obj_id))
        elif group == 'patient' and obj_id:
            Invalidate.patient(cache, int(obj_id))
        elif group == 'availability' and obj_id:
            Invalidate.availability(cache, int(obj_id))
        elif group == 'departments':
            cache.delete(CK.DEPT_LIST)
        elif group == 'appointments' and obj_id:
            # Requires both doctor_id and patient_id; use admin flush for broad clear
            cache.delete(CK.APPT_STATS)
        else:
            return jsonify({'error': f"Unknown group '{group}' or missing id."}), 400

        return jsonify({'message': f"Cache group '{group}' invalidated."}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
