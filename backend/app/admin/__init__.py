from flask import Blueprint

admin_ui_bp = Blueprint('admin_ui', __name__, template_folder='../../templates/admin')

from . import routes
