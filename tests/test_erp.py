import unittest
from datetime import date
from app import create_app, db
from app.models import (
    User, Income, Expense, Vendor, VendorBill, VendorPayment,
    Employee, Attendance, EmployeeAdvance, Payroll,
    Savings, Loan, LoanRepayment, CreditAccount,
    CreditTransaction, MDSirAccount, CashBook
)
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory SQLite for testing speed and isolation
    WTF_CSRF_ENABLED = False


class ERPTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation_and_password(self):
        user = User(username='testop', email='test@saiprasad.com', role='Staff')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        
        fetched = User.query.filter_by(username='testop').first()
        self.assertIsNotNone(fetched)
        self.assertTrue(fetched.check_password('pass123'))
        self.assertFalse(fetched.check_password('wrongpass'))

    def test_cashbook_inflow_outflow(self):
        # Initial balance should be 0
        self.assertEqual(CashBook.get_current_balance(), 0.0)

        # Log income inflow
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='In',
            amount=5000.0,
            source='Income',
            reference_id=1,
            description='Old Bill Received'
        )
        self.assertEqual(CashBook.get_current_balance(), 5000.0)

        # Log expense outflow
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='Out',
            amount=1500.0,
            source='Expense',
            reference_id=1,
            description='Grocery mandai purchase'
        )
        self.assertEqual(CashBook.get_current_balance(), 3500.0)

        # Rebuild balances
        CashBook.rebuild_balances()
        self.assertEqual(CashBook.get_current_balance(), 3500.0)

    def test_vendor_purchases_and_payments(self):
        # Create vendor
        vendor = Vendor(name='Girish Provisions')
        db.session.add(vendor)
        db.session.commit()

        self.assertEqual(vendor.outstanding_balance, 0.0)

        # Add credit purchase bill (INV-1)
        bill1 = VendorBill(vendor_id=vendor.id, bill_number='INV-1', amount=8000.0)
        db.session.add(bill1)
        db.session.flush()
        vendor.recalculate_outstanding()
        self.assertEqual(vendor.outstanding_balance, 8000.0)

        # Add vendor payment
        payment1 = VendorPayment(vendor_id=vendor.id, amount=3000.0, payment_method='Cash')
        db.session.add(payment1)
        db.session.flush()
        vendor.recalculate_outstanding()
        self.assertEqual(vendor.outstanding_balance, 5000.0)

    def test_employee_salary_calculations_and_advances(self):
        # Create Monthly employee
        emp = Employee(name='Rajesh Cook', designation='Chef', salary_type='Monthly', basic_salary=15000.0)
        db.session.add(emp)
        db.session.commit()

        self.assertEqual(emp.advance_balance, 0.0)
        self.assertEqual(emp.outstanding_salary, 0.0)

        # Issue Advance
        adv = EmployeeAdvance(employee_id=emp.id, amount=2000.0)
        db.session.add(adv)
        db.session.flush()
        emp.recalculate_balances()
        self.assertEqual(emp.advance_balance, 2000.0)

        # Release Payroll with adjustments
        # calculated salary is 15000. Adjust 1500 of advance. Deduct 500 other. Net payable = 13000.
        payroll = Payroll(
            employee_id=emp.id,
            month='2026-06',
            days_present=26.0,
            calculated_salary=15000.0,
            advance_adjusted=1500.0,
            deductions=500.0,
            net_payable=13000.0,
            paid_amount=10000.0,
            pending_amount=3000.0,
            payment_status='Partial'
        )
        db.session.add(payroll)
        db.session.flush()
        
        emp.recalculate_balances()
        # Advance balance should reduce to: 2000 - 1500 = 500
        self.assertEqual(emp.advance_balance, 500.0)
        # Outstanding salary should equal pending amount: 3000
        self.assertEqual(emp.outstanding_salary, 3000.0)

    def test_payroll_days_present_optional(self):
        # Create Monthly employee
        emp_m = Employee(name='Suresh Manager', designation='Manager', salary_type='Monthly', basic_salary=20000.0)
        # Create Daily employee
        emp_d = Employee(name='Naresh Waiter', designation='Waiter', salary_type='Daily', basic_salary=500.0)
        db.session.add_all([emp_m, emp_d])
        db.session.commit()

        # Payroll for Monthly employee: days_present is None/empty
        p_monthly = Payroll(
            employee_id=emp_m.id,
            month='2026-06',
            days_present=None,
            calculated_salary=20000.0,
            advance_adjusted=0.0,
            deductions=0.0,
            net_payable=20000.0,
            paid_amount=20000.0,
            pending_amount=0.0,
            payment_status='Paid'
        )
        db.session.add(p_monthly)

        # Payroll for Daily employee: days_present is 25.5
        p_daily = Payroll(
            employee_id=emp_d.id,
            month='2026-06',
            days_present=25.5,
            calculated_salary=12750.0,
            advance_adjusted=0.0,
            deductions=0.0,
            net_payable=12750.0,
            paid_amount=12750.0,
            pending_amount=0.0,
            payment_status='Paid'
        )
        db.session.add(p_daily)
        db.session.commit()

        self.assertEqual(p_monthly.days_present, 0.0)
        self.assertEqual(p_daily.days_present, 25.5)

    def test_savings_and_loans(self):
        # Bank Savings
        s1 = Savings(date=date.today(), transaction_type='Deposit', amount=4000.0, bank_name='SBI')
        s2 = Savings(date=date.today(), transaction_type='Withdrawal', amount=1500.0, bank_name='SBI')
        db.session.add_all([s1, s2])
        db.session.flush()
        self.assertEqual(Savings.get_balance(), 2500.0)

        # Bank Installments Paid (Loans Taken)
        # Initial cashbook balance
        initial_cb_balance = CashBook.get_current_balance()
        
        # Simulate route logic: find or create Loan with principal_amount = 0.0 for bank
        bank_name = 'SBI Bank'
        loan = Loan.query.filter(db.func.lower(Loan.lender_name) == bank_name.lower()).first()
        if not loan:
            loan = Loan(
                lender_name=bank_name,
                principal_amount=0.0,
                outstanding_balance=0.0,
                payment_method='Bank',
                description='Automatically created for installments tracking'
            )
            db.session.add(loan)
            db.session.flush()
            
        self.assertEqual(CashBook.get_current_balance(), initial_cb_balance)

        # Recording installment
        repay = LoanRepayment(loan_id=loan.id, principal_paid=10000.0, interest_paid=0.0)
        db.session.add(repay)
        db.session.flush()
        
        loan.recalculate_outstanding()
        self.assertEqual(loan.outstanding_balance, -10000.0)

        # Manually log transaction to match what route does (outflow)
        total_payment = repay.principal_paid
        CashBook.log_transaction(
            date=repay.date,
            transaction_type='Out',
            amount=total_payment,
            source='LoanRepayment',
            reference_id=repay.id,
            description=f"Loan Installment Paid ({loan.lender_name}): Amount ₹{repay.principal_paid} via {repay.payment_method}",
            payment_method=repay.payment_method
        )
        db.session.commit()
        
        # Verify that cashbook has the 'Out' record and balance has decreased
        cb_entry = CashBook.query.filter_by(source='LoanRepayment', reference_id=repay.id).first()
        self.assertIsNotNone(cb_entry)
        self.assertEqual(cb_entry.transaction_type, 'Out')
        self.assertEqual(cb_entry.amount, 10000.0)
        self.assertEqual(CashBook.get_current_balance(), initial_cb_balance - 10000.0)

    def test_credit_lena_dena_parties(self):
        party = CreditAccount(party_name='M/S Sai Caterers')
        db.session.add(party)
        db.session.commit()

        # We lent money (Given) -> Bill Pending increases
        tx1 = CreditTransaction(credit_account_id=party.id, transaction_type='Given', amount=12000.0)
        db.session.add(tx1)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.receivable_balance, 12000.0)

        # They repaid (Received) -> Bill Pending decreases
        tx2 = CreditTransaction(credit_account_id=party.id, transaction_type='Received', amount=8000.0)
        db.session.add(tx2)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.receivable_balance, 4000.0)

        # We borrowed (Taken) -> Bill Received increases
        tx3 = CreditTransaction(credit_account_id=party.id, transaction_type='Taken', amount=5000.0)
        db.session.add(tx3)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.payable_balance, 5000.0)

    def test_md_sir_capital_ledger(self):
        self.assertEqual(MDSirAccount.get_balance(), 0.0)

        # Deposit Capital
        md1 = MDSirAccount(transaction_type='Deposit', amount=50000.0, payment_method='Bank')
        # Drawings
        md2 = MDSirAccount(transaction_type='Withdraw', amount=12000.0, payment_method='Cash')
        db.session.add_all([md1, md2])
        db.session.commit()

        self.assertEqual(MDSirAccount.get_balance(), 38000.0)

    def test_cash_and_bank_separation(self):
        # Initial balances should be 0
        self.assertEqual(CashBook.get_cash_balance(), 0.0)
        self.assertEqual(CashBook.get_bank_balance(), 0.0)

        # 1. Log Cash Inflow
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='In',
            amount=10000.0,
            source='Income',
            reference_id=1,
            description='Cash room booking revenue',
            payment_method='Cash'
        )
        self.assertEqual(CashBook.get_cash_balance(), 10000.0)
        self.assertEqual(CashBook.get_bank_balance(), 0.0)

        # 2. Log UPI Inflow (Bank Balance)
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='In',
            amount=15000.0,
            source='Income',
            reference_id=2,
            description='UPI booking revenue',
            payment_method='UPI'
        )
        self.assertEqual(CashBook.get_cash_balance(), 10000.0)
        self.assertEqual(CashBook.get_bank_balance(), 15000.0)

        # 3. Log Cheque Outflow (Bank Balance)
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='Out',
            amount=5000.0,
            source='Expense',
            reference_id=1,
            description='Cheque paid for wood/renovation',
            payment_method='Cheque'
        )
        self.assertEqual(CashBook.get_cash_balance(), 10000.0)
        self.assertEqual(CashBook.get_bank_balance(), 10000.0)

        # 4. Log Cash Outflow
        CashBook.log_transaction(
            date=date.today(),
            transaction_type='Out',
            amount=2000.0,
            source='Expense',
            reference_id=2,
            description='Cash grocery purchase',
            payment_method='Cash'
        )
        self.assertEqual(CashBook.get_cash_balance(), 8000.0)
        self.assertEqual(CashBook.get_bank_balance(), 10000.0)
        self.assertEqual(CashBook.get_current_balance(), 18000.0)

        # 5. Rebuild balances to check correctness and drift recovery
        CashBook.rebuild_balances()
        self.assertEqual(CashBook.get_cash_balance(), 8000.0)
        self.assertEqual(CashBook.get_bank_balance(), 10000.0)
        self.assertEqual(CashBook.get_current_balance(), 18000.0)

    def test_signed_credit_transactions(self):
        party = CreditAccount(party_name='Test Party')
        db.session.add(party)
        db.session.commit()

        # 1. Add Bill Pending (Lena / Given) - Positive amount
        tx1 = CreditTransaction(credit_account_id=party.id, transaction_type='Given', amount=5000.0, date=date.today())
        db.session.add(tx1)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.receivable_balance, 5000.0)

        # 2. Settle Bill Pending (Lena / Given) - Negative amount
        tx2 = CreditTransaction(credit_account_id=party.id, transaction_type='Given', amount=-2000.0, date=date.today())
        db.session.add(tx2)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.receivable_balance, 3000.0)

        # 3. Add Bill Received (Dena / Taken) - Positive amount
        tx3 = CreditTransaction(credit_account_id=party.id, transaction_type='Taken', amount=4000.0, date=date.today())
        db.session.add(tx3)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.payable_balance, 4000.0)

        # 4. Settle Bill Received (Dena / Taken) - Negative amount
        tx4 = CreditTransaction(credit_account_id=party.id, transaction_type='Taken', amount=-1500.0, date=date.today())
        db.session.add(tx4)
        db.session.flush()
        party.recalculate_balances()
        self.assertEqual(party.payable_balance, 2500.0)

        # Verify dashboard/reports logic
        # Income from credit should include negative Given (customer payment) and bill_received outstanding
        bill_received = party.payable_balance # 2500.0
        credit_income = (
            (db.session.query(db.func.sum(CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Received').scalar() or 0.0) +
            (db.session.query(db.func.sum(-CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Given', CreditTransaction.amount < 0).scalar() or 0.0) +
            bill_received
        )
        self.assertEqual(credit_income, 4500.0)

        # Expense from credit should include negative Taken (our repayment) and bill_pending outstanding
        bill_pending = party.receivable_balance # 3000.0
        credit_expense = (
            (db.session.query(db.func.sum(CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Paid').scalar() or 0.0) +
            (db.session.query(db.func.sum(-CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Taken', CreditTransaction.amount < 0).scalar() or 0.0) +
            bill_pending
        )
        self.assertEqual(credit_expense, 4500.0)

    def test_split_payment_income(self):
        user = User(username='testop2', email='test2@saiprasad.com')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        # 1. Test Split Income Insertion
        income = Income(
            date=date.today(),
            category='Old Bill Received',
            amount=10000.0,
            payment_method='Split',
            cash_amount=4000.0,
            online_amount=6000.0,
            created_by_id=user.id
        )
        db.session.add(income)
        db.session.flush()

        # Verify CashBook split logging
        # Cash portion
        CashBook.log_transaction(
            date=income.date,
            transaction_type='In',
            amount=income.cash_amount,
            source='Income',
            reference_id=income.id,
            description=f"Income (Split-Cash): {income.category}",
            payment_method='Cash'
        )
        # Online portion
        CashBook.log_transaction(
            date=income.date,
            transaction_type='In',
            amount=income.online_amount,
            source='Income',
            reference_id=income.id,
            description=f"Income (Split-Online): {income.category}",
            payment_method='UPI'
        )
        db.session.commit()

        # Retrieve logged transactions from CashBook
        cb_entries = CashBook.query.filter_by(source='Income', reference_id=income.id).all()
        self.assertEqual(len(cb_entries), 2)
        
        cash_entries = [e for e in cb_entries if e.payment_method == 'Cash']
        upi_entries = [e for e in cb_entries if e.payment_method == 'UPI']
        
        self.assertEqual(len(cash_entries), 1)
        self.assertEqual(cash_entries[0].amount, 4000.0)
        self.assertEqual(len(upi_entries), 1)
        self.assertEqual(upi_entries[0].amount, 6000.0)

        # 2. Test deletion of split income cleans both CashBook records
        CashBook.remove_transaction(source='Income', reference_id=income.id)
        db.session.commit()
        
        remaining_cb = CashBook.query.filter_by(source='Income', reference_id=income.id).all()
        self.assertEqual(len(remaining_cb), 0)

    def test_loan_repay_view_render(self):
        # Create user
        user = User(username='testop', email='test@saiprasad.com', role='Admin')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        client = self.app.test_client()
        # Log in the user
        response = client.post('/auth/login', data={
            'username': 'testop',
            'password': 'pass123'
        }, follow_redirects=True)
        self.assertIn(b'Welcome back, testop!', response.data)

        # GET request to /finance/loan/repay
        response = client.get('/finance/loan/repay')
        self.assertEqual(response.status_code, 200)
        # Check that bank_name and amount are rendered in the HTML
        self.assertIn(b'Bank / Lender Name', response.data)
        self.assertIn(b'Installment Amount', response.data)
        # Ensure old fields are NOT rendered
        self.assertNotIn(b'loan_id', response.data)
        self.assertNotIn(b'principal_paid', response.data)

    def test_reset_month_resets_balances_and_keeps_profiles(self):
        # Create user
        user = User(username='testadmin', email='admin@saiprasad.com', role='Admin')
        user.set_password('pass123')
        db.session.add(user)
        
        # Create employee
        emp = Employee(name='Ramesh Kumar', designation='Head Chef', basic_salary=800.0, advance_balance=500.0, outstanding_salary=1000.0)
        db.session.add(emp)
        db.session.commit()

        # Add payroll & advance records
        adv = EmployeeAdvance(employee_id=emp.id, date=date.today(), amount=500.0)
        pay = Payroll(employee_id=emp.id, date=date.today(), month='2026-08', calculated_salary=800.0, net_payable=800.0, pending_amount=1000.0)
        db.session.add(adv)
        db.session.add(pay)
        db.session.commit()

        client = self.app.test_client()
        client.post('/auth/login', data={'username': 'testadmin', 'password': 'pass123'}, follow_redirects=True)

        # Execute reset_month
        resp = client.post('/staff/reset_month', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Verify employee profile remains
        emp_after = Employee.query.filter_by(name='Ramesh Kumar').first()
        self.assertIsNotNone(emp_after)
        self.assertEqual(emp_after.designation, 'Head Chef')
        self.assertEqual(emp_after.advance_balance, 0.0)
        self.assertEqual(emp_after.outstanding_salary, 0.0)

        # Verify Payroll and EmployeeAdvance records are cleared
        self.assertEqual(Payroll.query.count(), 0)
        self.assertEqual(EmployeeAdvance.query.count(), 0)


if __name__ == '__main__':
    unittest.main()

