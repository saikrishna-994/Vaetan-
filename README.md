# Vaetan — HR & Payroll Management System

> **Smart HR. Seamless Pay.**

Vaetan is a full-stack HR and Payroll Management System built with Python Flask and PostgreSQL. It handles everything from employee onboarding to monthly payroll calculation with real Indian statutory deductions, PDF payslip generation, and role-based access control for three user types.

---

## Screenshots

> *(Add your screenshots here)*

| Login | Dashboard | Employees |
|:---:|:---:|:---:|
| ![Login](screenshots/login.png) | ![Dashboard](screenshots/dashboard.png) | ![Employees](screenshots/employees.png) |

| Attendance | Payroll | Payslip PDF |
|:---:|:---:|:---:|
| ![Attendance](screenshots/attendance.png) | ![Payroll](screenshots/payroll.png) | ![Payslip](screenshots/payslip.png) |

---

## What It Does

Vaetan solves the real problem of managing a company's workforce end-to-end through a single unified system. It replaces spreadsheet-based HR processes with a structured, role-aware web application.

### Core Modules

**Authentication & Role-Based Access Control**
Three user roles with completely separate experiences. Admins and HR Managers see the full system. Employees log in and see only their own attendance history and payslips — nothing else. Role enforcement happens at the route level using custom Python decorators, not just UI hiding.

**Employee Management**
Add, edit, and manage employee profiles with personal details, job information, salary structure (Basic, HRA, DA, Special Allowance, Travel Allowance), bank details for payslip generation, and profile photo upload. Each employee gets an auto-generated employee code (EMP001, EMP002...) and a login account created simultaneously.

**Attendance Tracking**
Mark daily attendance for all active employees from one screen — Present, Absent, Half Day, or On Leave — with check-in and check-out times. Late arrivals are auto-flagged if check-in is after 09:30 AM. Each employee has a monthly calendar view colour-coded by attendance status, showing an attendance percentage summary for the month.

**Payroll Engine**
Run monthly payroll for all employees with one click. The calculation engine applies real Indian statutory rules:
- **PF** = 12% of Basic Salary
- **ESI** = 0.75% of Gross Salary (only if Gross ≤ ₹21,000/month)
- **TDS** = Estimated monthly using new income tax regime slabs + 4% Health & Education Cess
- **Loss of Pay** = (Gross ÷ Working Days) × Absent Days

An anomaly detector runs before approval — it flags zero attendance with non-zero pay, salary jumps over 20%, negative net pay, and duplicate bank account numbers.

**Payslip Generation**
Generate professional PDF payslips using ReportLab with company branding, employee details, itemised earnings and deductions, net pay highlighted, and an attendance summary. Download any payslip instantly or email it directly to the employee.

**Employee Self-Service Portal**
Employees log in to a simplified dashboard showing their monthly attendance percentage, recent attendance history, and latest payslip — with a direct download link. No access to other employees' data.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.11+, Flask 3.x | Web framework, routing, business logic |
| **Database** | PostgreSQL 15+ | Primary data store |
| **ORM** | SQLAlchemy + Flask-Migrate | Database models and schema migrations |
| **Auth** | Flask-Login + Flask-Bcrypt | Session management, password hashing |
| **PDF** | ReportLab | Payslip PDF generation |
| **Email** | Flask-Mail | Payslip email delivery via Gmail |
| **Frontend** | Jinja2, HTML5, CSS3, JavaScript | Server-side rendered templates |
| **Charts** | Chart.js | Dashboard KPI visualisations |
| **Config** | python-dotenv | Environment variable management |

---

## Project Structure

```
vaetan/
├── run.py                          # Entry point — starts the Flask server
├── config.py                       # Dev / production / test configurations
├── requirements.txt                # All Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore
│
└── app/
    ├── __init__.py                 # App factory — wires extensions and blueprints
    │
    ├── models/
    │   ├── __init__.py             # Imports all models for Flask-Migrate
    │   ├── user.py                 # Login accounts and roles
    │   ├── employee.py             # Employee profiles and salary structure
    │   ├── attendance.py           # Daily attendance records
    │   ├── payroll.py              # Monthly payroll with calculation engine
    │   └── payslip.py              # Generated PDF tracking
    │
    ├── routes/
    │   ├── auth.py                 # /login  /logout
    │   ├── dashboard.py            # / (branches by role)
    │   ├── employees.py            # /employees — CRUD + CSV export
    │   ├── attendance.py           # /attendance — daily view + calendar
    │   ├── payroll.py              # /payroll — run, approve, lock
    │   └── payslips.py             # /payslips — generate, download, email
    │
    ├── templates/
    │   ├── auth/login.html
    │   ├── dashboard/index.html              # HR/Admin dashboard
    │   ├── dashboard/employee_index.html     # Employee self-service
    │   ├── employees/index.html
    │   ├── employees/form.html               # Add + Edit (shared form)
    │   ├── attendance/index.html
    │   ├── attendance/calendar.html
    │   ├── payroll/index.html
    │   ├── payroll/detail.html
    │   └── payslips/index.html
    │
    ├── utils/
    │   ├── decorators.py           # @hr_required, @employee_owns_or_hr
    │   └── pdf_generator.py        # ReportLab PDF builder
    │
    └── static/
        ├── css/
        ├── js/
        ├── uploads/                # Employee profile photos
        └── payslips/               # Generated PDF files
```

---

