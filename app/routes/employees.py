"""
Vaetan — app/routes/employees.py
Handles: /employees  /employees/add  /employees/<id>/edit  /employees/<id>/delete
"""
import os, csv
from datetime import date
from io import StringIO
from flask import (Blueprint, render_template, redirect, url_for,
                   request, flash, current_app, make_response)
from flask_login import login_required, current_user
from app.utils.decorators import hr_required
from app import db
from app.models.user     import User
from app.models.employee import Employee

employees_bp = Blueprint("employees", __name__)


# ── helpers ──────────────────────────────────────────────────
def _allowed_file(filename: str) -> bool:
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in \
           current_app.config.get("ALLOWED_EXTENSIONS", {"png","jpg","jpeg","webp"})


def _save_photo(file) -> str | None:
    """Save uploaded photo and return relative path."""
    if not file or file.filename == "":
        return None
    if not _allowed_file(file.filename):
        return None
    ext      = file.filename.rsplit(".", 1)[1].lower()
    filename = f"emp_{int(__import__('time').time())}.{ext}"
    upload_dir = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))
    return f"uploads/{filename}"


# ── LIST ─────────────────────────────────────────────────────
@employees_bp.route("/")
@login_required
@hr_required
def index():
    status_filter = request.args.get("status", "active")
    search        = request.args.get("q", "").strip()
    dept_filter   = request.args.get("dept", "")

    query = Employee.query
    if status_filter and status_filter != "all":
        query = query.filter_by(status=status_filter)
    if search:
        query = query.join(User).filter(
            db.or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                Employee.department.ilike(f"%{search}%"),
                Employee.designation.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
            )
        )
    if dept_filter:
        query = query.filter_by(department=dept_filter)

    employees = query.order_by(Employee.created_at.desc()).all()

    # Dept list for filter dropdown
    all_depts = [d[0] for d in db.session.query(Employee.department).distinct().all()]

    # Counts for tab badges
    counts = {
        "all":      Employee.query.count(),
        "active":   Employee.query.filter_by(status="active").count(),
        "inactive": Employee.query.filter_by(status="inactive").count(),
        "on_leave": Employee.query.filter_by(status="on_leave").count(),
    }

    return render_template(
        "employees/index.html",
        employees     = employees,
        status_filter = status_filter,
        search        = search,
        dept_filter   = dept_filter,
        all_depts     = all_depts,
        counts        = counts,
    )


# ── CSV EXPORT ────────────────────────────────────────────────
@employees_bp.route("/export")
@login_required
@hr_required
def export_csv():
    employees = Employee.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Code","Name","Email","Department","Designation","Type","Join Date","Basic Salary","Gross","Status"])
    for e in employees:
        writer.writerow([
            e.employee_code, e.full_name, e.email,
            e.department, e.designation, e.employment_type,
            e.join_date, float(e.basic_salary), float(e.gross_salary), e.status
        ])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=employees.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ── ADD ───────────────────────────────────────────────────────
@employees_bp.route("/add", methods=["GET", "POST"])
@login_required
@hr_required
def add():
    if request.method == "POST":
        errors = _validate_employee_form(request.form, is_edit=False)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("employees/form.html", emp=None, form=request.form)

        # Create user account
        user = User(
            full_name = request.form["full_name"].strip(),
            email     = request.form["email"].strip().lower(),
            role      = "employee",
        )
        user.set_password(request.form.get("password", "vaetan@123"))
        db.session.add(user)
        db.session.flush()   # get user.id before commit

        # Save photo
        photo = _save_photo(request.files.get("photo"))

        # Create employee profile
        emp = Employee(
            user_id           = user.id,
            employee_code     = Employee.generate_code(),
            phone             = request.form.get("phone","").strip(),
            date_of_birth     = _parse_date(request.form.get("date_of_birth")),
            gender            = request.form.get("gender") or None,
            address           = request.form.get("address","").strip(),
            photo_path        = photo,
            department        = request.form["department"].strip(),
            designation       = request.form["designation"].strip(),
            employment_type   = request.form.get("employment_type","full_time"),
            join_date         = _parse_date(request.form.get("join_date")) or date.today(),
            bank_name         = request.form.get("bank_name","").strip(),
            bank_account_no   = request.form.get("bank_account_no","").strip(),
            ifsc_code         = request.form.get("ifsc_code","").strip(),
            pan_number        = request.form.get("pan_number","").strip(),
            basic_salary      = float(request.form.get("basic_salary") or 0),
            hra               = float(request.form.get("hra") or 0),
            da                = float(request.form.get("da") or 0),
            special_allowance = float(request.form.get("special_allowance") or 0),
            travel_allowance  = float(request.form.get("travel_allowance") or 0),
            status            = "active",
        )
        db.session.add(emp)
        db.session.commit()
        flash(f"Employee {emp.employee_code} — {emp.full_name} added successfully!", "success")
        return redirect(url_for("employees.index"))

    return render_template("employees/form.html", emp=None, form={})


