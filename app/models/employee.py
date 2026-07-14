"""
Vaetan — HR Payroll Management System
app/models/employee.py  |  Employee profile + salary structure
"""

from datetime import date, datetime, timezone
from app import db


class Employee(db.Model):
    """
    Full employee profile — personal info, job info, salary breakdown.
    Linked 1-to-1 with User (login account).
    """

    __tablename__ = "employees"

    # ── Primary key ───────────────────────────────────────────
    id                = db.Column(db.Integer, primary_key=True)

    # ── Link to login account ─────────────────────────────────
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # ── Personal details ──────────────────────────────────────
    employee_code     = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g. EMP001
    phone             = db.Column(db.String(15), nullable=True)
    date_of_birth     = db.Column(db.Date, nullable=True)
    gender            = db.Column(
        db.Enum("male", "female", "other", name="gender_enum"),
        nullable=True
    )
    address           = db.Column(db.Text, nullable=True)
    photo_path        = db.Column(db.String(255), nullable=True)    # relative path under /static/uploads/

    # ── Job details ───────────────────────────────────────────
    department        = db.Column(db.String(100), nullable=False)
    designation       = db.Column(db.String(100), nullable=False)
    employment_type   = db.Column(
        db.Enum("full_time", "part_time", "contract", "intern", name="employment_type_enum"),
        nullable=False,
        default="full_time"
    )
    join_date         = db.Column(db.Date, nullable=False, default=date.today)
    exit_date         = db.Column(db.Date, nullable=True)           # null = still employed

    # ── Bank details (for payslip) ────────────────────────────
    bank_name         = db.Column(db.String(100), nullable=True)
    bank_account_no   = db.Column(db.String(30),  nullable=True)
    ifsc_code         = db.Column(db.String(15),  nullable=True)
    pan_number        = db.Column(db.String(15),  nullable=True)    # for TDS

    # ── Salary structure (monthly, in ₹) ──────────────────────
    basic_salary      = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    hra               = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # House Rent Allowance
    da                = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # Dearness Allowance
    special_allowance = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    travel_allowance  = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # ── Status ────────────────────────────────────────────────
    status            = db.Column(
        db.Enum("active", "inactive", "on_leave", "terminated", name="emp_status_enum"),
        nullable=False,
        default="active",
        index=True
    )

    # ── AI: attrition risk score (updated periodically) ───────
    risk_score        = db.Column(db.Float, nullable=True)          # 1.0 (low) to 10.0 (high)
    risk_updated_at   = db.Column(db.DateTime, nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at        = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────
    user              = db.relationship("User", back_populates="employee")
    attendance_records = db.relationship(
        "Attendance",
        back_populates="employee",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    payroll_records   = db.relationship(
        "Payroll",
        back_populates="employee",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ── Computed properties ───────────────────────────────────
    @property
    def gross_salary(self) -> float:
        """Sum of all salary components."""
        return float(
            self.basic_salary + self.hra + self.da +
            self.special_allowance + self.travel_allowance
        )

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else "—"

    @property
    def email(self) -> str:
        return self.user.email if self.user else "—"

    @property
    def years_of_service(self) -> float:
        end = self.exit_date or date.today()
        return round((end - self.join_date).days / 365.25, 1)

    @property
    def risk_label(self) -> str:
        """Human-readable risk level from numeric score."""
        if self.risk_score is None:
            return "unknown"
        if self.risk_score <= 3:
            return "low"
        if self.risk_score <= 6:
            return "medium"
        return "high"

    @property
    def risk_color(self) -> str:
        colors = {"low": "green", "medium": "amber", "high": "red", "unknown": "grey"}
        return colors[self.risk_label]

    # ── Class methods ─────────────────────────────────────────
    @classmethod
    def generate_code(cls) -> str:
        """Auto-generate next employee code e.g. EMP042."""
        last = cls.query.order_by(cls.id.desc()).first()
        next_id = (last.id + 1) if last else 1
        return f"EMP{next_id:03d}"

    def __repr__(self) -> str:
        return f"<Employee {self.employee_code} | {self.full_name}>"