## Database Schema

Five tables in Third Normal Form (3NF). No data is repeated across tables — everything has exactly one home.

```
users
  id, full_name, email, password_hash, role, is_active, last_login

employees
  id, user_id (FK → users), employee_code, department, designation,
  employment_type, join_date, basic_salary, hra, da, special_allowance,
  travel_allowance, bank_name, bank_account_no, ifsc_code, pan_number,
  status, risk_score, photo_path

attendance
  id, employee_id (FK → employees), date, status, check_in, check_out,
  is_late, leave_type
  UNIQUE CONSTRAINT: (employee_id, date)

payroll
  id, employee_id (FK → employees), month, year, working_days,
  days_present, days_absent, basic_salary, hra, da, gross_pay,
  pf_deduction, esi_deduction, tds_deduction, absent_deduction,
  total_deductions, net_pay, status, anomaly_flag, anomaly_reason
  UNIQUE CONSTRAINT: (employee_id, month, year)

payslips
  id, payroll_id (FK → payroll), pdf_path, generated_at,
  email_sent, emailed_at
```

---

## Installation and Setup

### Prerequisites

Make sure the following are installed:

- Python 3.11 or higher — [python.org](https://python.org)
- PostgreSQL 15 or higher — [postgresql.org](https://postgresql.org)
- Git — [git-scm.com](https://git-scm.com)

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/yourusername/vaetan.git
cd vaetan
```

---

### Step 2 — Create and activate a virtual environment

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — Mac / Linux
source venv/bin/activate
```

---

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Set up PostgreSQL

Open pgAdmin or a psql terminal and run:

```sql
CREATE DATABASE hr_payroll;
CREATE USER hr_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE hr_payroll TO hr_user;
GRANT ALL ON SCHEMA public TO hr_user;
```

---

### Step 5 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-string

DATABASE_URL=postgresql://hr_user:yourpassword@localhost/hr_payroll

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=yourteamemail@gmail.com
MAIL_PASSWORD=your-16-char-gmail-app-password
```

> **Gmail App Password:** Generate one at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Use this instead of your real Gmail password — it's required if you have 2FA enabled.

---

### Step 6 — Run database migrations

```bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

You should see 5 tables created in your PostgreSQL database:
`users`, `employees`, `attendance`, `payroll`, `payslips`

---

### Step 7 — Create the first admin account

```bash
flask shell
```

Then paste this block:

```python
from app.models.user import User
from app import db

admin = User(full_name='Admin', email='admin@vaetan.com', role='admin')
admin.set_password('admin123')
db.session.add(admin)
db.session.commit()
print("Done:", admin)
exit()
```

---

### Step 8 — Start the server

```bash
python run.py
```

Open your browser and visit:

```
http://localhost:5000
```

**Demo credentials:**
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@vaetan.com | admin123 |
| Employee | *(created via Add Employee)* | vaetan@123 |

---

## Usage Guide

### HR Manager / Admin workflow

1. **Add employees** — Employees → Add Employee → fill in personal details, job info, salary structure. A login account is created automatically.

2. **Mark attendance** — Attendance → select today's date → click Present / Absent / Half Day / Leave for each employee → Save. Click 📅 to view any employee's monthly calendar.

3. **Run payroll** — Payroll → select month → click "Run Payroll". The engine calculates salary for every active employee based on their actual attendance. Review the breakdown per employee.

4. **Approve payroll** — Click Approve on each record (or Approve All Drafts). Anomaly-flagged rows are highlighted in red — review them before approving.

5. **Generate payslips** — Payslips → click Generate next to each approved record → Download PDF or Email to employee.

### Employee workflow

1. Log in with credentials provided by HR.
2. View your attendance summary and monthly calendar on the dashboard.
3. Go to Payslips to download your salary slips.

---

## Payroll Calculation Reference

| Deduction | Rule |
|-----------|------|
| PF (Employee) | 12% of Basic Salary |
| ESI | 0.75% of Gross, only if Gross ≤ ₹21,000/month |
| TDS | Monthly estimate using new tax regime slabs + 4% cess |
| Loss of Pay | (Gross ÷ Working Days in Month) × Absent Days |
| **Net Pay** | **Gross Pay − Total Deductions** |

### New Tax Regime Slabs (FY 2024-25)

| Annual Income | Tax Rate |
|--------------|----------|
| Up to ₹3,00,000 | Nil |
| ₹3,00,001 – ₹6,00,000 | 5% |
| ₹6,00,001 – ₹9,00,000 | 10% |
| ₹9,00,001 – ₹12,00,000 | 15% |
| ₹12,00,001 – ₹15,00,000 | 20% |
| Above ₹15,00,000 | 30% |

*4% Health & Education Cess applied on total tax.*

---

## Security

- **Password hashing** — bcrypt with automatic salting. Passwords are never stored in plain text.
- **Role-based access** — Custom decorators enforce access at the route level. An employee trying to access `/employees/` or `/payroll/` is redirected, not shown a 403.
- **Data isolation** — Employees can only view their own records. Attempting to access another employee's payslip returns HTTP 403.
- **Session security** — Flask-Login manages encrypted, server-side session cookies.
- **No hardcoded secrets** — All credentials loaded from `.env`, which is excluded from version control.

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Author

**Sai Krishna**  
Computer Science Student | Full Stack Developer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/sai-krishna-61625b279/)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black)](https://github.com/saikrishna-994)
