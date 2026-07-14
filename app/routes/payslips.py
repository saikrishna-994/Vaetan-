"""
Vaetan — app/routes/payslips.py
Handles: /payslips  /payslips/<payroll_id>/generate  /payslips/<payroll_id>/download
Role-aware: HR/admin see all payslips, employees see only their own.
"""
import os
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, send_from_directory, current_app, abort)
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models.payroll import Payroll
from app.models.payslip import Payslip
from app.utils.pdf_generator import generate_payslip_pdf

payslips_bp = Blueprint("payslips", __name__)


# ── LIST ─────────────────────────────────────────────────────
@payslips_bp.route("/")
@login_required
def index():
    if current_user.is_hr_manager:
        records = Payroll.query.filter(
            Payroll.status.in_(["approved", "locked"])
        ).order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    else:
        emp = current_user.employee
        records = [] if not emp else Payroll.query.filter_by(employee_id=emp.id).filter(
            Payroll.status.in_(["approved", "locked"])
        ).order_by(Payroll.year.desc(), Payroll.month.desc()).all()

    return render_template("payslips/index.html", records=records)


# ── GENERATE PDF (creates file if not already generated) ───────
@payslips_bp.route("/<int:payroll_id>/generate", methods=["POST"])
@login_required
def generate(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    _authorize_access(record)

    if record.status not in ("approved", "locked"):
        flash("Only approved payroll can have a payslip generated.", "danger")
        return redirect(url_for("payslips.index"))

    # Get or create the Payslip row
    payslip = record.payslip
    if not payslip:
        payslip = Payslip(payroll_id=record.id)
        db.session.add(payslip)
        db.session.flush()

    # Build the PDF
    filename    = Payslip.build_filename(record.employee.employee_code, record.month, record.year)
    rel_path    = Payslip.build_pdf_path(record.employee.employee_code, record.month, record.year)
    upload_dir  = os.path.join(current_app.static_folder, "payslips")
    os.makedirs(upload_dir, exist_ok=True)
    full_path   = os.path.join(upload_dir, filename)

    generate_payslip_pdf(record, full_path)
    payslip.mark_generated(rel_path, current_user.id)
    db.session.commit()

    flash(f"Payslip generated for {record.employee.full_name} — {record.period_label}.", "success")
    return redirect(url_for("payslips.index"))


# ── DOWNLOAD PDF ─────────────────────────────────────────────
@payslips_bp.route("/<int:payroll_id>/download")
@login_required
def download(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    _authorize_access(record)

    payslip = record.payslip
    if not payslip or not payslip.pdf_exists:
        # Auto-generate on the fly if missing
        filename   = Payslip.build_filename(record.employee.employee_code, record.month, record.year)
        rel_path   = Payslip.build_pdf_path(record.employee.employee_code, record.month, record.year)
        upload_dir = os.path.join(current_app.static_folder, "payslips")
        os.makedirs(upload_dir, exist_ok=True)
        full_path  = os.path.join(upload_dir, filename)
        generate_payslip_pdf(record, full_path)

        if not payslip:
            payslip = Payslip(payroll_id=record.id)
            db.session.add(payslip)
        payslip.mark_generated(rel_path, current_user.id)
        db.session.commit()

    directory = os.path.join(current_app.static_folder, "payslips")
    filename  = payslip.filename
    return send_from_directory(directory, filename, as_attachment=True)


# ── EMAIL PDF to employee ───────────────────────────────────────
@payslips_bp.route("/<int:payroll_id>/email", methods=["POST"])
@login_required
def email_payslip(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    _authorize_access(record, hr_only=True)   # only HR can trigger emails

    payslip = record.payslip
    if not payslip or not payslip.pdf_exists:
        flash("Generate the payslip PDF first before emailing.", "danger")
        return redirect(url_for("payslips.index"))

    try:
        full_path = os.path.join(current_app.static_folder, payslip.pdf_path)
        msg = Message(
            subject=f"Your Payslip — {record.period_label} | Vaetan",
            recipients=[record.employee.email],
            body=(
                f"Hi {record.employee.full_name.split()[0]},\n\n"
                f"Your payslip for {record.period_label} is attached.\n"
                f"Net Pay: Rs. {float(record.net_pay):,.2f}\n\n"
                f"— Vaetan HR Team"
            ),
        )
        with open(full_path, "rb") as f:
            msg.attach(payslip.filename, "application/pdf", f.read())
        mail.send(msg)

        payslip.mark_emailed(record.employee.email)
        db.session.commit()
        flash(f"Payslip emailed to {record.employee.email}.", "success")
    except Exception as e:
        flash(f"Email failed: {str(e)}. Check your MAIL_USERNAME/MAIL_PASSWORD in .env", "danger")

    return redirect(url_for("payslips.index"))


# ── helpers ──────────────────────────────────────────────────
def _authorize_access(record: Payroll, hr_only: bool = False) -> None:
    """Abort 403 unless current_user is HR/admin or owns this payroll record."""
    if current_user.is_hr_manager:
        return
    if hr_only:
        abort(403)
    emp = current_user.employee
    if not emp or emp.id != record.employee_id:
        abort(403)
