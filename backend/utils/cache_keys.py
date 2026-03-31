"""
backend/utils/cache_keys.py
Centralised cache key registry.

All cache keys live here so invalidation is consistent and no
magic strings are scattered across route files.

Naming convention:
    <entity>:<scope>:<id_or_qualifier>
    e.g.  doctor:availability:42
          admin:dashboard
          patient:appointments:7:upcoming
"""

# ── TTL constants (seconds) ─────────────────────────────────────
TTL_SHORT   =  60        # 1 min  — highly volatile (live availability)
TTL_MEDIUM  = 300        # 5 min  — moderately volatile (department lists)
TTL_LONG    = 1800       # 30 min — stable-ish (doctor profiles)
TTL_DAY     = 86400      # 24 hr  — very stable (department catalog)


# ── Key builders ────────────────────────────────────────────────

class CK:
    """Cache Key factory — call CK.<method>() to get the key string."""

    # Admin
    ADMIN_DASHBOARD       = 'admin:dashboard'
    ADMIN_DOCTOR_LIST     = 'admin:doctors:all'
    ADMIN_PATIENT_LIST    = 'admin:patients:all'

    @staticmethod
    def admin_appt_page(status: str, page: int) -> str:
        return f'admin:appointments:{status or "all"}:p{page}'

    # Departments
    DEPT_LIST = 'departments:all'

    @staticmethod
    def dept_detail(dept_id: int) -> str:
        return f'departments:{dept_id}'

    # Doctors
    @staticmethod
    def doctor_list(q: str = '', spec: str = '', dept_id: int = 0) -> str:
        return f'doctors:list:{q}:{spec}:{dept_id}'

    @staticmethod
    def doctor_profile(doctor_id: int) -> str:
        return f'doctor:profile:{doctor_id}'

    @staticmethod
    def doctor_availability(doctor_id: int) -> str:
        return f'doctor:availability:{doctor_id}'

    # Patient
    @staticmethod
    def patient_profile(patient_id: int) -> str:
        return f'patient:profile:{patient_id}'

    @staticmethod
    def patient_appointments(patient_id: int, view: str) -> str:
        return f'patient:appointments:{patient_id}:{view}'

    @staticmethod
    def patient_history(patient_id: int) -> str:
        return f'patient:history:{patient_id}'

    # Doctor dashboard
    @staticmethod
    def doctor_dashboard(doctor_id: int) -> str:
        return f'doctor:dashboard:{doctor_id}'

    @staticmethod
    def doctor_patients(doctor_id: int) -> str:
        return f'doctor:patients:{doctor_id}'

    # Appointment stats
    APPT_STATS = 'appointments:stats'


# ── Invalidation groups ─────────────────────────────────────────
# When an entity changes, delete all keys in its group.

class Invalidate:
    """
    Call these after write operations to keep cache consistent.
    Usage:
        from extensions import cache
        from utils.cache_keys import Invalidate
        Invalidate.doctor(cache, doctor_id)
    """

    @staticmethod
    def admin_dashboard(cache):
        cache.delete(CK.ADMIN_DASHBOARD)
        cache.delete(CK.ADMIN_DOCTOR_LIST)
        cache.delete(CK.ADMIN_PATIENT_LIST)
        cache.delete(CK.APPT_STATS)

    @staticmethod
    def doctor(cache, doctor_id: int):
        cache.delete(CK.doctor_profile(doctor_id))
        cache.delete(CK.doctor_availability(doctor_id))
        cache.delete(CK.doctor_dashboard(doctor_id))
        cache.delete(CK.doctor_patients(doctor_id))
        cache.delete(CK.ADMIN_DOCTOR_LIST)
        cache.delete(CK.ADMIN_DASHBOARD)
        # Bust all doctor list search keys (prefix delete via Redis)
        _delete_prefix(cache, 'doctors:list:')

    @staticmethod
    def patient(cache, patient_id: int):
        cache.delete(CK.patient_profile(patient_id))
        cache.delete(CK.patient_history(patient_id))
        cache.delete(CK.ADMIN_PATIENT_LIST)
        cache.delete(CK.ADMIN_DASHBOARD)
        _delete_prefix(cache, f'patient:appointments:{patient_id}:')

    @staticmethod
    def appointment(cache, doctor_id: int, patient_id: int):
        cache.delete(CK.doctor_availability(doctor_id))
        cache.delete(CK.doctor_dashboard(doctor_id))
        cache.delete(CK.doctor_patients(doctor_id))
        cache.delete(CK.patient_history(patient_id))
        cache.delete(CK.ADMIN_DASHBOARD)
        cache.delete(CK.APPT_STATS)
        _delete_prefix(cache, f'patient:appointments:{patient_id}:')
        _delete_prefix(cache, f'admin:appointments:')

    @staticmethod
    def availability(cache, doctor_id: int):
        cache.delete(CK.doctor_availability(doctor_id))
        cache.delete(CK.doctor_dashboard(doctor_id))
        _delete_prefix(cache, 'doctors:list:')


def _delete_prefix(cache, prefix: str):
    """
    Delete all Redis keys that start with `prefix`.
    Falls back silently if the underlying store does not support SCAN.
    """
    try:
        client = cache.cache._write_client   # flask-caching RedisCache
        keys   = client.scan_iter(f'{prefix}*')
        for k in keys:
            client.delete(k)
    except Exception:
        pass   # degrade gracefully — cache miss is always safe
