"""
backend/celery_worker.py
Celery application factory + Beat periodic schedule.

Run worker:
    celery -A celery_worker.celery worker --loglevel=info

Run beat (scheduler):
    celery -A celery_worker.celery beat --loglevel=info

Run both together (dev only):
    celery -A celery_worker.celery worker --beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab


def make_celery(app):
    """Bind Celery to Flask app context."""
    celery = Celery(
        app.import_name,
        broker  = app.config['CELERY_BROKER_URL'],
        backend = app.config['CELERY_RESULT_BACKEND'],
    )
    celery.conf.update(app.config)

    # ── Beat periodic schedule ──────────────────
    celery.conf.beat_schedule = {

        # Daily reminder — every morning at 07:00
        'daily-appointment-reminders': {
            'task':     'tasks.reminders.send_daily_reminders',
            'schedule': crontab(hour=7, minute=0),
        },

        # Monthly report — 1st of every month at 06:00
        'monthly-doctor-reports': {
            'task':     'tasks.reports.send_monthly_reports',
            'schedule': crontab(day_of_month=1, hour=6, minute=0),
        },
    }
    celery.conf.timezone = 'Asia/Kolkata'

    class ContextTask(celery.Task):
        """Execute every task inside Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# ── Bootstrap ──────────────────────────────────
from app import create_app

flask_app = create_app()
celery    = make_celery(flask_app)

# Import task modules so Celery auto-discovers them
import tasks.reminders  # noqa: F401
import tasks.reports    # noqa: F401
import tasks.exports    # noqa: F401
