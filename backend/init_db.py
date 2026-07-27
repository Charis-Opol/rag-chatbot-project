"""
Run this once before starting the server for the first time:

    python -m backend.init_db

Creates all tables and seeds:
  - the "admin" and "staff" roles
  - one default IT Officer account (credentials from .env)
"""
from backend.database import Base, engine, SessionLocal
from backend import models
from backend.security import hash_password
from backend.config import settings


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed roles
        role_names = ["admin", "staff"]
        roles = {}
        for name in role_names:
            role = db.query(models.Role).filter(models.Role.role_name == name).first()
            if not role:
                role = models.Role(role_name=name)
                db.add(role)
                db.commit()
                db.refresh(role)
            roles[name] = role

        # Seed default admin
        existing = db.query(models.User).filter(models.User.email == settings.DEFAULT_ADMIN_EMAIL).first()
        if not existing:
            admin = models.User(
                full_name=settings.DEFAULT_ADMIN_NAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role_id=roles["admin"].role_id,
            )
            db.add(admin)
            db.commit()
            print(f"[OK] Seeded default IT Officer account: {settings.DEFAULT_ADMIN_EMAIL} / {settings.DEFAULT_ADMIN_PASSWORD}")
        else:
            print("[OK] Default admin account already exists — skipped.")

        # Seed demo staff account
        existing_staff = db.query(models.User).filter(models.User.email == settings.DEFAULT_STAFF_EMAIL).first()
        if not existing_staff:
            staff = models.User(
                full_name=settings.DEFAULT_STAFF_NAME,
                email=settings.DEFAULT_STAFF_EMAIL,
                password_hash=hash_password(settings.DEFAULT_STAFF_PASSWORD),
                role_id=roles["staff"].role_id,
            )
            db.add(staff)
            db.commit()
            print(f"[OK] Seeded demo Ministry Staff account: {settings.DEFAULT_STAFF_EMAIL} / {settings.DEFAULT_STAFF_PASSWORD}")
        else:
            print("[OK] Demo staff account already exists — skipped.")

        print("[OK] Database initialized.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
