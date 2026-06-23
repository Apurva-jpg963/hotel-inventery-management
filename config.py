import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-saiprasad-erp-key-1298371239'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(BASE_DIR, 'hotel_saiprasad.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Custom constants
    INCOME_CATEGORIES = [
        'Room Revenue',
        'Restaurant Revenue',
        'Banquet Revenue',
        'Other Revenue'
    ]
    
    EXPENSE_TYPES = {
        'Hotel': ['Grocery', 'Dairy', 'Mandai', 'Gas', 'Wood', 'Other Hotel Expense'],
        'Other': ['Electricity', 'Water', 'Internet', 'Marketing', 'Maintenance', 'Miscellaneous'],
        'Development': ['Construction', 'Renovation', 'Furniture', 'Equipment Purchase']
    }
