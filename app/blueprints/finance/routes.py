from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.blueprints.finance import finance_bp
from app.blueprints.finance.forms import (
    SavingsTransactionForm, LoanRepaymentForm,
    CreditAccountForm, CreditTransactionForm, MDSirTransactionForm
)
from app.models import (
    Savings, Loan, LoanRepayment, CreditAccount,
    CreditTransaction, MDSirAccount, CashBook
)
from datetime import datetime

@finance_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'savings')
    if tab not in ['savings', 'loans', 'credit', 'md']:
        tab = 'savings'

    if tab == 'savings':
        transactions = Savings.query.order_by(Savings.date.desc(), Savings.id.desc()).all()
        balance = Savings.get_balance()
        return render_template('finance/savings.html', tab=tab, transactions=transactions, balance=balance)

    elif tab == 'loans':
        repayments = LoanRepayment.query.order_by(LoanRepayment.date.desc(), LoanRepayment.id.desc()).all()
        total_installments_paid = sum(r.principal_paid + r.interest_paid for r in repayments)
        return render_template('finance/loans.html', tab=tab, repayments=repayments, total_installments_paid=total_installments_paid)

    elif tab == 'credit':
        # Select Credit accounts
        accounts = CreditAccount.query.order_by(CreditAccount.party_name.asc()).all()
        total_bill_pending = db.session.query(db.func.sum(CreditAccount.receivable_balance)).scalar() or 0.0
        total_bill_received = db.session.query(db.func.sum(CreditAccount.payable_balance)).scalar() or 0.0
        
        # Check if detailed ledger for a specific party is selected
        party_id = request.args.get('party_id', type=int)
        selected_party = None
        ledger_entries = []
        if party_id:
            selected_party = CreditAccount.query.get_or_404(party_id)
            txs = CreditTransaction.query.filter_by(credit_account_id=party_id).order_by(CreditTransaction.date.asc(), CreditTransaction.id.asc()).all()
            
            running_bill_pending = 0.0
            running_bill_received = 0.0
            for tx in txs:
                if tx.transaction_type == 'Given':
                    running_bill_pending += tx.amount
                    display_type = 'Bill Pending' if tx.amount >= 0 else 'Pending Settled'
                elif tx.transaction_type == 'Received':
                    running_bill_pending -= tx.amount
                    display_type = 'Pending Settled'
                elif tx.transaction_type == 'Taken':
                    running_bill_received += tx.amount
                    display_type = 'Bill Received' if tx.amount >= 0 else 'Received Settled'
                elif tx.transaction_type == 'Paid':
                    running_bill_received -= tx.amount
                    display_type = 'Received Settled'
                
                ledger_entries.append({
                    'id': tx.id,
                    'date': tx.date,
                    'type': display_type,
                    'payment_method': tx.payment_method,
                    'description': tx.description or 'Credit transaction',
                    'amount': abs(tx.amount),
                    'running_bill_pending': max(0.0, running_bill_pending),
                    'running_bill_received': max(0.0, running_bill_received)
                })

            return render_template(
                'finance/credit_ledger.html',
                tab=tab,
                selected_party=selected_party,
                ledger_entries=ledger_entries,
                datetime_now=datetime.now()
            )

        return render_template('finance/credit.html', tab=tab, accounts=accounts, total_bill_pending=total_bill_pending, total_bill_received=total_bill_received)

    elif tab == 'md':
        transactions = MDSirAccount.query.order_by(MDSirAccount.date.asc(), MDSirAccount.id.asc()).all()
        cash_balance = CashBook.get_current_balance()

        # Separate running balances for Cash vs Online
        running_cash = 0.0
        running_online = 0.0
        running_total = 0.0
        md_ledger = []
        for tx in transactions:
            sign = 1 if tx.transaction_type == 'Deposit' else -1
            is_cash = tx.payment_method == 'Cash'
            if is_cash:
                running_cash += sign * tx.amount
            else:
                running_online += sign * tx.amount
            running_total += sign * tx.amount
            md_ledger.append({
                'tx': tx,
                'running_cash': running_cash,
                'running_online': running_online,
                'running_total': running_total
            })
        md_ledger.reverse()

        return render_template('finance/md_account.html', tab=tab, md_ledger=md_ledger,
            balance_cash=running_cash, balance_online=running_online,
            balance_total=running_total, cash_balance=cash_balance)

    return redirect(url_for('finance.index'))


