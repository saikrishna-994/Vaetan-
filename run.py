"""
Vaetan — HR Payroll Management System
run.py  |  Application entry point

Usage:
    python run.py                   # runs on http://localhost:5000
    flask run --debug               # same with hot reload
    flask --app run shell           # interactive shell
"""

import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "default"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config["DEBUG"],
    )
