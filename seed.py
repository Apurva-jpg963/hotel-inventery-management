from app import create_app, db
from app.models import User, Settings

def seed_database():
    app = create_app()
    with app.app_context():
        # 1. Create Default Admin User
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@saiprasad.com',
                role='Admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            print("Seeded: Default admin user (username: admin, password: admin123)")
        else:
            print("Skip: Admin user already exists")
            
        # 2. Create Default ERP Settings
        default_settings = {
            'hotel_name': 'Hotel Saiprasad',
            'hotel_address': 'Main Highway, Near City Center',
            'hotel_phone': '+91 98765 43210',
            'currency': 'INR',
            'tax_rate_percent': '18.0'
        }
        
        for key, value in default_settings.items():
            setting = Settings.query.filter_by(key=key).first()
            if not setting:
                setting = Settings(key=key, value=value)
                db.session.add(setting)
                print(f"Seeded setting: {key} = {value}")
            else:
                print(f"Skip setting: {key} already exists")
                
        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed_database()
