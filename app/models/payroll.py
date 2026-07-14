"""
Vaetan — HR Payroll Management System
app/models/payroll.py  |  Monthly payroll calculation record
"""

from datetime import datetime, timezone
from decimal import Decimal
from flask import current_app
from app import db


class Payroll(db.Model):
    """
    One row per employee per month.
    Stores every earning and deduction component, net pay,
    and the approval/lock status for that month's payroll run.
    """

    __tablename__ = "payroll"

    # One payroll record per employee per month
    __table_args__ = (
        db.UniqueConstraint("employee_id", "month", "year", name="uq_payroll_emp_month"),
    )

    # ── Primary key ───────────────────────────────────────────
    id                  = db.Column(db.Integer, primary_key=True)

    # ── Foreign key ───────────────────────────────────────────
    employee_id         = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Pay period ────────────────────────────────────────────
    month               = db.Column(db.Integer, nullable=False)   # 1–12
    year                = db.Column(db.Integer, nullable=False)

    # ── Working days context ──────────────────────────────────
    working_days        = db.Column(db.Integer, nullable=False, default=26)   # total working days in month
    days_present        = db.Column(db.Integer, nullable=False, default=0)    # actual days worked (incl. 0.5 for half-day)
    days_absent         = db.Column(db.Integer, nullable=False, default=0)
    days_leave          = db.Column(db.Integer, nullable=False, default=0)

    # ── Earnings (₹) ──────────────────────────────────────────
    basic_salary        = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    hra                 = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    da                  = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    special_allowance   = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    travel_allowance    = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    overtime_pay        = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    bonus               = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # ── Deductions (₹) ────────────────────────────────────────
    pf_deduction        = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # 12% of basic
    esi_deduction       = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # 0.75% of gross (if eligible)
    tds_deduction       = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # as per income slab
    other_deductions    = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # loans, advances
    absent_deduction    = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # LOP (Loss of Pay)

    # ── Totals (stored for fast reads & payslip rendering) ────
    gross_pay           = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_deductions    = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    net_pay             = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # ── Status ────────────────────────────────────────────────
    status              = db.Column(
        db.Enum("draft", "approved", "locked", "cancelled", name="payroll_status_enum"),
        nullable=False,
        default="draft",
        index=True
    )

    # ── AI anomaly flag ───────────────────────────────────────
    anomaly_flag        = db.Column(db.Boolean, default=False)
    anomaly_reason      = db.Column(db.Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────
    approved_by_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at         = db.Column(db.DateTime, nullable=True)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at          = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ─────────────────────────────────────────
    employee            = db.relationship("Employee", back_populates="payroll_records")
    approved_by         = db.relationship("User", foreign_keys=[approved_by_id])
    payslip             = db.relationship(
        "Payslip",
        back_populates="payroll",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # ── Core calculation method ───────────────────────────────
    def calculate(self) -> "Payroll":
        """
        Run the full payroll calculation using Indian statutory rules.
        Call this after setting employee and attendance data.
        Always call db.session.commit() after this method.
        """
        emp = self.employee
        cfg = current_app.config

        # 1. Copy salary structure from employee profile
        self.basic_salary      = emp.basic_salary
        self.hra               = emp.hra
        self.da                = emp.da
        self.special_allowance = emp.special_allowance
        self.travel_allowance  = emp.travel_allowance

        # 2. Loss-of-pay deduction for absent days
        per_day = float(emp.gross_salary) / self.working_days
        self.absent_deduction = Decimal(str(round(per_day * self.days_absent, 2)))

        # 3. Gross pay (before deductions) — attendance-adjusted
        self.gross_pay = Decimal(str(
            float(self.basic_salary + self.hra + self.da +
                  self.special_allowance + self.travel_allowance +
                  self.overtime_pay + self.bonus)
            - float(self.absent_deduction)
        ))

        # 4. PF — 12% of basic salary (not gross)
        self.pf_deduction = Decimal(str(
            round(float(self.basic_salary) * cfg["PF_RATE"], 2)
        ))

        # 5. ESI — 0.75% of gross, only if gross <= ₹21,000
        if float(self.gross_pay) <= cfg["ESI_SALARY_LIMIT"]:
            self.esi_deduction = Decimal(str(
                round(float(self.gross_pay) * cfg["ESI_RATE"], 2)
            ))
        else:
            self.esi_deduction = Decimal("0.00")

        # 6. TDS — simple annual slab estimation
        self.tds_deduction = Decimal(str(self._estimate_monthly_tds()))

        # 7. Totals
        self.total_deductions = (
            self.pf_deduction + self.esi_deduction +
            self.tds_deduction + self.other_deductions +
            self.absent_deduction
        )
        self.net_pay = self.gross_pay - self.total_deductions

        return self

    def _estimate_monthly_tds(self) -> float:
        """
        Estimate monthly TDS based on projected annual income.
        Uses simplified new-regime slabs (FY 2024-25).
        """
        annual = float(self.gross_pay) * 12
        if annual <= 300000:
            tax = 0
        elif annual <= 600000:
            tax = (annual - 300000) * 0.05
        elif annual <= 900000:
            tax = 15000 + (annual - 600000) * 0.10
        elif annual <= 1200000:
            tax = 45000 + (annual - 900000) * 0.15
        elif annual <= 1500000:
            tax = 90000 + (annual - 1200000) * 0.20
        else:
            tax = 150000 + (annual - 1500000) * 0.30
        # Add 4% health & education cess
        tax = tax * 1.04
        return round(tax / 12, 2)

    def approve(self, approved_by_user_id: int) -> None:
        self.status          = "approved"
        self.approved_by_id  = approved_by_user_id
        self.approved_at     = datetime.now(timezone.utc)

    def lock(self) -> None:
        """Lock prevents any further edits — called after payslip is generated."""
        self.status = "locked"

    @property
    def period_label(self) -> str:
        """e.g.  'June 2025'"""
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"

    @property
    def is_editable(self) -> bool:
        return self.status == "draft"

    def __repr__(self) -> str:
        return f"<Payroll emp={self.employee_id} {self.period_label} net=₹{self.net_pay} [{self.status}]>"
