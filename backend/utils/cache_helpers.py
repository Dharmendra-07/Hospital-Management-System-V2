"""
backend/utils/cache_helpers.py
Thin wrappers around flask-caching for ergonomic get-or-set patterns
and JSON-safe serialisation.
"""

import json
import logging
from functools import wraps
from flask import request
from extensions import cache

logger = logging.getLogger(__name__)


def get_or_set(key: str, builder_fn, timeout: int = 300):
    """
    Fetch `key` from cache; if missing, call `builder_fn()`,
    store the result, and return it.

    Example:
        data = get_or_set(
            CK.doctor_availability(doctor_id),
            lambda: _build_availability(doctor_id),
            timeout=TTL_SHORT,
        )
    """
    cached = cache.get(key)
    if cached is not None:
        logger.debug(f'[Cache HIT]  {key}')
        return cached

    logger.debug(f'[Cache MISS] {key}')
    value = builder_fn()
    cache.set(key, value, timeout=timeout)
    return value


def invalidate(*keys: str):
    """Delete one or more cache keys."""
    for key in keys:
        cache.delete(key)
        logger.debug(f'[Cache DEL]  {key}')


def cache_response(key_fn, timeout: int = 300):
    """
    Decorator that caches a route's JSON response.
    `key_fn` receives (args, kwargs) from the route and returns a string key.

    Example:
        @doctor_bp.route('/availability')
        @cache_response(lambda a, kw: CK.doctor_availability(kw['doctor_id']), TTL_SHORT)
        def get_availability(doctor_id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key    = key_fn(args, kwargs)
            cached = cache.get(key)
            if cached is not None:
                logger.debug(f'[Cache HIT]  {key}')
                from flask import jsonify
                return jsonify(cached), 200
            result, status = fn(*args, **kwargs)
            if status == 200:
                try:
                    data = result.get_json()
                    cache.set(key, data, timeout=timeout)
                    logger.debug(f'[Cache SET]  {key} ttl={timeout}s')
                except Exception:
                    pass
            return result, status
        return wrapper
    return decorator
