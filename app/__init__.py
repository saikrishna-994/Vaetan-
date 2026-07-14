"""
Vaetan — HR Payroll Management System
app/__init__.py  |  Application Factory
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail

# ── Extension instances (unbound until create_app) ───────────
db       = SQLAlchemy()
migrate  = Migrate()
login_manager = LoginManager()
bcrypt   = Bcrypt()
mail     = Mail()


def create_app(config_name: str = "default") -> Flask:
    """
    Application factory.
    Usage:
        app = create_app()          # production / default
        app = create_app("testing") # test suite
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Load config ───────────────────────────────────────────
    from config import config_map
    app.config.from_object(config_map[config_name])

    # ── Bind extensions to this app ───────────────────────────
    _init_extensions(app)

    # ── Register blueprints (one per page / feature group) ────
    _register_blueprints(app)

    # ── Shell context for `flask shell` debugging ─────────────
    _register_shell_context(app)
    _register_context_processors(app)

    return app


# ─────────────────────────────────────────────────────────────
#  Private helpers
# ─────────────────────────────────────────────────────────────

def _init_extensions(app: Flask) -> None:
    """Bind all Flask extensions to the app instance."""

    # Database + migrations
    db.init_app(app)

    # !! CRITICAL — import all models before migrate.init_app()
    # so Alembic can detect the table schema and generate migrations.
    # Without this, `flask db migrate` produces an empty migration file.
    with app.app_context():
        from app.models import User, Employee, Attendance, Payroll, Payslip  # noqa: F401

    migrate.init_app(app, db)

    # Password hashing
    bcrypt.init_app(app)

    # Email
    mail.init_app(app)

    # ── Login manager ─────────────────────────────────────────
    login_manager.init_app(app)
    login_manager.login_view       = "auth.login"          # redirect here if @login_required fails
    login_manager.login_message    = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        """Tell Flask-Login how to reload a user from the session."""
        from app.models.user import User
        return User.query.get(int(user_id))


def _register_blueprints(app: Flask) -> None:
    """Import and register every blueprint."""

    from app.routes.auth       import auth_bp
    from app.routes.dashboard  import dashboard_bp
    from app.routes.employees  import employees_bp
    from app.routes.attendance import attendance_bp
    from app.routes.payroll    import payroll_bp
    from app.routes.payslips   import payslips_bp

    app.register_blueprint(auth_bp)                           # /login  /logout
    app.register_blueprint(dashboard_bp,  url_prefix="/")    # /
    app.register_blueprint(employees_bp,  url_prefix="/employees")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")
    app.register_blueprint(payroll_bp,    url_prefix="/payroll")
    app.register_blueprint(payslips_bp,   url_prefix="/payslips")


def _register_shell_context(app: Flask) -> None:
    """Push models into `flask shell` so you can query without imports."""

    @app.shell_context_processor
    def make_shell_context():
        from app.models.user       import User
        from app.models.employee   import Employee
        from app.models.attendance import Attendance
        from app.models.payroll    import Payroll
        from app.models.payslip    import Payslip

        return {
            "db":         db,
            "User":       User,
            "Employee":   Employee,
            "Attendance": Attendance,
            "Payroll":    Payroll,
            "Payslip":    Payslip,
        }
def _register_context_processors(app: Flask) -> None:
    """Global template variables available in every Jinja template."""
    from datetime import datetime

    @app.context_processor
    def inject_globals():
        return {
            "now":      datetime.utcnow(),
            "app_name": app.config.get("APP_NAME", "Vaetan"),
        }