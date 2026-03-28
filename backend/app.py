"""
backend/app.py — Flask application factory
Milestones: Auth · Admin · Doctor · Patient · Appointments/History/Conflict
"""

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from config import Config
from models import db

cache = Cache()
jwt   = JWTManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)

    # ── JWT error handlers ───────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({'error': 'Missing or invalid token.', 'reason': reason}), 401

    @jwt.expired_token_loader
    def expired(h, p):
        return jsonify({'error': 'Token expired. Please log in again.'}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({'error': 'Invalid token.', 'reason': reason}), 422

    # ── Blueprints ───────────────────────────
    from routes.auth         import auth_bp
    from routes.admin        import admin_bp
    from routes.doctor       import doctor_bp
    from routes.patient      import patient_bp
    from routes.appointments import appt_bp

    app.register_blueprint(auth_bp,    url_prefix='/api/auth')
    app.register_blueprint(admin_bp,   url_prefix='/api/admin')
    app.register_blueprint(doctor_bp,  url_prefix='/api/doctor')
    app.register_blueprint(patient_bp, url_prefix='/api/patient')
    app.register_blueprint(appt_bp,    url_prefix='/api/appointments')

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'HMS V2'}), 200

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
