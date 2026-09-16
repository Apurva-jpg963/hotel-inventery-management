from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.blueprints.finance import finance_bp
from app.blueprints.finance.forms import (
    SavingsTransactionForm, LoanRepaymentForm,
    CreditAccountForm, CreditTransactionForm, MDSirTransactionForm,
    FinanceLedgerForm
)
from app.models import (
    Savings, Loan, LoanRepayment, CreditAccount,
    CreditTransaction, MDSirAccount, CashBook
)
from datetime import datetime, date

@finance_bp.route('/')
@login_required
def index():
    tab = request.args.get('tab', 'ledger')
    if tab not in ['ledger', 'savings', 'loans', 'credit', 'md']:
        tab = 'ledger'

    if tab == 'ledger':
        entries_query = CashBook.query.order_by(CashBook.date.asc(), CashBook.id.asc()).all()
        
        running_bal = 0.0
        total_deposits = 0.0
        total_withdrawals = 0.0
        ledger_entries = []
        
        for entry in entries_query:
            is_deposit = entry.transaction_type in ['In', 'Deposit']
            deposit_val = entry.deposit_amount if entry.deposit_amount > 0 else (entry.amount if is_deposit else 0.0)
            withdrawal_val = entry.withdrawal_amount if entry.withdrawal_amount > 0 else (entry.amount if not is_deposit else 0.0)
            
            running_bal += (deposit_val - withdrawal_val)
            total_deposits += deposit_val
            total_withdrawals += withdrawal_val

            # Standardize category name fallback
            cat = entry.category
            if not cat:
                if entry.source == 'Income':
                    cat = 'Cash Collection'
                elif entry.source == 'Expense':
                    cat = 'Miscellaneous'
                elif entry.source == 'Payroll':
                    cat = 'Staff Salary'
                elif entry.source == 'VendorPayment':
                    cat = 'Vendor Payment'
                elif is_deposit:
                    cat = 'Other Income'
                else:
                    cat = 'Miscellaneous'

            ledger_entries.append({
                'id': entry.id,
                'date': entry.date,
                'description': entry.description or f"{entry.source} entry",
                'category': cat,
                'payment_method': entry.payment_method or 'Cash',
                'deposit': deposit_val,
                'withdrawal': withdrawal_val,
                'running_balance': running_bal,
                'remarks': entry.remarks or '',
                'source': entry.source,
                'reference_id': entry.reference_id
            })

        net_change = total_deposits - total_withdrawals
        closing_balance = running_bal
        
        # Display latest transactions on top in UI
        display_entries = list(reversed(ledger_entries))

        return render_template(
            'finance/ledger.html',
            tab=tab,
            entries=display_entries,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            net_change=net_change,
            closing_balance=closing_balance
        )

    elif tab == 'savings':
        all_txs = Savings.query.order_by(Savings.date.asc(), Savings.id.asc()).all()
        running_bal = 0.0
        total_dep = 0.0
        total_wit = 0.0
        savings_entries = []
        for s in all_txs:
            is_dep = s.transaction_type == 'Deposit'
            dep = s.amount if is_dep else 0.0
            wit = s.amount if not is_dep else 0.0
            running_bal += (dep - wit)
            total_dep += dep
            total_wit += wit
            savings_entries.append({
                'id': s.id,
                'date': s.date,
                'type': s.transaction_type,
                'bank_name': s.bank_name,
                'description': s.description,
                'payment_method': s.payment_method,
                'deposit': dep,
                'withdrawal': wit,
                'running_balance': running_bal
            })
        savings_entries.reverse()  # Latest first for UI
        return render_template(
            'finance/savings.html',
            tab=tab,
            transactions=savings_entries,
            balance=running_bal,
            total_dep=total_dep,
            total_wit=total_wit
        )

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
            tot_in = 0.0
            tot_out = 0.0
            for tx in txs:
                amt = abs(tx.amount)
                money_in = 0.0
                money_out = 0.0
                if tx.transaction_type == 'Given':
                    if tx.amount >= 0:
                        running_bill_pending += amt
                        display_type = 'Bill Pending (Lena)'
                        money_out = amt
                    else:
                        running_bill_pending = max(0.0, running_bill_pending - amt)
                        display_type = 'Payment Received (Clear Lena)'
                        money_in = amt
                elif tx.transaction_type == 'Received':
                    running_bill_pending = max(0.0, running_bill_pending - amt)
                    display_type = 'Payment Received (Clear Lena)'
                    money_in = amt
                elif tx.transaction_type == 'Taken':
                    if tx.amount >= 0:
                        running_bill_received += amt
                        display_type = 'Bill Payable (Dena)'
                        money_in = amt
                    else:
                        running_bill_received = max(0.0, running_bill_received - amt)
                        display_type = 'Payment Paid (Clear Dena)'
                        money_out = amt
                elif tx.transaction_type == 'Paid':
                    running_bill_received = max(0.0, running_bill_received - amt)
                    display_type = 'Payment Paid (Clear Dena)'
                    money_out = amt
                else:
                    display_type = tx.transaction_type
                    if tx.amount >= 0:
                        money_in = amt
                    else:
                        money_out = amt

                tot_in += money_in
                tot_out += money_out

                ledger_entries.append({
                    'id': tx.id,
                    'date': tx.date,
                    'type': display_type,
                    'raw_type': tx.transaction_type,
                    'payment_method': tx.payment_method,
                    'description': tx.description or 'Credit transaction',
                    'amount': amt,
                    'money_in': money_in,
                    'money_out': money_out,
                    'running_bill_pending': running_bill_pending,
                    'running_bill_received': running_bill_received
                })

            display_ledger = list(reversed(ledger_entries))

            return render_template(
                'finance/credit_ledger.html',
                tab=tab,
                selected_party=selected_party,
                ledger_entries=display_ledger,
                tot_in=tot_in,
                tot_out=tot_out,
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
        tot_dep = 0.0
        tot_wit = 0.0
        md_ledger = []
        for tx in transactions:
            is_dep = tx.transaction_type == 'Deposit'
            dep = tx.amount if is_dep else 0.0
            wit = tx.amount if not is_dep else 0.0
            tot_dep += dep
            tot_wit += wit
            sign = 1 if is_dep else -1
            is_cash = tx.payment_method == 'Cash'
            if is_cash:
                running_cash += sign * tx.amount
            else:
                running_online += sign * tx.amount
            running_total += sign * tx.amount
            md_ledger.append({
                'tx': tx,
                'deposit': dep,
                'withdrawal': wit,
                'running_cash': running_cash,
                'running_online': running_online,
                'running_total': running_total
            })
        md_ledger.reverse()

        return render_template(
            'finance/md_account.html',
            tab=tab,
            md_ledger=md_ledger,
            tot_dep=tot_dep,
            tot_wit=tot_wit,
            balance_cash=running_cash,
            balance_online=running_online,
            balance_total=running_total,
            cash_balance=cash_balance
        )

    return redirect(url_for('finance.index'))


# =========================================================================
# FINANCE DEPOSIT & WITHDRAWAL LEDGER MANAGEMENT
# =========================================================================
@finance_bp.route('/ledger/add', methods=['GET', 'POST'])
@login_required
def ledger_add():
    form = FinanceLedgerForm()
    if form.validate_on_submit():
        entry_type = form.type.data  # Deposit or Withdrawal
        amount = form.amount.data
        
        CashBook.log_transaction(
            date=form.date.data,
            transaction_type=entry_type,
            amount=amount,
            source='FinanceLedger',
            reference_id=None,
            description=form.description.data,
            payment_method=form.payment_method.data,
            category=form.category.data,
            remarks=form.remarks.data
        )
        db.session.commit()
        flash(f"{entry_type} entry of ₹{amount:,.2f} recorded in Finance Ledger.", "success")
        return redirect(url_for('finance.index', tab='ledger'))
        
    return render_template('finance/form.html', form=form, title="Record Finance Ledger Entry")


@finance_bp.route('/ledger/delete/<int:entry_id>', methods=['POST'])
@login_required
def ledger_delete(entry_id):
    entry = CashBook.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.flush()
    CashBook.rebuild_balances()
    db.session.commit()
    flash("Ledger entry deleted successfully.", "success")
    return redirect(url_for('finance.index', tab='ledger'))


@finance_bp.route('/ledger/clear', methods=['POST'])
@login_required
def ledger_clear():
    CashBook.query.delete()
    db.session.commit()
    flash("Cash Book transactions cleared and Cash & Bank balances reset to ₹0.00.", "success")
    return redirect(url_for('finance.index', tab='ledger'))



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
            amount=abs(form.amount.data),
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

        # CashBook logging direction based on transaction_type:
        # Given (Bill Pending Lena): Cash Outflow (Out)
        # Received (Payment Received for Lena): Cash Inflow (In) -> Adds to Cash or Bank balance!
        # Taken (Bill Payable Dena): Cash Inflow (In)
        # Paid (Payment Paid for Dena): Cash Outflow (Out) -> Subtracts from Cash or Bank balance!
        ttype = tx.transaction_type
        amt = abs(tx.amount)
        if ttype == 'Given':
            cb_type = 'Out'
            label = 'Bill Pending (Lena Given)'
        elif ttype == 'Received':
            cb_type = 'In'
            label = 'Payment Received (Clear Lena)'
        elif ttype == 'Taken':
            cb_type = 'In'
            label = 'Bill Payable (Dena Taken)'
        elif ttype == 'Paid':
            cb_type = 'Out'
            label = 'Payment Paid (Clear Dena)'
        else:
            cb_type = 'Out' if tx.amount >= 0 else 'In'
            label = 'Credit Transaction'

        if amt > 0:
            if tx.payment_method == 'Split':
                if tx.cash_amount > 0:
                    CashBook.log_transaction(
                        date=tx.date,
                        transaction_type=cb_type,
                        amount=tx.cash_amount,
                        source='CreditTransaction',
                        reference_id=tx.id,
                        description=f"Credit {label} [{party.party_name}] (Split-Cash) - {tx.description or ''}",
                        payment_method='Cash'
                    )
                if tx.online_amount > 0:
                    CashBook.log_transaction(
                        date=tx.date,
                        transaction_type=cb_type,
                        amount=tx.online_amount,
                        source='CreditTransaction',
                        reference_id=tx.id,
                        description=f"Credit {label} [{party.party_name}] (Split-Online) - {tx.description or ''}",
                        payment_method='UPI'
                    )
            else:
                CashBook.log_transaction(
                    date=tx.date,
                    transaction_type=cb_type,
                    amount=amt,
                    source='CreditTransaction',
                    reference_id=tx.id,
                    description=f"Credit {label} [{party.party_name}] via {tx.payment_method} - {tx.description or ''}",
                    payment_method=tx.payment_method
                )

        db.session.commit()
        flash(f'Credit transaction "{label}" of ₹{amt:.2f} recorded for {party.party_name}.', 'success')
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


@finance_bp.route('/delete-bulk', methods=['POST'])
@login_required
def delete_bulk():
    entry_type = request.form.get('type')
    ids_str = request.form.get('ids', '')
    if not ids_str:
        flash("No items selected for deletion.", "warning")
        return redirect(request.referrer or url_for('dashboard.index'))
        
    try:
        id_list = [int(x) for x in ids_str.split(',') if x.strip()]
    except ValueError:
        flash("Invalid IDs provided.", "danger")
        return redirect(request.referrer or url_for('dashboard.index'))
        
    deleted_count = 0
    
    if entry_type == 'income':
        from app.models import Income
        incomes = Income.query.filter(Income.id.in_(id_list)).all()
        for item in incomes:
            CashBook.remove_transaction(source='Income', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'expense':
        from app.models import Expense
        expenses = Expense.query.filter(Expense.id.in_(id_list)).all()
        for item in expenses:
            CashBook.remove_transaction(source='Expense', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'savings':
        from app.models import Savings
        savings = Savings.query.filter(Savings.id.in_(id_list)).all()
        for item in savings:
            CashBook.remove_transaction(source='Savings', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'loan_repayment':
        from app.models import LoanRepayment, Loan
        repayments = LoanRepayment.query.filter(LoanRepayment.id.in_(id_list)).all()
        affected_loans = set()
        for item in repayments:
            affected_loans.add(item.loan_id)
            CashBook.remove_transaction(source='LoanRepayment', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
        db.session.flush()
        for loan_id in affected_loans:
            loan = Loan.query.get(loan_id)
            if loan:
                loan.recalculate_outstanding()
                
    elif entry_type == 'md_sir':
        from app.models import MDSirAccount
        md_txs = MDSirAccount.query.filter(MDSirAccount.id.in_(id_list)).all()
        for item in md_txs:
            CashBook.remove_transaction(source='MDSir', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'credit_transaction':
        from app.models import CreditTransaction, CreditAccount
        txs = CreditTransaction.query.filter(CreditTransaction.id.in_(id_list)).all()
        affected_parties = set()
        for item in txs:
            affected_parties.add(item.credit_account_id)
            CashBook.remove_transaction(source='CreditTransaction', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
        db.session.flush()
        for party_id in affected_parties:
            party = CreditAccount.query.get(party_id)
            if party:
                party.recalculate_balances()
                
    elif entry_type == 'vendor_bill':
        from app.models import VendorBill, Vendor
        bills = VendorBill.query.filter(VendorBill.id.in_(id_list)).all()
        affected_vendors = set()
        for item in bills:
            affected_vendors.add(item.vendor_id)
            db.session.delete(item)
            deleted_count += 1
        db.session.flush()
        for vendor_id in affected_vendors:
            vendor = Vendor.query.get(vendor_id)
            if vendor:
                vendor.recalculate_outstanding()
                
    elif entry_type == 'vendor_payment':
        from app.models import VendorPayment, Vendor
        payments = VendorPayment.query.filter(VendorPayment.id.in_(id_list)).all()
        affected_vendors = set()
        for item in payments:
            affected_vendors.add(item.vendor_id)
            CashBook.remove_transaction(source='VendorPayment', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
        db.session.flush()
        for vendor_id in affected_vendors:
            vendor = Vendor.query.get(vendor_id)
            if vendor:
                vendor.recalculate_outstanding()
                
    elif entry_type == 'staff_advance':
        from app.models import EmployeeAdvance, Employee
        advances = EmployeeAdvance.query.filter(EmployeeAdvance.id.in_(id_list)).all()
        affected_employees = set()
        for item in advances:
            affected_employees.add(item.employee_id)
            CashBook.remove_transaction(source='EmployeeAdvance', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
        db.session.flush()
        for emp_id in affected_employees:
            emp = Employee.query.get(emp_id)
            if emp:
                emp.recalculate_balances()
                
    elif entry_type == 'payroll':
        from app.models import Payroll, Employee
        payrolls = Payroll.query.filter(Payroll.id.in_(id_list)).all()
        affected_employees = set()
        for item in payrolls:
            affected_employees.add(item.employee_id)
            if item.paid_amount > 0:
                CashBook.remove_transaction(source='Payroll', reference_id=item.id)
            db.session.delete(item)
            deleted_count += 1
        for emp_id in affected_employees:
            emp = Employee.query.get(emp_id)
            if emp:
                emp.recalculate_balances()
                
    elif entry_type == 'employee':
        from app.models import Employee, EmployeeAdvance, Payroll
        employees = Employee.query.filter(Employee.id.in_(id_list)).all()
        for item in employees:
            advances = EmployeeAdvance.query.filter_by(employee_id=item.id).all()
            for adv in advances:
                CashBook.remove_transaction(source='EmployeeAdvance', reference_id=adv.id)
                
            payrolls = Payroll.query.filter_by(employee_id=item.id).all()
            for pay in payrolls:
                CashBook.remove_transaction(source='Payroll', reference_id=pay.id)
                
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'vendor':
        from app.models import Vendor, VendorPayment
        vendors = Vendor.query.filter(Vendor.id.in_(id_list)).all()
        for item in vendors:
            vendor_payments = VendorPayment.query.filter_by(vendor_id=item.id).all()
            for p in vendor_payments:
                CashBook.remove_transaction(source='VendorPayment', reference_id=p.id)
                
            db.session.delete(item)
            deleted_count += 1
            
    elif entry_type == 'credit_party':
        from app.models import CreditAccount, CreditTransaction
        parties = CreditAccount.query.filter(CreditAccount.id.in_(id_list)).all()
        for item in parties:
            txs = CreditTransaction.query.filter_by(credit_account_id=item.id).all()
            for tx in txs:
                CashBook.remove_transaction(source='CreditTransaction', reference_id=tx.id)
            db.session.delete(item)
            deleted_count += 1
                
    db.session.commit()
    flash(f"Successfully deleted {deleted_count} record(s).", "success")
    return redirect(request.referrer or url_for('dashboard.index'))


@finance_bp.route('/bulk-add', methods=['GET', 'POST'])
@login_required
def bulk_add():
    from flask import jsonify
    from datetime import date
    
    if request.method == 'POST':
        import json
        from flask_login import current_user
        from app.models import Income, Expense, Savings, LoanRepayment, Loan, MDSirAccount, CreditTransaction, CreditAccount, VendorBill, Vendor, VendorPayment, EmployeeAdvance, Employee
        
        data = request.get_json()
        if not data or 'type' not in data or 'rows' not in data:
            return jsonify({'success': False, 'message': 'Invalid payload.'}), 400
            
        entry_type = data['type']
        rows = data['rows']
        
        if not rows:
            return jsonify({'success': False, 'message': 'No rows to add.'}), 400
            
        try:
            created_count = 0
            for row in rows:
                desc_val = row.get('description', '')
                
                if entry_type not in ('employee', 'vendor', 'credit_party'):
                    date_val = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    amount_val = float(row['amount'])
                    pay_method = row.get('payment_method', 'Cash')
                    cash_val = float(row.get('cash_amount', 0.0))
                    online_val = float(row.get('online_amount', 0.0))
                    
                    if pay_method == 'Split':
                        if abs((cash_val + online_val) - amount_val) > 0.01:
                            return jsonify({'success': False, 'message': f"Row with amount {amount_val}: Split portions must sum to total amount."}), 400
                
                if entry_type == 'income':
                    income = Income(
                        date=date_val,
                        category=row['category'],
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val,
                        created_by_id=current_user.id
                    )
                    db.session.add(income)
                    db.session.flush()
                    
                    if income.payment_method == 'Split':
                        if income.cash_amount > 0:
                            CashBook.log_transaction(income.date, 'In', income.cash_amount, 'Income', income.id, f"Income (Split-Cash): {income.category} - {income.description or ''}", 'Cash')
                        if income.online_amount > 0:
                            CashBook.log_transaction(income.date, 'In', income.online_amount, 'Income', income.id, f"Income (Split-Online): {income.category} - {income.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(income.date, 'In', income.amount, 'Income', income.id, f"Income: {income.category} ({income.payment_method}) - {income.description or ''}", income.payment_method)
                    created_count += 1
                    
                elif entry_type == 'expense':
                    expense = Expense(
                        date=date_val,
                        type=row['expense_type'],
                        category=row['category'],
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val,
                        created_by_id=current_user.id
                    )
                    db.session.add(expense)
                    db.session.flush()
                    
                    if expense.payment_method == 'Split':
                        if expense.cash_amount > 0:
                            CashBook.log_transaction(expense.date, 'Out', expense.cash_amount, 'Expense', expense.id, f"Expense (Split-Cash) ({expense.type}): {expense.category} - {expense.description or ''}", 'Cash')
                        if expense.online_amount > 0:
                            CashBook.log_transaction(expense.date, 'Out', expense.online_amount, 'Expense', expense.id, f"Expense (Split-Online) ({expense.type}): {expense.category} - {expense.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(expense.date, 'Out', expense.amount, 'Expense', expense.id, f"Expense ({expense.type}): {expense.category} ({expense.payment_method}) - {expense.description or ''}", expense.payment_method)
                    created_count += 1
                    
                elif entry_type == 'savings':
                    tx_type = row['transaction_type']
                    savings = Savings(
                        date=date_val,
                        transaction_type=tx_type,
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        bank_name=row['bank_name'],
                        description=desc_val
                    )
                    db.session.add(savings)
                    db.session.flush()
                    
                    cb_type = 'Out' if savings.transaction_type == 'Deposit' else 'In'
                    if savings.payment_method == 'Split':
                        if savings.cash_amount > 0:
                            CashBook.log_transaction(savings.date, cb_type, savings.cash_amount, 'Savings', savings.id, f"Savings {savings.transaction_type} (Split-Cash) to/from {savings.bank_name} - {savings.description or ''}", 'Cash')
                        if savings.online_amount > 0:
                            CashBook.log_transaction(savings.date, cb_type, savings.online_amount, 'Savings', savings.id, f"Savings {savings.transaction_type} (Split-Online) to/from {savings.bank_name} - {savings.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(savings.date, cb_type, savings.amount, 'Savings', savings.id, f"Savings {savings.transaction_type} to {savings.bank_name} - {savings.description or ''}", savings.payment_method)
                    created_count += 1
                    
                elif entry_type == 'loan_repayment':
                    bank = row['bank_name'].strip()
                    loan = Loan.query.filter(db.func.lower(Loan.lender_name) == bank.lower()).first()
                    if not loan:
                        loan = Loan(lender_name=bank, principal_amount=0.0, outstanding_balance=0.0, payment_method='Cash', description='Automatically created for installments tracking')
                        db.session.add(loan)
                        db.session.flush()
                        
                    repayment = LoanRepayment(
                        loan_id=loan.id,
                        date=date_val,
                        principal_paid=amount_val,
                        interest_paid=0.0,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val
                    )
                    db.session.add(repayment)
                    db.session.flush()
                    loan.recalculate_outstanding()
                    
                    if repayment.payment_method == 'Split':
                        if repayment.cash_amount > 0:
                            CashBook.log_transaction(repayment.date, 'Out', repayment.cash_amount, 'LoanRepayment', repayment.id, f"Loan Installment Paid (Split-Cash) ({loan.lender_name}) - {repayment.description or ''}", 'Cash')
                        if repayment.online_amount > 0:
                            CashBook.log_transaction(repayment.date, 'Out', repayment.online_amount, 'LoanRepayment', repayment.id, f"Loan Installment Paid (Split-Online) ({loan.lender_name}) - {repayment.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(repayment.date, 'Out', repayment.principal_paid, 'LoanRepayment', repayment.id, f"Loan Installment Paid ({loan.lender_name}): Amount ₹{repayment.principal_paid} via {repayment.payment_method}", repayment.payment_method)
                    created_count += 1
                    
                elif entry_type == 'md_sir':
                    tx_type = row['transaction_type']
                    md_tx = MDSirAccount(
                        date=date_val,
                        transaction_type=tx_type,
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val
                    )
                    db.session.add(md_tx)
                    db.session.flush()
                    
                    cb_type = 'In' if md_tx.transaction_type == 'Deposit' else 'Out'
                    if md_tx.payment_method == 'Split':
                        if md_tx.cash_amount > 0:
                            CashBook.log_transaction(md_tx.date, cb_type, md_tx.cash_amount, 'MDSir', md_tx.id, f"MD Sir: {md_tx.transaction_type} (Split-Cash) - {md_tx.description or ''}", 'Cash')
                        if md_tx.online_amount > 0:
                            CashBook.log_transaction(md_tx.date, cb_type, md_tx.online_amount, 'MDSir', md_tx.id, f"MD Sir: {md_tx.transaction_type} (Split-Online) - {md_tx.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(md_tx.date, cb_type, md_tx.amount, 'MDSir', md_tx.id, f"MD Sir: {md_tx.transaction_type} ({md_tx.payment_method}) - {md_tx.description or ''}", md_tx.payment_method)
                    created_count += 1
                    
                elif entry_type == 'credit_transaction':
                    party_id = int(row['credit_account_id'])
                    tx_type = row['transaction_type']
                    tx = CreditTransaction(
                        credit_account_id=party_id,
                        date=date_val,
                        transaction_type=tx_type,
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val
                    )
                    db.session.add(tx)
                    db.session.flush()
                    
                    party = CreditAccount.query.get(party_id)
                    party.recalculate_balances()
                    
                    ttype = tx.transaction_type
                    amt = abs(tx.amount)
                    if ttype == 'Given':
                        cb_type = 'Out'
                        label = 'Bill Pending (Lena Given)'
                    elif ttype == 'Received':
                        cb_type = 'In'
                        label = 'Payment Received (Clear Lena)'
                    elif ttype == 'Taken':
                        cb_type = 'In'
                        label = 'Bill Payable (Dena Taken)'
                    elif ttype == 'Paid':
                        cb_type = 'Out'
                        label = 'Payment Paid (Clear Dena)'
                    else:
                        cb_type = 'Out' if tx.amount >= 0 else 'In'
                        label = 'Credit Transaction'

                    if amt > 0:
                        if tx.payment_method == 'Split':
                            if tx.cash_amount > 0:
                                CashBook.log_transaction(tx.date, cb_type, tx.cash_amount, 'CreditTransaction', tx.id, f"Credit {label} [{party.party_name}] (Split-Cash) - {tx.description or ''}", 'Cash')
                            if tx.online_amount > 0:
                                CashBook.log_transaction(tx.date, cb_type, tx.online_amount, 'CreditTransaction', tx.id, f"Credit {label} [{party.party_name}] (Split-Online) - {tx.description or ''}", 'UPI')
                        else:
                            CashBook.log_transaction(tx.date, cb_type, amt, 'CreditTransaction', tx.id, f"Credit {label} [{party.party_name}] via {tx.payment_method} - {tx.description or ''}", tx.payment_method)
                    created_count += 1
                    
                elif entry_type == 'vendor_bill':
                    vendor_id = int(row['vendor_id'])
                    bill = VendorBill(
                        vendor_id=vendor_id,
                        bill_number=row['bill_number'],
                        date=date_val,
                        amount=amount_val,
                        description=desc_val
                    )
                    db.session.add(bill)
                    db.session.flush()
                    vendor = Vendor.query.get(vendor_id)
                    vendor.recalculate_outstanding()
                    created_count += 1
                    
                elif entry_type == 'vendor_payment':
                    vendor_id = int(row['vendor_id'])
                    payment = VendorPayment(
                        vendor_id=vendor_id,
                        date=date_val,
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val
                    )
                    db.session.add(payment)
                    db.session.flush()
                    vendor = Vendor.query.get(vendor_id)
                    vendor.recalculate_outstanding()
                    
                    if payment.payment_method == 'Split':
                        if payment.cash_amount > 0:
                            CashBook.log_transaction(payment.date, 'Out', payment.cash_amount, 'VendorPayment', payment.id, f"Vendor Payment (Split-Cash): {vendor.name} - {payment.description or ''}", 'Cash')
                        if payment.online_amount > 0:
                            CashBook.log_transaction(payment.date, 'Out', payment.online_amount, 'VendorPayment', payment.id, f"Vendor Payment (Split-Online): {vendor.name} - {payment.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(payment.date, 'Out', payment.amount, 'VendorPayment', payment.id, f"Vendor Payment: {vendor.name} ({payment.payment_method}) - {payment.description or ''}", payment.payment_method)
                    created_count += 1
                    
                elif entry_type == 'staff_advance':
                    emp_id = int(row['employee_id'])
                    adv = EmployeeAdvance(
                        employee_id=emp_id,
                        date=date_val,
                        amount=amount_val,
                        payment_method=pay_method,
                        cash_amount=cash_val if pay_method == 'Split' else 0.0,
                        online_amount=online_val if pay_method == 'Split' else 0.0,
                        description=desc_val
                    )
                    db.session.add(adv)
                    db.session.flush()
                    emp = Employee.query.get(emp_id)
                    emp.recalculate_balances()
                    
                    if adv.payment_method == 'Split':
                        if adv.cash_amount > 0:
                            CashBook.log_transaction(adv.date, 'Out', adv.cash_amount, 'EmployeeAdvance', adv.id, f"Staff Advance (Split-Cash): {emp.name} - {adv.description or ''}", 'Cash')
                        if adv.online_amount > 0:
                            CashBook.log_transaction(adv.date, 'Out', adv.online_amount, 'EmployeeAdvance', adv.id, f"Staff Advance (Split-Online): {emp.name} - {adv.description or ''}", 'UPI')
                    else:
                        CashBook.log_transaction(adv.date, 'Out', adv.amount, 'EmployeeAdvance', adv.id, f"Staff Advance: {emp.name} ({adv.payment_method}) - {adv.description or ''}", adv.payment_method)
                    created_count += 1
                    
                elif entry_type == 'employee':
                    emp = Employee(
                        name=row['name'],
                        designation=row.get('designation', ''),
                        basic_salary=float(row.get('basic_salary', 0.0)),
                        salary_type=row.get('salary_type', 'Monthly'),
                        phone=row.get('phone', ''),
                        email=row.get('email', '')
                    )
                    db.session.add(emp)
                    created_count += 1
                    
                elif entry_type == 'vendor':
                    vendor = Vendor(
                        name=row['name'],
                        contact_person=row.get('contact_person', ''),
                        phone=row.get('phone', ''),
                        email=row.get('email', ''),
                        address=row.get('address', '')
                    )
                    db.session.add(vendor)
                    created_count += 1
                    
                elif entry_type == 'credit_party':
                    party = CreditAccount(
                        party_name=row['name'],
                        phone=row.get('phone', ''),
                        receivable_balance=0.0,
                        payable_balance=0.0
                    )
                    db.session.add(party)
                    created_count += 1
                    
            db.session.commit()
            return jsonify({'success': True, 'message': f"Successfully saved {created_count} transaction(s)."})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f"Error: {str(e)}"}), 500
            
    # GET request
    from app.models import Vendor, Employee, CreditAccount
    from flask import current_app
    
    vendors = [{'id': v.id, 'name': v.name} for v in Vendor.query.order_by(Vendor.name.asc()).all()]
    employees = [{'id': e.id, 'name': e.name} for e in Employee.query.filter_by(status='Active').order_by(Employee.name.asc()).all()]
    parties = [{'id': c.id, 'name': c.party_name} for c in CreditAccount.query.order_by(CreditAccount.party_name.asc()).all()]
    
    expense_cats = current_app.config.get('EXPENSE_TYPES', {})
    # Get all subcategory arrays flattened or grouped
    expense_list = []
    for k, v in expense_cats.items():
        expense_list.extend(v)
    expense_list = sorted(list(set(expense_list)))
    
    income_cats = ['Old Bill Received', 'Restaurant Revenue', 'Banquet Revenue', 'Opening Balance', 'Other Revenue']
    
    default_type = request.args.get('type', 'income')
    
    return render_template(
        'finance/bulk_add.html',
        vendors=vendors,
        employees=employees,
        parties=parties,
        expense_cats=expense_list,
        income_cats=income_cats,
        default_type=default_type
    )
