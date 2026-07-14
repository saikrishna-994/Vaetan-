"""
Vaetan — HR Payroll Management System
app/models/attendance.py  |  Daily attendance record
"""

from datetime import date, datetime, time, timezone
from app import db


class Attendance(db.Model):
    """
    One row per employee per working day.
    Tracks status, check-in/out times, and late flags.
    """

    __tablename__ = "attendance"

    # Composite unique constraint — one record per employee per date
    __table_args__ = (
        db.UniqueConstraint("employee_id", "date", name="uq_attendance_emp_date"),
    )

    # ── Primary key ───────────────────────────────────────────
    id            = db.Column(db.Integer, primary_key=True)

    # ── Foreign key ───────────────────────────────────────────
    employee_id   = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Date ──────────────────────────────────────────────────
    date          = db.Column(db.Date, nullable=False, index=True, default=date.today)

    # ── Status ────────────────────────────────────────────────
    status        = db.Column(
        db.Enum(
            "present",
            "absent",
            "half_day",
            "on_leave",
            "holiday",
            "weekend",
            name="attendance_status_enum"
        ),
        nullable=False,
        default="present"
    )

    # ── Time tracking ─────────────────────────────────────────
    check_in      = db.Column(db.Time, nullable=True)
    check_out     = db.Column(db.Time, nullable=True)

    # ── Late flag (auto-set if check_in > LATE_THRESHOLD) ─────
    is_late       = db.Column(db.Boolean, default=False, nullable=False)
    LATE_THRESHOLD = time(9, 30)   # 09:30 AM

    # ── Leave type (when status = on_leave) ───────────────────
    leave_type    = db.Column(
        db.Enum("casual", "sick", "earned", "unpaid", name="leave_type_enum"),
        nullable=True
    )

    # ── Notes ─────────────────────────────────────────────────
    notes         = db.Column(db.String(255), nullable=True)

    # ── Marked by ─────────────────────────────────────────────
    marked_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    marked_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Relationships ─────────────────────────────────────────
    employee      = db.relationship("Employee", back_populates="attendance_records")
    marked_by     = db.relationship("User", foreign_keys=[marked_by_id])

    # ── Computed properties ───────────────────────────────────
    @property
    def hours_worked(self) -> float | None:
        """Return hours worked as float, or None if times missing."""
        if self.check_in and self.check_out:
            ci = datetime.combine(self.date, self.check_in)
            co = datetime.combine(self.date, self.check_out)
            delta = co - ci
            return round(delta.seconds / 3600, 2)
        return None

    @property
    def status_badge_color(self) -> str:
        colors = {
            "present":  "green",
            "absent":   "red",
            "half_day": "amber",
            "on_leave": "blue",
            "holiday":  "purple",
            "weekend":  "grey",
        }
        return colors.get(self.status, "grey")

    # ── Hooks ─────────────────────────────────────────────────
    def auto_flag_late(self) -> None:
        """Call after setting check_in to auto-update is_late."""
        if self.check_in:
            self.is_late = self.check_in > self.LATE_THRESHOLD

    # ── Class helpers ─────────────────────────────────────────
    @classmethod
    def get_monthly(cls, employee_id: int, year: int, month: int):
        """Fetch all attendance rows for one employee in a given month."""
        from sqlalchemy import extract
        return cls.query.filter(
            cls.employee_id == employee_id,
            extract("year",  cls.date) == year,
            extract("month", cls.date) == month,
        ).order_by(cls.date).all()

    @classmethod
    def monthly_summary(cls, employee_id: int, year: int, month: int) -> dict:
        """Return count of each status for the month."""
        records = cls.get_monthly(employee_id, year, month)
        summary = {"present": 0, "absent": 0, "half_day": 0, "on_leave": 0, "late": 0}
        for r in records:
            if r.status in summary:
                summary[r.status] += 1
            if r.is_late:
                summary["late"] += 1
        summary["total"] = len(records)
        # attendance % — half-day counts as 0.5
        worked = summary["present"] + summary["half_day"] * 0.5
        summary["percentage"] = round((worked / summary["total"]) * 100, 1) if summary["total"] else 0
        return summary

    def __repr__(self) -> str:
        return f"<Attendance emp={self.employee_id} date={self.date} status={self.status}>"
