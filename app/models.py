from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='Staff')  # Admin, Manager, Staff
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class CashBook(db.Model):
    __tablename__ = 'cash_book'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'In' (Inflow), 'Out' (Outflow)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Card, Bank, Cheque
    source = db.Column(db.String(50), nullable=False)  # 'Income', 'Expense', 'VendorPayment', 'Payroll', 'Savings', 'Loan', 'Credit', 'MDSir'
    reference_id = db.Column(db.Integer, nullable=True)  # ID of the source record
    description = db.Column(db.String(255), nullable=True)
    running_balance = db.Column(db.Float, default=0.0)
    running_cash_balance = db.Column(db.Float, default=0.0)
    running_bank_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_current_balance():
        last_entry = CashBook.query.order_by(CashBook.id.desc()).first()
        return last_entry.running_balance if last_entry else 0.0

    @staticmethod
    def get_cash_balance():
        """Balance for Cash-only transactions."""
        last_entry = CashBook.query.order_by(CashBook.id.desc()).first()
        return last_entry.running_cash_balance if last_entry else 0.0

    @staticmethod
    def get_bank_balance():
        """Balance for non-Cash transactions (UPI, Card, Bank, Cheque)."""
        last_entry = CashBook.query.order_by(CashBook.id.desc()).first()
        return last_entry.running_bank_balance if last_entry else 0.0

    @staticmethod
    def log_transaction(date, transaction_type, amount, source, reference_id, description, payment_method='Cash'):
        # Calculate new running balances
        current_cash = CashBook.get_cash_balance()
        current_bank = CashBook.get_bank_balance()
        current_total = current_cash + current_bank
        
        is_cash = (payment_method == 'Cash')
        if transaction_type == 'In':
            change = amount
        elif transaction_type == 'Out':
            change = -amount
        else:
            raise ValueError("Invalid transaction type. Must be 'In' or 'Out'")

        new_cash = current_cash + change if is_cash else current_cash
        new_bank = current_bank + change if not is_cash else current_bank
        new_total = current_total + change

        entry = CashBook(
            date=date,
            transaction_type=transaction_type,
            amount=amount,
            payment_method=payment_method,
            source=source,
            reference_id=reference_id,
            description=description,
            running_balance=new_total,
            running_cash_balance=new_cash,
            running_bank_balance=new_bank
        )
        db.session.add(entry)
        return entry

    @staticmethod
    def remove_transaction(source, reference_id):
        # Remove logs matching source and reference_id
        entries = CashBook.query.filter_by(source=source, reference_id=reference_id).all()
        for entry in entries:
            db.session.delete(entry)
        db.session.flush()
        CashBook.rebuild_balances()

    @staticmethod
    def rebuild_balances():
        # Re-evaluates running balance from the first entry to correct any drifts
        entries = CashBook.query.order_by(CashBook.id.asc()).all()
        current_cash = 0.0
        current_bank = 0.0
        for entry in entries:
            is_cash = (entry.payment_method == 'Cash')
            if entry.transaction_type == 'In':
                change = entry.amount
            elif entry.transaction_type == 'Out':
                change = -entry.amount
            else:
                change = 0.0
                
            if is_cash:
                current_cash += change
            else:
                current_bank += change
                
            entry.running_cash_balance = current_cash
            entry.running_bank_balance = current_bank
            entry.running_balance = current_cash + current_bank
        db.session.flush()


class Income(db.Model):
    __tablename__ = 'income'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    category = db.Column(db.String(50), nullable=False)  # Room, Restaurant, Banquet, Other
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Card, Bank, Split
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', backref=db.backref('incomes', lazy='dynamic'))


class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    type = db.Column(db.String(20), nullable=False)  # Hotel, Other, Development
    category = db.Column(db.String(50), nullable=False)  # Grocery, Dairy, Mandai, Gas, Wood, Custom categories
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Card, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', backref=db.backref('expenses', lazy='dynamic'))


