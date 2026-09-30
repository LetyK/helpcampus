from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def equipe_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.e_equipe:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.e_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper
