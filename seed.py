from app import create_app, db
from app.models import User, Settings, Employee

DEFAULT_STAFF = [
    ("ADITYA J", "CASHIER", 400.00),
    ("MANIK B", "CASHIER", 400.00),
    ("AHEMAD S", "CASHIER", 500.00),
    ("MANOJ R", "CAPTAIN", 566.66),
    ("GOVID I", "CAPTAIN", 566.66),
    ("CHINTU K", "CAPTAIN", 566.66),
    ("AKASH C", "STEWARD", 466.66),
    ("TAKSHAK R", "STEWARD", 466.66),
    ("KIRAN S", "STEWARD", 466.66),
    ("VIKAS R", "STEWARD", 466.66),
    ("DEEPAK B", "STEWARD", 466.66),
    ("SANTOSH S", "CHIEF", 600.00),
    ("PIYUSH K", "CHIEF", 600.00),
    ("LIPU", "CHIEF", 600.00),
    ("BABASAHEB S", "CHIEF", 600.00),
    ("DASHRAT S", "HK", 350.00),
    ("FATIMA", "HK", 350.00),
    ("POOJA B", "HK", 350.00),
    ("SANGITA S", "HK", 350.00),
    ("DATTA A", "DRIVER", 500.00),
    ("NIVRUTI P", "E CHIEF", 700.00),
    ("MAHESH H", "RM", 800.00),
    ("UDAY C", "GM", 1000.00),
    ("ARIFA", "HK", 350.00),
    ("PRADEEP", "HELPER", 350.00)
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
        for name, desig, wage in DEFAULT_STAFF:
            emp = Employee.query.filter_by(name=name).first()
            if not emp:
                emp = Employee(
                    name=name,
                    designation=desig,
                    salary_type='Daily',
                    basic_salary=wage,
                    status='Active',
                    advance_balance=0.0,
                    outstanding_salary=0.0
                )
                db.session.add(emp)
                seeded_staff_count += 1
            else:
                # Update basic_salary if it was 0
                if emp.basic_salary == 0.0:
                    emp.basic_salary = wage
        
        print(f"Seeded {seeded_staff_count} new staff members.")
        db.session.commit()
        print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed_database()