# ── EDIT ──────────────────────────────────────────────────────
@employees_bp.route("/<int:emp_id>/edit", methods=["GET", "POST"])
@login_required
@hr_required
def edit(emp_id):
    emp = Employee.query.get_or_404(emp_id)

    if request.method == "POST":
        errors = _validate_employee_form(request.form, is_edit=True, emp=emp)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("employees/form.html", emp=emp, form=request.form)

        # Update user
        emp.user.full_name = request.form["full_name"].strip()
        if request.form["email"].strip().lower() != emp.user.email:
            emp.user.email = request.form["email"].strip().lower()

        # Update photo
        new_photo = _save_photo(request.files.get("photo"))
        if new_photo:
            emp.photo_path = new_photo

        # Update employee fields
        emp.phone             = request.form.get("phone","").strip()
        emp.date_of_birth     = _parse_date(request.form.get("date_of_birth"))
        emp.gender            = request.form.get("gender") or None
        emp.address           = request.form.get("address","").strip()
        emp.department        = request.form["department"].strip()
        emp.designation       = request.form["designation"].strip()
        emp.employment_type   = request.form.get("employment_type","full_time")
        emp.join_date         = _parse_date(request.form.get("join_date")) or emp.join_date
        emp.bank_name         = request.form.get("bank_name","").strip()
        emp.bank_account_no   = request.form.get("bank_account_no","").strip()
        emp.ifsc_code         = request.form.get("ifsc_code","").strip()
        emp.pan_number        = request.form.get("pan_number","").strip()
        emp.basic_salary      = float(request.form.get("basic_salary") or 0)
        emp.hra               = float(request.form.get("hra") or 0)
        emp.da                = float(request.form.get("da") or 0)
        emp.special_allowance = float(request.form.get("special_allowance") or 0)
        emp.travel_allowance  = float(request.form.get("travel_allowance") or 0)
        emp.status            = request.form.get("status", emp.status)

        db.session.commit()
        flash(f"{emp.full_name}'s profile updated successfully.", "success")
        return redirect(url_for("employees.index"))

    return render_template("employees/form.html", emp=emp, form={})


# ── DELETE ────────────────────────────────────────────────────
@employees_bp.route("/<int:emp_id>/delete", methods=["POST"])
@login_required
@hr_required
def delete(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    name = emp.full_name
    db.session.delete(emp.user)   # cascade deletes employee too
    db.session.commit()
    flash(f"{name} has been removed from the system.", "info")
    return redirect(url_for("employees.index"))


# ── Helpers ───────────────────────────────────────────────────
def _parse_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def _validate_employee_form(form, is_edit=False, emp=None):
    errors = []
    if not form.get("full_name","").strip():
        errors.append("Full name is required.")
    email = form.get("email","").strip().lower()
    if not email:
        errors.append("Email is required.")
    else:
        existing = User.query.filter_by(email=email).first()
        if existing and (not is_edit or existing.id != emp.user_id):
            errors.append(f"Email {email} is already in use.")
    if not form.get("department","").strip():
        errors.append("Department is required.")
    if not form.get("designation","").strip():
        errors.append("Designation is required.")
    try:
        if float(form.get("basic_salary") or 0) < 0:
            errors.append("Basic salary cannot be negative.")
    except ValueError:
        errors.append("Basic salary must be a number.")
    return errors
