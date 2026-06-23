from flask import Blueprint

staff_bp = Blueprint('staff', __name__)

from app.blueprints.staff import routes