# =========================================================================
# SAVINGS MANAGEMENT
# =========================================================================
@finance_bp.route('/savings/add', methods=['GET', 'POST'])
@login_required
def savings_add():
    form = SavingsTransactionForm()
    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('vendor/form.html', form=form, title="Record Bank Savings Entry")

        savings = Savings(
            date=form.date.data,
            transaction_type=form.transaction_type.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            bank_name=form.bank_name.data,
            description=form.description.data
        )
        db.session.add(savings)
        db.session.flush()

        # Automation Rules: 
        # Savings deposit decreases liquid cash (CashBook Out)
        # Savings withdrawal increases liquid cash (CashBook In)
        cb_type = 'Out' if savings.transaction_type == 'Deposit' else 'In'
        
        if savings.payment_method == 'Split':
            if savings.cash_amount > 0:
                CashBook.log_transaction(
                    date=savings.date,
                    transaction_type=cb_type,
                    amount=savings.cash_amount,
                    source='Savings',
                    reference_id=savings.id,
                    description=f"Savings {savings.transaction_type} (Split-Cash) to/from {savings.bank_name} - {savings.description or ''}",
                    payment_method='Cash'
                )
            if savings.online_amount > 0:
                CashBook.log_transaction(
                    date=savings.date,
                    transaction_type=cb_type,
                    amount=savings.online_amount,
                    source='Savings',
                    reference_id=savings.id,
                    description=f"Savings {savings.transaction_type} (Split-Online) to/from {savings.bank_name} - {savings.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=savings.date,
                transaction_type=cb_type,
                amount=savings.amount,
                source='Savings',
                reference_id=savings.id,
                description=f"Savings {savings.transaction_type} to {savings.bank_name} - {savings.description or ''}",
                payment_method=savings.payment_method
            )

        db.session.commit()
        flash(f'Savings transaction of {savings.amount} recorded.', 'success')
        return redirect(url_for('finance.index', tab='savings'))
        
    return render_template('vendor/form.html', form=form, title="Record Bank Savings Entry")


@finance_bp.route('/savings/delete/<int:savings_id>', methods=['POST'])
@login_required
def savings_delete(savings_id):
    savings = Savings.query.get_or_404(savings_id)
    CashBook.remove_transaction(source='Savings', reference_id=savings.id)
    db.session.delete(savings)
    db.session.commit()
    flash('Savings transaction deleted successfully.', 'success')
    return redirect(url_for('finance.index', tab='savings'))


# =========================================================================
# LOAN LIABILITIES
# =========================================================================
@finance_bp.route('/loan/repay', methods=['GET', 'POST'])
@login_required
def loan_repay():
    form = LoanRepaymentForm()
    
    # Prefill bank name if passed as argument
    bank_name = request.args.get('bank_name')
    if bank_name and request.method == 'GET':
        form.bank_name.data = bank_name

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('vendor/form.html', form=form, title="Record Bank Installment Paid")

        bank = form.bank_name.data.strip()
        # Find or create a hidden loan for this bank
        loan = Loan.query.filter(db.func.lower(Loan.lender_name) == bank.lower()).first()
        if not loan:
            loan = Loan(
                lender_name=bank,
                principal_amount=0.0,
                outstanding_balance=0.0,
                payment_method='Cash',
                description='Automatically created for installments tracking'
            )
            db.session.add(loan)
            db.session.flush()
        
        repayment = LoanRepayment(
            loan_id=loan.id,
            date=form.date.data,
            principal_paid=form.amount.data,
            interest_paid=0.0,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data
        )
        db.session.add(repayment)
        db.session.flush()

        # Recalculate Loan outstanding
        loan.recalculate_outstanding()

        # Automation Rule: Loan Installment Paid decreases central cash (CashBook Out)
        total_payment = repayment.principal_paid
        if repayment.payment_method == 'Split':
            if repayment.cash_amount > 0:
                CashBook.log_transaction(
                    date=repayment.date,
                    transaction_type='Out',
                    amount=repayment.cash_amount,
                    source='LoanRepayment',
                    reference_id=repayment.id,
                    description=f"Loan Installment Paid (Split-Cash) ({loan.lender_name}) - {repayment.description or ''}",
                    payment_method='Cash'
                )
            if repayment.online_amount > 0:
                CashBook.log_transaction(
                    date=repayment.date,
                    transaction_type='Out',
                    amount=repayment.online_amount,
                    source='LoanRepayment',
                    reference_id=repayment.id,
                    description=f"Loan Installment Paid (Split-Online) ({loan.lender_name}) - {repayment.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=repayment.date,
                transaction_type='Out',
                amount=total_payment,
                source='LoanRepayment',
                reference_id=repayment.id,
                description=f"Loan Installment Paid ({loan.lender_name}): Amount ₹{repayment.principal_paid} via {repayment.payment_method}",
                payment_method=repayment.payment_method
            )

        db.session.commit()
        flash(f'Installment of {total_payment} paid to {loan.lender_name}.', 'success')
        return redirect(url_for('finance.index', tab='loans'))

    return render_template('vendor/form.html', form=form, title="Record Bank Installment Paid")


