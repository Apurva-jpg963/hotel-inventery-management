import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import Config
from app.database import db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Import models to ensure they are registered
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Add custom template filter for currency formatting
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            val = float(value)
            return f"₹ {val:,.2f}"
        except (ValueError, TypeError):
            return "₹ 0.00"

    # Add custom template filter for short dates
    @app.template_filter('shortdate')
    def shortdate_filter(date_val):
        if not date_val:
            return ""
        if isinstance(date_val, str):
            try:
                from datetime import datetime
                clean_str = date_val.split(' ')[0].split('T')[0]
                dt = datetime.strptime(clean_str, '%Y-%m-%d')
                return dt.strftime('%d-%b-%Y')
            except Exception:
                return date_val
        if hasattr(date_val, 'strftime'):
            return date_val.strftime('%d-%b-%Y')
        return str(date_val)

    # Root redirect to dashboard
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.income import income_bp
    from app.blueprints.expense import expense_bp
    from app.blueprints.vendor import vendor_bp
    from app.blueprints.staff import staff_bp
    from app.blueprints.finance import finance_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(income_bp, url_prefix='/income')
    app.register_blueprint(expense_bp, url_prefix='/expense')
    app.register_blueprint(vendor_bp, url_prefix='/vendor')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(finance_bp, url_prefix='/finance')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Register global context processor to make notifications available everywhere
    @app.context_processor
    def inject_global_data():
        from app.models import Notification
        unread_notifications = Notification.query.filter_by(is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
        unread_count = Notification.query.filter_by(is_read=False).count()
        return dict(
            unread_notifications=unread_notifications,
            unread_count=unread_count
        )

    # Database initialization hook
    with app.app_context():
        db.create_all()
        # Alter tables for split payment method columns if they don't exist
        tables_to_migrate = [
            'income', 'expenses', 'vendor_payments', 'employee_advances',
            'payroll', 'savings', 'loans', 'loan_repayments',
            'credit_transactions', 'md_sir_account', 'cash_book'
        ]
        for tbl in tables_to_migrate:
            for col in ['cash_amount', 'online_amount']:
                try:
                    db.session.execute(db.text(f"ALTER TABLE {tbl} ADD COLUMN {col} FLOAT DEFAULT 0.0"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        # Add custom new columns for CashBook and Payroll if they don't exist
        extra_migrations = [
            ('cash_book', 'category', 'VARCHAR(100)'),
            ('cash_book', 'remarks', 'VARCHAR(255)'),
            ('cash_book', 'deposit_amount', 'FLOAT DEFAULT 0.0'),
            ('cash_book', 'withdrawal_amount', 'FLOAT DEFAULT 0.0'),
            ('payroll', 'date', 'DATE'),
            ('payroll', 'remarks', 'VARCHAR(255)')
        ]
        for tbl, col, col_type in extra_migrations:
            try:
                db.session.execute(db.text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}"))
                db.session.commit()
            except Exception:
                db.session.rollback()

    return app
