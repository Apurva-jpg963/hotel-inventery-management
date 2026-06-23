from flask import Blueprint

expense_bp = Blueprint('expense', __name__)

from app.blueprints.expense import routes