class Vendor(db.Model):
    __tablename__ = 'vendors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    outstanding_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bills = db.relationship('VendorBill', backref='vendor', cascade='all, delete-orphan', lazy='dynamic')
    payments = db.relationship('VendorPayment', backref='vendor', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def total_billed(self):
        return sum(b.amount for b in self.bills.all())

    @property
    def total_paid(self):
        return sum(p.amount for p in self.payments.all())

    def recalculate_outstanding(self):
        # Bills increase outstanding, Payments decrease it
        total_bills = db.session.query(db.func.sum(VendorBill.amount)).filter(VendorBill.vendor_id == self.id).scalar() or 0.0
        total_payments = db.session.query(db.func.sum(VendorPayment.amount)).filter(VendorPayment.vendor_id == self.id).scalar() or 0.0
        self.outstanding_balance = total_bills - total_payments
        db.session.flush()

    def recalculate_balances(self):
        self.recalculate_outstanding()


class VendorBill(db.Model):
    __tablename__ = 'vendor_bills'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    bill_number = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VendorPayment(db.Model):
    __tablename__ = 'vendor_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Card, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    designation = db.Column(db.String(50), nullable=True)
    salary_type = db.Column(db.String(20), default='Monthly')  # Monthly, Daily
    basic_salary = db.Column(db.Float, nullable=False)
    outstanding_salary = db.Column(db.Float, default=0.0)
    advance_balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Active')  # Active, Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance = db.relationship('Attendance', backref='employee', cascade='all, delete-orphan', lazy='dynamic')
    advances = db.relationship('EmployeeAdvance', backref='employee', cascade='all, delete-orphan', lazy='dynamic')
    payrolls = db.relationship('Payroll', backref='employee', cascade='all, delete-orphan', lazy='dynamic')

    def recalculate_balances(self):
        # Recalculates total outstanding salary and advance balance
        # Advances increase advance balance, Payroll advance_adjusted decreases it
        total_advances = db.session.query(db.func.sum(EmployeeAdvance.amount)).filter(EmployeeAdvance.employee_id == self.id).scalar() or 0.0
        total_adjusted = db.session.query(db.func.sum(Payroll.advance_adjusted)).filter(Payroll.employee_id == self.id).scalar() or 0.0
        self.advance_balance = total_advances - total_adjusted

        # Outstanding payroll salary (pending_amount)
        total_pending = db.session.query(db.func.sum(Payroll.pending_amount)).filter(Payroll.employee_id == self.id).scalar() or 0.0
        self.outstanding_salary = total_pending
        db.session.flush()


class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Half Day, Leave
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmployeeAdvance(db.Model):
    __tablename__ = 'employee_advances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Bank, Cheque
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Payroll(db.Model):
    __tablename__ = 'payroll'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month = db.Column(db.String(7), nullable=False, index=True)  # Format "YYYY-MM"
    days_present = db.Column(db.Float, nullable=True, default=0.0)
    calculated_salary = db.Column(db.Float, nullable=False)
    advance_adjusted = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    net_payable = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    pending_amount = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='Pending')  # Paid, Pending, Partial
    payment_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)  # Cash, UPI, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Savings(db.Model):
    __tablename__ = 'savings'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # Deposit, Withdrawal
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Bank, Cheque
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    bank_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_balance():
        total_deposits = db.session.query(db.func.sum(Savings.amount)).filter(Savings.transaction_type == 'Deposit').scalar() or 0.0
        total_withdrawals = db.session.query(db.func.sum(Savings.amount)).filter(Savings.transaction_type == 'Withdrawal').scalar() or 0.0
        return total_deposits - total_withdrawals


class Loan(db.Model):
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    lender_name = db.Column(db.String(100), nullable=False)
    date_taken = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    principal_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Bank')  # Cash, UPI, Bank, Cheque
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    interest_rate = db.Column(db.Float, default=0.0)  # Annual percentage
    outstanding_balance = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    repayments = db.relationship('LoanRepayment', backref='loan', cascade='all, delete-orphan', lazy='dynamic')

    def recalculate_outstanding(self):
        total_repayments = db.session.query(db.func.sum(LoanRepayment.principal_paid)).filter(LoanRepayment.loan_id == self.id).scalar() or 0.0
        self.outstanding_balance = self.principal_amount - total_repayments
        db.session.flush()


class LoanRepayment(db.Model):
    __tablename__ = 'loan_repayments'
    
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loans.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    principal_paid = db.Column(db.Float, nullable=False)
    interest_paid = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CreditAccount(db.Model):
    __tablename__ = 'credit_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    party_name = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    receivable_balance = db.Column(db.Float, default=0.0)  # Money we gave (they owe us)
    payable_balance = db.Column(db.Float, default=0.0)  # Money we took (we owe them)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('CreditTransaction', backref='credit_account', cascade='all, delete-orphan', lazy='dynamic')

    def recalculate_balances(self):
        # Calculate receivables: sum of all 'Given' transactions (which can be positive or negative) 
        # and subtract historical 'Received' transactions.
        total_given = db.session.query(db.func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.credit_account_id == self.id, CreditTransaction.transaction_type == 'Given'
        ).scalar() or 0.0
        total_received = db.session.query(db.func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.credit_account_id == self.id, CreditTransaction.transaction_type == 'Received'
        ).scalar() or 0.0
        self.receivable_balance = max(0.0, total_given - total_received)

        # Calculate payables: sum of all 'Taken' transactions (which can be positive or negative)
        # and subtract historical 'Paid' transactions.
        total_taken = db.session.query(db.func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.credit_account_id == self.id, CreditTransaction.transaction_type == 'Taken'
        ).scalar() or 0.0
        total_paid = db.session.query(db.func.sum(CreditTransaction.amount)).filter(
            CreditTransaction.credit_account_id == self.id, CreditTransaction.transaction_type == 'Paid'
        ).scalar() or 0.0
        self.payable_balance = max(0.0, total_taken - total_paid)
        
        db.session.flush()


class CreditTransaction(db.Model):
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_account_id = db.Column(db.Integer, db.ForeignKey('credit_accounts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # Given, Taken, Received, Paid
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MDSirAccount(db.Model):
    __tablename__ = 'md_sir_account'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # Deposit, Withdraw
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')  # Cash, UPI, Bank
    cash_amount = db.Column(db.Float, nullable=True, default=0.0)
    online_amount = db.Column(db.Float, nullable=True, default=0.0)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_balance():
        total_deposits = db.session.query(db.func.sum(MDSirAccount.amount)).filter(MDSirAccount.transaction_type == 'Deposit').scalar() or 0.0
        total_withdrawals = db.session.query(db.func.sum(MDSirAccount.amount)).filter(MDSirAccount.transaction_type == 'Withdraw').scalar() or 0.0
        return total_deposits - total_withdrawals


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='Info')  # Info, Warning, Alert
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def add(title, message, type='Info'):
        notification = Notification(title=title, message=message, type=type)
        db.session.add(notification)
        db.session.flush()
        return notification


class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get(key, default=None):
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set(key, value):
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Settings(key=key, value=str(value))
            db.session.add(setting)
        db.session.flush()
