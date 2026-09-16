# =========================================================================
# PythonAnywhere WSGI Configuration File Template
# =========================================================================
# Copy this content into your PythonAnywhere WSGI configuration file:
# /var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py
# (Replace YOUR_USERNAME with your actual PythonAnywhere username)

import sys
import os

# 1. Path to your project directory on PythonAnywhere
path = '/home/YOUR_USERNAME/hotel_saiprasad_finance_final'
if path not in sys.path:
    sys.path.insert(0, path)

# 2. Set environment variables (Optional)
os.environ['FLASK_ENV'] = 'production'
os.environ['SECRET_KEY'] = 'saiprasad-hotel-finance-secret-key-2026'

# 3. Import and initialize the Flask application
from app import create_app

application = create_app()
