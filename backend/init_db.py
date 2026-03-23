"""
init_db.py — Run once to:
  1. Create all tables
  2. Seed default departments
  3. Pre-create the Admin user programmatically

Usage:
    python init_db.py
"""

from app import create_app
from models import db, User, Department

DEPARTMENTS = [
    {"name": "Cardiology",       "description": "Diagnosis and treatment of heart disorders."},
    {"name": "Oncology",         "description": "Diagnosis and treatment of cancer."},
    {"name": "General Medicine", "description": "Primary and general healthcare services."},
    {"name": "Orthopedics",      "description": "Musculoskeletal system care."},
    {"name": "Neurology",        "description": "Disorders of the nervous system."},
    {"name": "Pediatrics",       "description": "Medical care for infants, children and adolescents."},
    {"name": "Dermatology",      "description": "Skin, hair and nail conditions."},
    {"name": "Gynecology",       "description": "Female reproductive health."},
]

ADMIN = {
    "username": "admin",
    "email":    "admin@hms.com",
    "password": "Admin@1234",   # ← change before production
    "role":     "admin",
}


def init_db():
    app = create_app()

    with app.app_context():
        # 1. Create all tables
        db.create_all()
        print("✅ Tables created.")

        # 2. Seed departments (skip if already exist)
        for dept_data in DEPARTMENTS:
            exists = Department.query.filter_by(name=dept_data["name"]).first()
            if not exists:
                dept = Department(**dept_data)
                db.session.add(dept)
        db.session.commit()
        print(f"✅ {len(DEPARTMENTS)} departments seeded.")

        # 3. Pre-create Admin user
        admin_exists = User.query.filter_by(role='admin').first()
        if not admin_exists:
            admin = User(
                username=ADMIN["username"],
                email=ADMIN["email"],
                role=ADMIN["role"],
                is_active=True,
            )
            admin.set_password(ADMIN["password"])
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin user created → username: '{ADMIN['username']}' | password: '{ADMIN['password']}'")
        else:
            print("ℹ️  Admin already exists — skipping.")

        print("\n🏥 Database initialised successfully!")


if __name__ == '__main__':
    init_db()
