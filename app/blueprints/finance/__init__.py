from flask import Blueprint

finance_bp = Blueprint('finance', __name__)

from app.blueprints.finance import routes
