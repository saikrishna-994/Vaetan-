"""
Vaetan — app/utils/pdf_generator.py
Generates professional PDF payslips using ReportLab.

IMPORTANT: Never use the Unicode ₹ symbol with ReportLab's base fonts —
it renders as a black box. We use "Rs." as the currency prefix instead,
which is also a standard convention on printed Indian payslips.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ── Brand colors (matching Vaetan's dark UI accent) ─────────────
ACCENT      = colors.HexColor("#6C63FF")
ACCENT_SOFT = colors.HexColor("#F0EFFF")
TEXT_DARK   = colors.HexColor("#1A1A2E")
TEXT_GREY   = colors.HexColor("#6B7280")
BORDER      = colors.HexColor("#E5E7EB")
GREEN       = colors.HexColor("#16A34A")


def fmt(amount) -> str:
    """Format a number as 'Rs. 12,345.00'"""
    return f"Rs. {float(amount):,.2f}"


def generate_payslip_pdf(payroll, output_path: str) -> str:
    """
    Build a professional payslip PDF for one Payroll record.
    `payroll` is a Payroll model instance (with .employee loaded).
    Returns the output_path on success.
    """
    emp = payroll.employee

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=20*mm, bottomMargin=20*mm,
        leftMargin=20*mm, rightMargin=20*mm,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Custom styles ────────────────────────────────────────
    company_style = ParagraphStyle(
        "Company", parent=styles["Heading1"],
        fontSize=20, textColor=ACCENT, spaceAfter=2, fontName="Helvetica-Bold"
    )
    tagline_style = ParagraphStyle(
        "Tagline", parent=styles["Normal"],
        fontSize=9, textColor=TEXT_GREY, spaceAfter=14
    )
    title_style = ParagraphStyle(
        "SlipTitle", parent=styles["Heading2"],
        fontSize=13, textColor=TEXT_DARK, spaceAfter=2
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=9, textColor=TEXT_GREY
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontSize=10, textColor=TEXT_DARK
    )
    section_header_style = ParagraphStyle(
        "SectionHeader", parent=styles["Normal"],
        fontSize=10, textColor=colors.white, fontName="Helvetica-Bold"
    )

    # ── Header: company + payslip title ─────────────────────
    story.append(Paragraph("Vaetan", company_style))
    story.append(Paragraph("Smart HR, Seamless Pay.", tagline_style))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=14))

    story.append(Paragraph(f"Payslip for {payroll.period_label}", title_style))
    story.append(Spacer(1, 4*mm))

    # ── Employee info table (2 columns) ─────────────────────
    emp_info = [
        [Paragraph("Employee Name", label_style),     Paragraph(emp.full_name, value_style),
         Paragraph("Employee Code", label_style),     Paragraph(emp.employee_code, value_style)],
        [Paragraph("Designation", label_style),       Paragraph(emp.designation, value_style),
         Paragraph("Department", label_style),        Paragraph(emp.department, value_style)],
        [Paragraph("Bank Account", label_style),      Paragraph(emp.bank_account_no or "—", value_style),
         Paragraph("PAN Number", label_style),        Paragraph(emp.pan_number or "—", value_style)],
        [Paragraph("Pay Period", label_style),         Paragraph(payroll.period_label, value_style),
         Paragraph("Status", label_style),             Paragraph(payroll.status.title(), value_style)],
    ]
    emp_table = Table(emp_info, colWidths=[32*mm, 60*mm, 32*mm, 46*mm])
    emp_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 6*mm))

    # ── Earnings & Deductions side-by-side ──────────────────
    earnings_rows = [
        [Paragraph("EARNINGS", section_header_style), ""],
        ["Basic Salary",        fmt(payroll.basic_salary)],
        ["HRA",                 fmt(payroll.hra)],
        ["DA",                  fmt(payroll.da)],
        ["Special Allowance",   fmt(payroll.special_allowance)],
        ["Travel Allowance",    fmt(payroll.travel_allowance)],
    ]
    if float(payroll.overtime_pay) > 0:
        earnings_rows.append(["Overtime Pay", fmt(payroll.overtime_pay)])
    if float(payroll.bonus) > 0:
        earnings_rows.append(["Bonus", fmt(payroll.bonus)])
    earnings_rows.append(["Gross Pay", fmt(payroll.gross_pay)])

    deductions_rows = [
        [Paragraph("DEDUCTIONS", section_header_style), ""],
        ["PF (12% of Basic)",   fmt(payroll.pf_deduction)],
        ["ESI",                 fmt(payroll.esi_deduction)],
        ["TDS",                 fmt(payroll.tds_deduction)],
    ]
    if float(payroll.absent_deduction) > 0:
        deductions_rows.append(["Loss of Pay", fmt(payroll.absent_deduction)])
    if float(payroll.other_deductions) > 0:
        deductions_rows.append(["Other Deductions", fmt(payroll.other_deductions)])
    deductions_rows.append(["Total Deductions", fmt(payroll.total_deductions)])

    # Pad shorter table to match row count
    while len(deductions_rows) < len(earnings_rows):
        deductions_rows.insert(-1, ["", ""])
    while len(earnings_rows) < len(deductions_rows):
        earnings_rows.insert(-1, ["", ""])

    earn_table = Table(earnings_rows, colWidths=[48*mm, 32*mm])
    earn_table.setStyle(TableStyle([
        ("SPAN", (0,0), (1,0)),
        ("BACKGROUND", (0,0), (1,0), ACCENT),
        ("TOPPADDING", (0,0), (1,0), 6),
        ("BOTTOMPADDING", (0,0), (1,0), 6),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("LINEBELOW", (0,1), (-1,-2), 0.5, BORDER),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LINEABOVE", (0,-1), (-1,-1), 1, TEXT_DARK),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
        ("TEXTCOLOR", (0,-1), (-1,-1), GREEN),
    ]))

    ded_table = Table(deductions_rows, colWidths=[48*mm, 32*mm])
    ded_table.setStyle(TableStyle([
        ("SPAN", (0,0), (1,0)),
        ("BACKGROUND", (0,0), (1,0), colors.HexColor("#EF4444")),
        ("TOPPADDING", (0,0), (1,0), 6),
        ("BOTTOMPADDING", (0,0), (1,0), 6),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("LINEBELOW", (0,1), (-1,-2), 0.5, BORDER),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LINEABOVE", (0,-1), (-1,-1), 1, TEXT_DARK),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.HexColor("#DC2626")),
    ]))

    side_by_side = Table([[earn_table, ded_table]], colWidths=[85*mm, 85*mm])
    side_by_side.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(side_by_side)
    story.append(Spacer(1, 6*mm))

    # ── Net Pay banner ───────────────────────────────────────
    net_table = Table(
        [["NET PAY", fmt(payroll.net_pay)]],
        colWidths=[110*mm, 60*mm]
    )
    net_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ACCENT_SOFT),
        ("TEXTCOLOR", (0,0), (0,0), TEXT_DARK),
        ("TEXTCOLOR", (1,0), (1,0), ACCENT),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (0,0), 11),
        ("FONTSIZE", (1,0), (1,0), 16),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("BOX", (0,0), (-1,-1), 1, ACCENT),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 6*mm))

    # ── Attendance summary ───────────────────────────────────
    att_rows = [[
        Paragraph("Working Days", label_style),
        Paragraph("Present", label_style),
        Paragraph("Absent", label_style),
        Paragraph("On Leave", label_style),
    ], [
        Paragraph(str(payroll.working_days), value_style),
        Paragraph(str(payroll.days_present), value_style),
        Paragraph(str(payroll.days_absent), value_style),
        Paragraph(str(payroll.days_leave), value_style),
    ]]
    att_table = Table(att_rows, colWidths=[42.5*mm]*4)
    att_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(att_table)
    story.append(Spacer(1, 10*mm))

    # ── Footer ────────────────────────────────────────────────
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=TEXT_GREY, alignment=TA_CENTER
    )
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
    story.append(Paragraph(
        "This is a system-generated payslip and does not require a signature.",
        footer_style
    ))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p')} via Vaetan HR Platform",
        footer_style
    ))

    doc.build(story)
    return output_path
