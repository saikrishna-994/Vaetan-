"""
Vaetan — app/routes/dashboard.py
Handles: /  (branches by role — HR/admin get the full dashboard,
              employees get redirected to their own simple view)
"""
import calendar
from datetime import datetime, date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.employee   import Employee
from app.models.attendance import Attendance
from app.models.payroll    import Payroll

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    # ── Route by role ───────────────────────────────────────────
    if current_user.is_hr_manager:
        return _hr_dashboard()
    return _employee_dashboard()


# ─────────────────────────────────────────────────────────────
#  HR / Admin dashboard — full org-wide view
# ─────────────────────────────────────────────────────────────
def _hr_dashboard():
    today         = date.today()
    current_month = today.month
    current_year  = today.year

    total_employees = Employee.query.filter_by(status="active").count()
    present_today   = Attendance.query.filter_by(date=today, status="present").count()
    on_leave_today  = Attendance.query.filter_by(date=today, status="on_leave").count()
    inactive_count  = Employee.query.filter_by(status="inactive").count()

    payroll_total = db.session.query(
        func.coalesce(func.sum(Payroll.net_pay), 0)
    ).filter(
        Payroll.month == current_month,
        Payroll.year  == current_year,
        Payroll.status.in_(["approved", "locked"])
    ).scalar() or 0

    payroll_trend = []
    for i in range(5, -1, -1):
        m, y = current_month - i, current_year
        if m <= 0:
            m += 12; y -= 1
        total = db.session.query(
            func.coalesce(func.sum(Payroll.net_pay), 0)
        ).filter(
            Payroll.month == m, Payroll.year == y,
            Payroll.status.in_(["approved", "locked"])
        ).scalar() or 0
        payroll_trend.append({"label": calendar.month_abbr[m], "value": float(total)})

    dept_data   = db.session.query(Employee.department, func.count(Employee.id))\
                    .filter_by(status="active").group_by(Employee.department).all()
    dept_labels = [d[0] for d in dept_data]
    dept_counts = [d[1] for d in dept_data]

    high_risk = Employee.query.filter(
        Employee.risk_score >= 7,
        Employee.status == "active"
    ).order_by(Employee.risk_score.desc()).limit(3).all()

    recent_employees = Employee.query.order_by(Employee.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard/index.html",
        total_employees  = total_employees,
        present_today    = present_today,
        on_leave_today   = on_leave_today,
        inactive_count   = inactive_count,
        payroll_total    = payroll_total,
        payroll_trend    = payroll_trend,
        dept_labels      = dept_labels,
        dept_counts      = dept_counts,
        high_risk        = high_risk,
        recent_employees = recent_employees,
        today            = today,
        current_month    = datetime.now().strftime("%B %Y"),
    )


# ─────────────────────────────────────────────────────────────
#  Employee dashboard — only their own data
# ─────────────────────────────────────────────────────────────
def _employee_dashboard():
    emp = current_user.employee
    today = date.today()

    if not emp:
        # Edge case: a user with role=employee but no linked Employee profile
        return render_template("dashboard/employee_index.html", emp=None)

    # This month's attendance summary
    summary = Attendance.monthly_summary(emp.id, today.year, today.month)

    # Recent attendance (last 10 records)
    recent_attendance = Attendance.query.filter_by(employee_id=emp.id)\
                            .order_by(Attendance.date.desc()).limit(10).all()

    # Latest payslip
    latest_payroll = Payroll.query.filter_by(employee_id=emp.id)\
                        .filter(Payroll.status.in_(["approved", "locked"]))\
                        .order_by(Payroll.year.desc(), Payroll.month.desc()).first()

    # Payslip history count
    payslip_count = Payroll.query.filter_by(employee_id=emp.id)\
                        .filter(Payroll.status.in_(["approved", "locked"])).count()

    return render_template(
        "dashboard/employee_index.html",
        emp                = emp,
        summary            = summary,
        recent_attendance  = recent_attendance,
        latest_payroll     = latest_payroll,
        payslip_count      = payslip_count,
        today              = today,
        current_month_name = today.strftime("%B %Y"),
    )
