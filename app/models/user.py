"""
Vaetan — HR Payroll Management System
app/models/user.py  |  User model (authentication + roles)
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """
    Stores login credentials and role for every system user.

    Roles
    -----
    admin       — full access to everything
    hr_manager  — can manage employees, payroll, attendance
    employee    — can only view their own payslips & attendance
    """

    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)

    # ── Identity ──────────────────────────────────────────────
    full_name     = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # ── Role ──────────────────────────────────────────────────
    role          = db.Column(
        db.Enum("admin", "hr_manager", "employee", name="user_role"),
        nullable=False,
        default="employee"
    )

    # ── Status ────────────────────────────────────────────────
    is_active     = db.Column(db.Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime, nullable=True)

    # ── Relationship ──────────────────────────────────────────
    employee      = db.relationship(
        "Employee",
        back_populates="user",
        uselist=False,
        lazy="select"
    )

    # ── Flask-Login required ──────────────────────────────────
    def get_id(self) -> str:
        return str(self.id)

    # ── Role helpers ──────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_hr_manager(self) -> bool:
        return self.role in ("admin", "hr_manager")

    # ── Password helpers ──────────────────────────────────────
    def set_password(self, raw_password: str) -> None:
        """Hash and store password — never store plain text."""
        from app import bcrypt
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """Return True if raw_password matches stored hash."""
        from app import bcrypt
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def record_login(self) -> None:
        """Update last_login timestamp on successful login."""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()

    def __repr__(self) -> str:
        return f"<User {self.id} | {self.email} | {self.role}>"
