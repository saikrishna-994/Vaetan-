"""
Vaetan — app/utils/decorators.py
Role-based access control decorators.

Usage:
    @hr_required          # admin or hr_manager only
    @admin_required        # admin only
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def hr_required(view_func):
    """
    Allow access only to admin and hr_manager roles.
    Plain 'employee' role gets redirected to their own dashboard
    with a friendly message — never a raw 403 page.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_hr_manager:
            flash("That page is for HR and admin accounts only.", "warning")
            return redirect(url_for("dashboard.index"))
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    """Allow access only to the admin role (e.g. user management, settings)."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            flash("That page is for administrators only.", "warning")
            return redirect(url_for("dashboard.index"))
        return view_func(*args, **kwargs)
    return wrapped


def employee_owns_or_hr(get_employee_id):
    """
    Allow access if current_user is HR/admin, OR if the employee_id
    in the route matches the logged-in employee's own record.
    `get_employee_id` is a function that extracts emp_id from view kwargs.

    Usage:
        @employee_owns_or_hr(lambda kwargs: kwargs['emp_id'])
        def some_view(emp_id): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.is_hr_manager:
                return view_func(*args, **kwargs)
            target_emp_id = get_employee_id(kwargs)
            own_emp_id = current_user.employee.id if current_user.employee else None
            if own_emp_id != target_emp_id:
                flash("You can only view your own records.", "warning")
                return redirect(url_for("dashboard.index"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
