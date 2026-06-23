from flask import Blueprint

vendor_bp = Blueprint('vendor', __name__)

from app.blueprints.vendor import routes
