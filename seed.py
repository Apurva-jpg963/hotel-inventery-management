from app import create_app, db
from app.models import User, Settings, Employee

DEFAULT_STAFF = [
    ("ADITYA J", "CASHIER"),
    ("MANIK B", "CASHIER"),
    ("AHEMAD S", "CASHIER"),
    ("MANOJ R", "CAPTAIN"),
    ("GOVID I", "CAPTAIN"),
    ("CHINTU K", "CAPTAIN"),
    ("AKASH C", "STEWARD"),
    ("TAKSHAK R", "STEWARD"),
    ("KIRAN S", "STEWARD"),
    ("VIKAS R", "STEWARD"),
    ("DEEPAK B", "STEWARD"),
    ("SANTOSH S", "CHIEF"),
    ("PIYUSH K", "CHIEF"),
    ("LIPU", "CHIEF"),
    ("BABASAHEB S", "CHIEF"),
    ("DASHRAT S", "HK"),
    ("FATIMA", "HK"),
    ("POOJA B", "HK"),
    ("SANGITA S", "HK"),
    ("DATTA A", "DRIVER"),
    ("NIVRUTI P", "E CHIEF"),
    ("MAHESH H", "RM"),
    ("UDAY C", "GM"),
    ("ARIFA", "HK"),
    ("PRADEEP", "HELPER")
]

def seed_database():
    app = create_app()
    with app.app_context():
        # 1. Create Default Admin User
        admin_user = User.query.filter((User.username == 'admin') | (User.email == 'admin@saiprasad.com')).first()
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

        # 3. Seed Default Staff Members
        seeded_staff_count = 0
        for name, desig in DEFAULT_STAFF:
            emp = Employee.query.filter_by(name=name).first()
            if not emp:
                emp = Employee(
                    name=name,
                    designation=desig,
                    salary_type='Daily',
                    basic_salary=0.0,
                    status='Active',
                    advance_balance=0.0,
                    outstanding_salary=0.0
                )
                db.session.add(emp)
                seeded_staff_count += 1
        
        print(f"Seeded {seeded_staff_count} staff members.")
        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed_database()

