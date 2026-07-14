"""
Vaetan — app/routes/attendance.py
Handles: /attendance  /attendance/mark  /attendance/calendar/<emp_id>
"""
import calendar as cal
from datetime import date, datetime, time
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.employee   import Employee
from app.models.attendance import Attendance
from app.utils.decorators  import hr_required, employee_owns_or_hr

attendance_bp = Blueprint("attendance", __name__)


# ── DAILY VIEW + BULK MARK — HR/admin only ──────────────────────
@attendance_bp.route("/", methods=["GET", "POST"])
@login_required
@hr_required
def index():
    # Selected date (default = today)
    selected_date = request.args.get("date")
    try:
        selected_date = date.fromisoformat(selected_date) if selected_date else date.today()
    except ValueError:
        selected_date = date.today()

    if request.method == "POST":
        employees = Employee.query.filter_by(status="active").all()
        for emp in employees:
            status_key = f"status_{emp.id}"
            status_val = request.form.get(status_key)
            if not status_val:
                continue

            record = Attendance.query.filter_by(employee_id=emp.id, date=selected_date).first()
            if not record:
                record = Attendance(employee_id=emp.id, date=selected_date)
                db.session.add(record)

            record.status     = status_val
            record.marked_by_id = current_user.id

            # Check-in / check-out times (only if present or half-day)
            if status_val in ("present", "half_day"):
                ci = request.form.get(f"checkin_{emp.id}")
                co = request.form.get(f"checkout_{emp.id}")
                record.check_in  = _parse_time(ci)
                record.check_out = _parse_time(co)
                record.auto_flag_late()
            else:
                record.check_in  = None
                record.check_out = None
                record.is_late   = False

            # Leave type
            if status_val == "on_leave":
                record.leave_type = request.form.get(f"leave_type_{emp.id}") or "casual"
            else:
                record.leave_type = None

        db.session.commit()
        flash(f"Attendance saved for {selected_date.strftime('%d %b %Y')}.", "success")
        return redirect(url_for("attendance.index", date=selected_date.isoformat()))

    # ── GET ────────────────────────────────────────────────────
    employees = Employee.query.filter_by(status="active").order_by(Employee.department, Employee.employee_code).all()

    # Existing records for selected date, keyed by employee_id
    records = Attendance.query.filter_by(date=selected_date).all()
    records_by_emp = {r.employee_id: r for r in records}

    # Quick stats for the day
    stats = {
        "present":  sum(1 for r in records if r.status == "present"),
        "absent":   sum(1 for r in records if r.status == "absent"),
        "half_day": sum(1 for r in records if r.status == "half_day"),
        "on_leave": sum(1 for r in records if r.status == "on_leave"),
        "unmarked": len(employees) - len(records),
    }

    return render_template(
        "attendance/index.html",
        employees      = employees,
        records_by_emp = records_by_emp,
        selected_date  = selected_date,
        stats          = stats,
        today          = date.today(),
        timedelta      = __import__("datetime").timedelta,
    )


# ── MONTHLY CALENDAR FOR ONE EMPLOYEE — owner or HR ─────────────
@attendance_bp.route("/calendar/<int:emp_id>")
@login_required
@employee_owns_or_hr(lambda kwargs: kwargs["emp_id"])
def employee_calendar(emp_id):
    emp = Employee.query.get_or_404(emp_id)

    year  = request.args.get("year",  type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    records = Attendance.get_monthly(emp_id, year, month)
    records_by_day = {r.date.day: r for r in records}
    summary = Attendance.monthly_summary(emp_id, year, month)

    # Build calendar grid
    cal_obj   = cal.Calendar(firstweekday=0)  # Monday start
    month_days = cal_obj.itermonthdates(year, month)
    weeks = []
    week = []
    for d in month_days:
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []

    # Prev/next month navigation
    prev_month, prev_year = (12, year-1) if month == 1 else (month-1, year)
    next_month, next_year = (1, year+1)  if month == 12 else (month+1, year)

    return render_template(
        "attendance/calendar.html",
        emp             = emp,
        weeks           = weeks,
        records_by_day  = records_by_day,
        summary         = summary,
        year            = year,
        month           = month,
        month_name      = cal.month_name[month],
        prev_month      = prev_month, prev_year = prev_year,
        next_month      = next_month, next_year = next_year,
        today           = date.today(),
    )


# ── helpers ──────────────────────────────────────────────────
def _parse_time(val):
    if not val:
        return None
    try:
        return time.fromisoformat(val)
    except ValueError:
        return None
