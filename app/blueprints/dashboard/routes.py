from datetime import datetime, timedelta
from flask import render_template
from flask_login import login_required
from app.database import db
from app.blueprints.dashboard import dashboard_bp
from app.models import (
    Income, Expense, Vendor, Employee, Loan, CreditAccount,
    Savings, MDSirAccount, CashBook, Attendance, Payroll,
    VendorPayment, EmployeeAdvance, LoanRepayment, CreditTransaction, VendorBill
)

@dashboard_bp.route('/')
@login_required
def index():
    # 1. Fetch KPI Metrics
    bill_pending = db.session.query(db.func.sum(CreditAccount.receivable_balance)).scalar() or 0.0
    bill_received = db.session.query(db.func.sum(CreditAccount.payable_balance)).scalar() or 0.0

    total_income = (
        (db.session.query(db.func.sum(Income.amount)).scalar() or 0.0) +
        (db.session.query(db.func.sum(MDSirAccount.amount)).filter(MDSirAccount.transaction_type == 'Deposit').scalar() or 0.0) +
        (db.session.query(db.func.sum(Savings.amount)).filter(Savings.transaction_type == 'Withdrawal').scalar() or 0.0) +
        (db.session.query(db.func.sum(CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Received').scalar() or 0.0) +
        (db.session.query(db.func.sum(-CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Given', CreditTransaction.amount < 0).scalar() or 0.0) +
        bill_received
    )
    total_expenses = (
        (db.session.query(db.func.sum(Expense.amount)).scalar() or 0.0) +
        (db.session.query(db.func.sum(VendorPayment.amount)).scalar() or 0.0) +
        (db.session.query(db.func.sum(Payroll.paid_amount)).scalar() or 0.0) +
        (db.session.query(db.func.sum(EmployeeAdvance.amount)).scalar() or 0.0) +
        (db.session.query(db.func.sum(Savings.amount)).filter(Savings.transaction_type == 'Deposit').scalar() or 0.0) +
        (db.session.query(db.func.sum(CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Paid').scalar() or 0.0) +
        (db.session.query(db.func.sum(-CreditTransaction.amount)).filter(CreditTransaction.transaction_type == 'Taken', CreditTransaction.amount < 0).scalar() or 0.0) +
        (db.session.query(db.func.sum(MDSirAccount.amount)).filter(MDSirAccount.transaction_type == 'Withdraw').scalar() or 0.0) +
        (db.session.query(db.func.sum(LoanRepayment.principal_paid + LoanRepayment.interest_paid)).scalar() or 0.0) +
        bill_pending
    )
    net_profit = total_income - total_expenses
    
    cash_balance = CashBook.get_cash_balance()
    bank_balance = CashBook.get_bank_balance()
    overall_balance = cash_balance + bank_balance
    savings_balance = Savings.get_balance()
    vendor_outstanding = db.session.query(db.func.sum(Vendor.outstanding_balance)).scalar() or 0.0
    salary_outstanding = db.session.query(db.func.sum(Employee.outstanding_salary)).scalar() or 0.0
    total_bank_installments = db.session.query(db.func.sum(LoanRepayment.principal_paid + LoanRepayment.interest_paid)).scalar() or 0.0
    md_sir_balance = MDSirAccount.get_balance()

    # 2. Charts Data Generation (Last 6 Months Trend)
    # Generate labels for last 6 months
    today = datetime.today()
    months_labels = []
    months_keys = []  # "YYYY-MM"
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        months_labels.append(d.strftime('%b %Y'))
        months_keys.append(d.strftime('%Y-%m'))

    # Initialize monthly datasets
    income_trend = {k: 0.0 for k in months_keys}
    expense_trend = {k: 0.0 for k in months_keys}
    profit_trend = {k: 0.0 for k in months_keys}

    # Query Incomes and other inflows from last 6 months
    six_months_ago = today - timedelta(days=180)
    incomes = Income.query.filter(Income.date >= six_months_ago.date()).all()
    for inc in incomes:
        m_key = inc.date.strftime('%Y-%m')
        if m_key in income_trend:
            income_trend[m_key] += inc.amount

    md_deposits = MDSirAccount.query.filter(MDSirAccount.date >= six_months_ago.date(), MDSirAccount.transaction_type == 'Deposit').all()
    for md in md_deposits:
        m_key = md.date.strftime('%Y-%m')
        if m_key in income_trend:
            income_trend[m_key] += md.amount

    savings_withdrawals = Savings.query.filter(Savings.date >= six_months_ago.date(), Savings.transaction_type == 'Withdrawal').all()
    for s in savings_withdrawals:
        m_key = s.date.strftime('%Y-%m')
        if m_key in income_trend:
            income_trend[m_key] += s.amount



    credit_inflows = CreditTransaction.query.filter(
        CreditTransaction.date >= six_months_ago.date(),
        CreditTransaction.transaction_type.in_(['Received', 'Given', 'Taken'])
    ).all()
    for c in credit_inflows:
        m_key = c.date.strftime('%Y-%m')
        if m_key in income_trend:
            if c.transaction_type == 'Received':
                income_trend[m_key] += c.amount
            elif c.transaction_type == 'Taken' and c.amount > 0:
                income_trend[m_key] += c.amount
            elif c.transaction_type == 'Given' and c.amount < 0:
                income_trend[m_key] += -c.amount



    # Query Expenses and other outflows from last 6 months
    expenses = Expense.query.filter(Expense.date >= six_months_ago.date()).all()
    for exp in expenses:
        m_key = exp.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += exp.amount

    vendor_pays = VendorPayment.query.filter(VendorPayment.date >= six_months_ago.date()).all()
    for vp in vendor_pays:
        m_key = vp.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += vp.amount

    payrolls = Payroll.query.filter(Payroll.payment_date >= six_months_ago.date()).all()
    for p in payrolls:
        m_key = p.payment_date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += p.paid_amount

    advances = EmployeeAdvance.query.filter(EmployeeAdvance.date >= six_months_ago.date()).all()
    for adv in advances:
        m_key = adv.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += adv.amount

    savings = Savings.query.filter(Savings.date >= six_months_ago.date(), Savings.transaction_type == 'Deposit').all()
    for s in savings:
        m_key = s.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += s.amount

    loan_repays = LoanRepayment.query.filter(LoanRepayment.date >= six_months_ago.date()).all()
    for lr in loan_repays:
        m_key = lr.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += (lr.principal_paid + lr.interest_paid)

    credit_outflows = CreditTransaction.query.filter(
        CreditTransaction.date >= six_months_ago.date(),
        CreditTransaction.transaction_type.in_(['Paid', 'Taken', 'Given'])
    ).all()
    for c in credit_outflows:
        m_key = c.date.strftime('%Y-%m')
        if m_key in expense_trend:
            if c.transaction_type == 'Paid':
                expense_trend[m_key] += c.amount
            elif c.transaction_type == 'Given' and c.amount > 0:
                expense_trend[m_key] += c.amount
            elif c.transaction_type == 'Taken' and c.amount < 0:
                expense_trend[m_key] += -c.amount

    md_txs = MDSirAccount.query.filter(MDSirAccount.date >= six_months_ago.date(), MDSirAccount.transaction_type == 'Withdraw').all()
    for m in md_txs:
        m_key = m.date.strftime('%Y-%m')
        if m_key in expense_trend:
            expense_trend[m_key] += m.amount



    # Compute profits
    for key in months_keys:
        profit_trend[key] = income_trend[key] - expense_trend[key]

    # Convert to lists for Chart.js
    income_dataset = [income_trend[k] for k in months_keys]
    expense_dataset = [expense_trend[k] for k in months_keys]
    profit_dataset = [profit_trend[k] for k in months_keys]

    # 3. Salary Analysis: Breakdown of Basic Salary by Designation
    employees = Employee.query.filter_by(status='Active').all()
    salary_by_desig = {}
    for emp in employees:
        desig = emp.designation or 'Other Staff'
        salary_by_desig[desig] = salary_by_desig.get(desig, 0.0) + emp.basic_salary
    
    salary_labels = list(salary_by_desig.keys())
    salary_dataset = list(salary_by_desig.values())

    # 4. Vendor Outstanding (Top 5 Vendors)
    top_vendors = Vendor.query.filter(Vendor.outstanding_balance > 0).order_by(Vendor.outstanding_balance.desc()).limit(5).all()
    vendor_labels = [v.name for v in top_vendors]
    vendor_dataset = [v.outstanding_balance for v in top_vendors]

    # 5. Savings Growth (Cumulative balance for last 6 months)
    savings_log = Savings.query.filter(Savings.date >= six_months_ago.date()).order_by(Savings.date.asc()).all()
    savings_growth = []
    # Fetch starting balance prior to 6 months ago
    starting_savings = db.session.query(db.func.sum(Savings.amount)).filter(
        Savings.date < six_months_ago.date(), Savings.transaction_type == 'Deposit'
    ).scalar() or 0.0
    starting_withdrawals = db.session.query(db.func.sum(Savings.amount)).filter(
        Savings.date < six_months_ago.date(), Savings.transaction_type == 'Withdrawal'
    ).scalar() or 0.0
    running_savings = starting_savings - starting_withdrawals

    savings_monthly = {k: 0.0 for k in months_keys}
    for item in savings_log:
        m_key = item.date.strftime('%Y-%m')
        if m_key in savings_monthly:
            if item.transaction_type == 'Deposit':
                savings_monthly[m_key] += item.amount
            else:
                savings_monthly[m_key] -= item.amount

    savings_growth_dataset = []
    for k in months_keys:
        running_savings += savings_monthly[k]
        savings_growth_dataset.append(running_savings)

    # 6. Cash Flow Analysis: Inflows vs Outflows (Last 4 Weeks)
    four_weeks_ago = today - timedelta(weeks=4)
    cash_logs = CashBook.query.filter(CashBook.date >= four_weeks_ago.date()).all()
    
    # Generate weekly buckets
    week_labels = ['Week 4 Ago', 'Week 3 Ago', 'Week 2 Ago', 'Last Week']
    inflows_weekly = [0.0, 0.0, 0.0, 0.0]
    outflows_weekly = [0.0, 0.0, 0.0, 0.0]

    for entry in cash_logs:
        days_diff = (today.date() - entry.date).days
        week_idx = 3 - (days_diff // 7)
        if 0 <= week_idx <= 3:
            if entry.transaction_type == 'In':
                inflows_weekly[week_idx] += entry.amount
            elif entry.transaction_type == 'Out':
                outflows_weekly[week_idx] += entry.amount

    return render_template(
        'dashboard/index.html',
        # KPI balances
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        cash_balance=cash_balance,
        bank_balance=bank_balance,
        overall_balance=overall_balance,
        savings_balance=savings_balance,
        vendor_outstanding=vendor_outstanding,
        salary_outstanding=salary_outstanding,
        total_bank_installments=total_bank_installments,
        bill_pending=bill_pending,
        bill_received=bill_received,
        md_sir_balance=md_sir_balance,
        # Chart 1: Income vs Expense Trend
        months_labels=months_labels,
        income_dataset=income_dataset,
        expense_dataset=expense_dataset,
        # Chart 2: Profit Trend
        profit_dataset=profit_dataset,
        # Chart 3: Salary Analysis by Designation
        salary_labels=salary_labels,
        salary_dataset=salary_dataset,
        # Chart 4: Vendor Outstanding
        vendor_labels=vendor_labels,
        vendor_dataset=vendor_dataset,
        # Chart 5: Savings Growth
        savings_growth_dataset=savings_growth_dataset,
        # Chart 6: Cash Flow
        week_labels=week_labels,
        inflows_weekly=inflows_weekly,
        outflows_weekly=outflows_weekly
    )
