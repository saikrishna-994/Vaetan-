"""
Vaetan — app/routes/payroll.py
Handles: /payroll  /payroll/run  /payroll/<id>/approve  /payroll/<id>/lock  /payroll/<id>/recalculate
"""
import calendar as calmod
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.decorators import hr_required
from app import db
from app.models.employee   import Employee
from app.models.attendance import Attendance
from app.models.payroll    import Payroll

payroll_bp = Blueprint("payroll", __name__)


# ── helper: working days in a month (excluding Sundays) ────────
def _working_days(year: int, month: int) -> int:
    days_in_month = calmod.monthrange(year, month)[1]
    working = 0
    for d in range(1, days_in_month + 1):
        if date(year, month, d).weekday() != 6:   # Sunday = 6
            working += 1
    return working


# ── LIST + selector ──────────────────────────────────────────
@payroll_bp.route("/")
@login_required
@hr_required
def index():
    year  = request.args.get("year",  type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    records = Payroll.query.filter_by(year=year, month=month)\
                .join(Employee).order_by(Employee.employee_code).all()

    # Which active employees don't have a payroll record yet this month
    existing_emp_ids = {r.employee_id for r in records}
    active_employees = Employee.query.filter_by(status="active").all()
    pending_employees = [e for e in active_employees if e.id not in existing_emp_ids]

    # Totals for summary cards
    totals = {
        "gross":      sum(float(r.gross_pay)        for r in records),
        "deductions": sum(float(r.total_deductions) for r in records),
        "net":        sum(float(r.net_pay)           for r in records),
        "approved":   sum(1 for r in records if r.status in ("approved","locked")),
        "draft":      sum(1 for r in records if r.status == "draft"),
        "anomalies":  sum(1 for r in records if r.anomaly_flag),
    }

    return render_template(
        "payroll/index.html",
        records           = records,
        pending_employees = pending_employees,
        year              = year,
        month             = month,
        month_name        = calmod.month_name[month],
        totals            = totals,
        today             = date.today(),
    )


# ── RUN PAYROLL for the month (all pending employees) ──────────
@payroll_bp.route("/run", methods=["POST"])
@login_required
@hr_required
def run():
    year  = request.form.get("year",  type=int) or date.today().year
    month = request.form.get("month", type=int) or date.today().month

    active_employees = Employee.query.filter_by(status="active").all()
    working_days = _working_days(year, month)
    created, skipped = 0, 0

    for emp in active_employees:
        existing = Payroll.query.filter_by(employee_id=emp.id, year=year, month=month).first()
        if existing:
            skipped += 1
            continue

        summary = Attendance.monthly_summary(emp.id, year, month)
        days_present = summary["present"] + summary["half_day"] * 0.5
        days_absent  = summary["absent"]
        days_leave   = summary["on_leave"]

        record = Payroll(
            employee_id   = emp.id,
            month         = month,
            year          = year,
            working_days  = working_days,
            days_present  = int(days_present),
            days_absent   = days_absent,
            days_leave    = days_leave,
            status        = "draft",
        )
        db.session.add(record)
        db.session.flush()   # populate record.employee relationship before calculate()
        record.calculate()
        _check_anomalies(record, emp)
        created += 1

    db.session.commit()
    flash(f"Payroll run complete — {created} record(s) generated, {skipped} already existed.", "success")
    return redirect(url_for("payroll.index", year=year, month=month))


# ── RECALCULATE a single record (e.g. after attendance correction) ─
@payroll_bp.route("/<int:payroll_id>/recalculate", methods=["POST"])
@login_required
@hr_required
def recalculate(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    if not record.is_editable:
        flash("Cannot recalculate — this payroll is already approved or locked.", "danger")
        return redirect(url_for("payroll.index", year=record.year, month=record.month))

    summary = Attendance.monthly_summary(record.employee_id, record.year, record.month)
    record.days_present = int(summary["present"] + summary["half_day"] * 0.5)
    record.days_absent  = summary["absent"]
    record.days_leave   = summary["on_leave"]
    record.working_days = _working_days(record.year, record.month)
    record.calculate()
    _check_anomalies(record, record.employee)
    db.session.commit()
    flash(f"Payroll recalculated for {record.employee.full_name}.", "success")
    return redirect(url_for("payroll.index", year=record.year, month=record.month))


# ── APPROVE single record ───────────────────────────────────────
@payroll_bp.route("/<int:payroll_id>/approve", methods=["POST"])
@login_required
@hr_required
def approve(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    if record.status != "draft":
        flash("Only draft payrolls can be approved.", "danger")
    else:
        record.approve(current_user.id)
        db.session.commit()
        flash(f"Payroll approved for {record.employee.full_name}.", "success")
    return redirect(url_for("payroll.index", year=record.year, month=record.month))


# ── APPROVE ALL drafts for the month ────────────────────────────
@payroll_bp.route("/approve-all", methods=["POST"])
@login_required
@hr_required
def approve_all():
    year  = request.form.get("year",  type=int)
    month = request.form.get("month", type=int)
    drafts = Payroll.query.filter_by(year=year, month=month, status="draft").all()
    for r in drafts:
        r.approve(current_user.id)
    db.session.commit()
    flash(f"{len(drafts)} payroll record(s) approved.", "success")
    return redirect(url_for("payroll.index", year=year, month=month))


# ── LOCK single record (after payslip generated) ───────────────
@payroll_bp.route("/<int:payroll_id>/lock", methods=["POST"])
@login_required
@hr_required
def lock(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    if record.status != "approved":
        flash("Only approved payrolls can be locked.", "danger")
    else:
        record.lock()
        db.session.commit()
        flash(f"Payroll locked for {record.employee.full_name}.", "info")
    return redirect(url_for("payroll.index", year=record.year, month=record.month))


# ── DETAIL view (breakdown for one employee/month) ──────────────
@payroll_bp.route("/<int:payroll_id>")
@login_required
@hr_required
def detail(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    return render_template("payroll/detail.html", record=record)


# ── Anomaly detection (rule-based, AI-ready) ────────────────────
def _check_anomalies(record: Payroll, emp: Employee) -> None:
    """
    Flags suspicious payroll entries. This is a rule-based first pass —
    swap reasons.append(...) calls with Claude API output later for the
    AI anomaly detector feature.
    """
    reasons = []

    # 1. Zero attendance but full pay
    if record.days_present == 0 and float(record.net_pay) > 0:
        reasons.append("Zero attendance recorded but salary is not zero.")

    # 2. Salary jump >20% vs last month
    prev = Payroll.query.filter_by(employee_id=emp.id)\
            .filter(Payroll.id != record.id)\
            .order_by(Payroll.year.desc(), Payroll.month.desc()).first()
    if prev and float(prev.net_pay) > 0:
        change = (float(record.net_pay) - float(prev.net_pay)) / float(prev.net_pay)
        if abs(change) > 0.20:
            direction = "increased" if change > 0 else "decreased"
            reasons.append(f"Net pay {direction} by {abs(change)*100:.0f}% vs last month.")

    # 3. Negative net pay (deductions exceed gross)
    if float(record.net_pay) < 0:
        reasons.append("Net pay is negative — deductions exceed gross pay.")

    # 4. Duplicate bank account across employees
    if emp.bank_account_no:
        dupes = Employee.query.filter(
            Employee.bank_account_no == emp.bank_account_no,
            Employee.id != emp.id
        ).count()
        if dupes > 0:
            reasons.append(f"Bank account number is shared with {dupes} other employee(s).")

    record.anomaly_flag   = bool(reasons)
    record.anomaly_reason = " | ".join(reasons) if reasons else None
