"""
Vaetan — HR Payroll Management System
app/models/payslip.py  |  Generated payslip record
"""

import os
from datetime import datetime, timezone
from app import db


class Payslip(db.Model):
    """
    Tracks every generated PDF payslip.
    One payslip per payroll record (1-to-1).
    Stores the PDF file path and email delivery status.
    """

    __tablename__ = "payslips"

    # ── Primary key ───────────────────────────────────────────
    id              = db.Column(db.Integer, primary_key=True)

    # ── Foreign key ───────────────────────────────────────────
    payroll_id      = db.Column(
        db.Integer,
        db.ForeignKey("payroll.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # ── PDF file ──────────────────────────────────────────────
    # stored as relative path under app/static/payslips/
    # e.g.  "payslips/EMP001_June_2025.pdf"
    pdf_path        = db.Column(db.String(255), nullable=True)

    # ── Generation ────────────────────────────────────────────
    generated_at    = db.Column(db.DateTime, nullable=True)
    generated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # ── Email delivery ────────────────────────────────────────
    email_sent      = db.Column(db.Boolean, default=False, nullable=False)
    emailed_at      = db.Column(db.DateTime, nullable=True)
    email_to        = db.Column(db.String(150), nullable=True)   # snapshot of recipient at send time

    # ── AI chatbot usage log ───────────────────────────────────
    # Stores last Q&A pair so the chat UI can show history
    last_question   = db.Column(db.Text, nullable=True)
    last_answer     = db.Column(db.Text, nullable=True)
    chat_count      = db.Column(db.Integer, default=0)           # total questions asked

    # ── Timestamps ────────────────────────────────────────────
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Relationships ─────────────────────────────────────────
    payroll         = db.relationship("Payroll", back_populates="payslip")
    generated_by    = db.relationship("User", foreign_keys=[generated_by_id])

    # ── Helpers ───────────────────────────────────────────────
    @property
    def filename(self) -> str | None:
        """Just the filename, e.g. 'EMP001_June_2025.pdf'"""
        return os.path.basename(self.pdf_path) if self.pdf_path else None

    @property
    def pdf_exists(self) -> bool:
        """True if the PDF file actually exists on disk."""
        if not self.pdf_path:
            return False
        from flask import current_app
        full_path = os.path.join(current_app.static_folder, self.pdf_path)
        return os.path.isfile(full_path)

    @property
    def employee(self):
        return self.payroll.employee if self.payroll else None

    @property
    def period_label(self) -> str:
        return self.payroll.period_label if self.payroll else "—"

    def mark_generated(self, pdf_path: str, generated_by_user_id: int) -> None:
        """Call after successfully writing the PDF to disk."""
        self.pdf_path           = pdf_path
        self.generated_at       = datetime.now(timezone.utc)
        self.generated_by_id    = generated_by_user_id

    def mark_emailed(self, recipient_email: str) -> None:
        """Call after successfully sending the email."""
        self.email_sent  = True
        self.emailed_at  = datetime.now(timezone.utc)
        self.email_to    = recipient_email

    def log_chat(self, question: str, answer: str) -> None:
        """Store last AI Q&A exchange and increment counter."""
        self.last_question = question
        self.last_answer   = answer
        self.chat_count    = (self.chat_count or 0) + 1

    @classmethod
    def build_filename(cls, employee_code: str, month: int, year: int) -> str:
        """
        Generate a clean PDF filename.
        e.g.  EMP001_June_2025.pdf
        """
        import calendar
        month_name = calendar.month_name[month]
        return f"{employee_code}_{month_name}_{year}.pdf"

    @classmethod
    def build_pdf_path(cls, employee_code: str, month: int, year: int) -> str:
        """
        Return the relative path to store the PDF under /static/.
        e.g.  'payslips/EMP001_June_2025.pdf'
        """
        return os.path.join("payslips", cls.build_filename(employee_code, month, year))

    def __repr__(self) -> str:
        return f"<Payslip payroll={self.payroll_id} emailed={self.email_sent} file={self.filename}>"
