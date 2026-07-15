"""
One-time script to create an admin user in the database.
Run:
    python create_admin.py
"""

from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    try:
        # Change this email if you want a different admin account
        email = "admin@vaetan.com"

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            print(f"Admin already exists: {existing_user.email}")
        else:
            admin = User(
                full_name="System Administrator",
                email=email,
                role="admin",
                is_active=True
            )

            # Hashes the password using Flask-Bcrypt
            admin.set_password("Admin@123")

            db.session.add(admin)
            db.session.commit()

            print("=" * 50)
            print("✅ Admin user created successfully!")
            print("Email    :", email)
            print("Password :", "Admin@123")
            print("Role     :", "admin")
            print("=" * 50)

    except Exception as e:
        db.session.rollback()
        print("❌ Failed to create admin user.")
        print(e)