"""
backend/config.py
All Flask configuration — DB, JWT, Redis, Celery, Mail, Cache.
Copy .env.example → .env and fill in real values before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ── Core ──────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hms-dev-secret-change-in-prod')

    # ── SQLite ────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        'sqlite:///' + os.path.join(BASE_DIR, 'hms.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ───────────────────────────────────
    JWT_SECRET_KEY          = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES  = 8 * 3600   # 8 hours (seconds)
    JWT_REFRESH_TOKEN_EXPIRES = 7 * 86400  # 7 days

    # ── Redis ─────────────────────────────────
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # ── Celery ────────────────────────────────
    CELERY_BROKER_URL      = REDIS_URL
    CELERY_RESULT_BACKEND  = REDIS_URL
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT  = ['json']
    CELERY_TIMEZONE        = 'Asia/Kolkata'
    CELERY_ENABLE_UTC      = True
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_RESULT_EXPIRES = 3600   # 1 hour

    # ── Flask-Caching (Redis) ─────────────────
    CACHE_TYPE              = 'RedisCache'
    CACHE_DEFAULT_TIMEOUT   = 300
    CACHE_REDIS_URL         = REDIS_URL

    # ── Flask-Mail ────────────────────────────
    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower() == 'true'
    MAIL_USE_SSL  = os.environ.get('MAIL_USE_SSL',  'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'HMS System <noreply@hms.com>'
    )

    # ── Google Chat Webhook (optional) ────────
    GCHAT_WEBHOOK_URL = os.environ.get('GCHAT_WEBHOOK_URL', '')