@finance_bp.route('/loan/repay/delete/<int:repayment_id>', methods=['POST'])
@login_required
def loan_repay_delete(repayment_id):
    repayment = LoanRepayment.query.get_or_404(repayment_id)
    loan_id = repayment.loan_id
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='LoanRepayment', reference_id=repayment.id)
    db.session.delete(repayment)
    db.session.flush()
    
    # Recalculate outstanding
    loan = Loan.query.get(loan_id)
    loan.recalculate_outstanding()
    
    db.session.commit()
    flash('Repayment record deleted.', 'success')
    return redirect(url_for('finance.index', tab='loans'))


# =========================================================================
# CREDIT ACCOUNTS (LENA-DENA)
# =========================================================================
@finance_bp.route('/credit/party/add', methods=['GET', 'POST'])
@login_required
def credit_party_add():
    form = CreditAccountForm()
    if form.validate_on_submit():
        party = CreditAccount(
            party_name=form.party_name.data,
            phone=form.phone.data,
            address=form.address.data
        )
        db.session.add(party)
        db.session.commit()
        flash(f'Credit party "{party.party_name}" registered successfully!', 'success')
        return redirect(url_for('finance.index', tab='credit'))
    return render_template('vendor/form.html', form=form, title="Add Credit Party (Lena-Dena)")


@finance_bp.route('/credit/party/delete/<int:party_id>', methods=['POST'])
@login_required
def credit_party_delete(party_id):
    party = CreditAccount.query.get_or_404(party_id)
    name = party.party_name
    
    # Clean CashBook for transactions
    txs = CreditTransaction.query.filter_by(credit_account_id=party_id).all()
    for tx in txs:
        CashBook.remove_transaction(source='CreditTransaction', reference_id=tx.id)
        
    db.session.delete(party)
    db.session.commit()
    flash(f'Credit account "{name}" and all transaction ledgers deleted.', 'success')
    return redirect(url_for('finance.index', tab='credit'))


@finance_bp.route('/credit/transaction/add', methods=['GET', 'POST'])
@login_required
def credit_transaction_add():
    form = CreditTransactionForm()
    form.credit_account_id.choices = [(p.id, p.party_name) for p in CreditAccount.query.order_by(CreditAccount.party_name.asc()).all()]
    
    party_id = request.args.get('party_id', type=int)
    if party_id and request.method == 'GET':
        form.credit_account_id.data = party_id

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - abs(form.amount.data)) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the absolute total Amount.", "danger")
                return render_template('vendor/form.html', form=form, title="Record Credit Transaction")

        tx = CreditTransaction(
            credit_account_id=form.credit_account_id.data,
            date=form.date.data,
            transaction_type=form.transaction_type.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data
        )
        db.session.add(tx)
        db.session.flush()

        # Recalculate Credit balances
        party = CreditAccount.query.get(tx.credit_account_id)
        party.recalculate_balances()

        # Automation Rules:
        # Bill Pending (Given):
        #   - Positive (We Lent): Cash Outflow (CashBook Out)
        #   - Negative (They Repaid): Cash Inflow (CashBook In)
        # Bill Received (Taken):
        #   - Positive (We Borrowed): Cash Inflow (CashBook In)
        #   - Negative (We Repaid): Cash Outflow (CashBook Out)
        is_bill_pending = (tx.transaction_type == 'Given')
        amount_val = tx.amount
        
        if is_bill_pending:
            if amount_val >= 0:
                cb_type = 'Out'
                cb_amount = amount_val
            else:
                cb_type = 'In'
                cb_amount = -amount_val
        else: # Taken
            if amount_val >= 0:
                cb_type = 'In'
                cb_amount = amount_val
            else:
                cb_type = 'Out'
                cb_amount = -amount_val

        if cb_amount > 0:
            if tx.payment_method == 'Split':
                # split of cb_amount based on cash_amount and online_amount ratios or absolute values
                # Since cash_amount + online_amount == cb_amount (abs(amount)), we can use them directly!
                if tx.cash_amount > 0:
                    CashBook.log_transaction(
                        date=tx.date,
                        transaction_type=cb_type,
                        amount=tx.cash_amount,
                        source='CreditTransaction',
                        reference_id=tx.id,
                        description=f"Credit ({'Bill Pending' if is_bill_pending else 'Bill Received'}) [{party.party_name}] (Split-Cash) - {tx.description or ''}",
                        payment_method='Cash'
                    )
                if tx.online_amount > 0:
                    CashBook.log_transaction(
                        date=tx.date,
                        transaction_type=cb_type,
                        amount=tx.online_amount,
                        source='CreditTransaction',
                        reference_id=tx.id,
                        description=f"Credit ({'Bill Pending' if is_bill_pending else 'Bill Received'}) [{party.party_name}] (Split-Online) - {tx.description or ''}",
                        payment_method='UPI'
                    )
            else:
                CashBook.log_transaction(
                    date=tx.date,
                    transaction_type=cb_type,
                    amount=cb_amount,
                    source='CreditTransaction',
                    reference_id=tx.id,
                    description=f"Credit ({'Bill Pending' if is_bill_pending else 'Bill Received'}) [{party.party_name}] via {tx.payment_method} - {tx.description or ''}",
                    payment_method=tx.payment_method
                )

        db.session.commit()
        flash(f"Credit transaction of {abs(tx.amount)} recorded for {party.party_name}.", 'success')
        return redirect(url_for('finance.index', tab='credit', party_id=party.id))

    return render_template('vendor/form.html', form=form, title="Record Credit Transaction")


@finance_bp.route('/credit/transaction/delete/<int:tx_id>', methods=['POST'])
@login_required
def credit_transaction_delete(tx_id):
    tx = CreditTransaction.query.get_or_404(tx_id)
    party_id = tx.credit_account_id
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='CreditTransaction', reference_id=tx.id)
    db.session.delete(tx)
    db.session.flush()
    
    # Recalculate party balance
    party = CreditAccount.query.get(party_id)
    party.recalculate_balances()
    
    db.session.commit()
    flash('Credit transaction deleted successfully.', 'success')
    return redirect(url_for('finance.index', tab='credit', party_id=party_id))


# =========================================================================
# MD SIR ACCOUNT
# =========================================================================
@finance_bp.route('/md/add', methods=['GET', 'POST'])
@login_required
def md_add():
    form = MDSirTransactionForm()
    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('finance/md_form.html', form=form, title="Record MD Sir Account Entry")

        md_tx = MDSirAccount(
            date=form.date.data,
            transaction_type=form.transaction_type.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data
        )
        db.session.add(md_tx)
        db.session.flush()

        # Automation Rules:
        # Deposit: increases central cash balance (CashBook In)
        # Withdraw: decreases central cash balance (CashBook Out)
        cb_type = 'In' if md_tx.transaction_type == 'Deposit' else 'Out'
        
        if md_tx.payment_method == 'Split':
            if md_tx.cash_amount > 0:
                CashBook.log_transaction(
                    date=md_tx.date,
                    transaction_type=cb_type,
                    amount=md_tx.cash_amount,
                    source='MDSir',
                    reference_id=md_tx.id,
                    description=f"MD Sir: {md_tx.transaction_type} (Split-Cash) - {md_tx.description or ''}",
                    payment_method='Cash'
                )
            if md_tx.online_amount > 0:
                CashBook.log_transaction(
                    date=md_tx.date,
                    transaction_type=cb_type,
                    amount=md_tx.online_amount,
                    source='MDSir',
                    reference_id=md_tx.id,
                    description=f"MD Sir: {md_tx.transaction_type} (Split-Online) - {md_tx.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=md_tx.date,
                transaction_type=cb_type,
                amount=md_tx.amount,
                source='MDSir',
                reference_id=md_tx.id,
                description=f"MD Sir: {md_tx.transaction_type} ({md_tx.payment_method}) - {md_tx.description or ''}",
                payment_method=md_tx.payment_method
            )

        db.session.commit()
        flash(f'MD Account entry of {md_tx.amount} ({md_tx.transaction_type}) logged.', 'success')
        return redirect(url_for('finance.index', tab='md'))

    return render_template('finance/md_form.html', form=form, title="Record MD Sir Account Entry")


@finance_bp.route('/md/delete/<int:md_id>', methods=['POST'])
@login_required
def md_delete(md_id):
    md_tx = MDSirAccount.query.get_or_404(md_id)
    CashBook.remove_transaction(source='MDSir', reference_id=md_tx.id)
    db.session.delete(md_tx)
    db.session.commit()
    flash('MD Account entry deleted successfully.', 'success')
    return redirect(url_for('finance.index', tab='md'))
