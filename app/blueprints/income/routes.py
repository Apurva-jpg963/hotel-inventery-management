from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.blueprints.income import income_bp
from app.blueprints.income.forms import IncomeForm
from app.models import Income, CashBook
from datetime import datetime

@income_bp.route('/')
@login_required
def index():
    # Search and Filter Parameters
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    query = Income.query

    # Apply Filters
    if search_query:
        query = query.filter(Income.description.ilike(f'%{search_query}%'))
    if category_filter:
        query = query.filter(Income.category == category_filter)
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Income.date >= start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(Income.date <= end_date)
        except ValueError:
            pass

    # Pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Income.date.desc(), Income.id.desc()).paginate(page=page, per_page=15, error_out=False)
    incomes = pagination.items

    return render_template(
        'income/index.html',
        incomes=incomes,
        pagination=pagination,
        search_query=search_query,
        category_filter=category_filter,
        start_date=start_date_str,
        end_date=end_date_str
    )


@income_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = IncomeForm()
    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('income/add_edit.html', form=form, title="Record Income")

        income = Income(
            date=form.date.data,
            category=form.category.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data,
            created_by_id=current_user.id
        )
        db.session.add(income)
        db.session.flush()  # Populate income.id before logging transaction

        # Automation Rule: Income increases balance (log inflow in CashBook)
        if income.payment_method == 'Split':
            if income.cash_amount > 0:
                CashBook.log_transaction(
                    date=income.date,
                    transaction_type='In',
                    amount=income.cash_amount,
                    source='Income',
                    reference_id=income.id,
                    description=f"Income (Split-Cash): {income.category} - {income.description or ''}",
                    payment_method='Cash'
                )
            if income.online_amount > 0:
                CashBook.log_transaction(
                    date=income.date,
                    transaction_type='In',
                    amount=income.online_amount,
                    source='Income',
                    reference_id=income.id,
                    description=f"Income (Split-Online): {income.category} - {income.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=income.date,
                transaction_type='In',
                amount=income.amount,
                source='Income',
                reference_id=income.id,
                description=f"Income: {income.category} ({income.payment_method}) - {income.description or ''}",
                payment_method=income.payment_method
            )
        
        db.session.commit()
        flash(f'Income of {income.amount} recorded successfully!', 'success')
        return redirect(url_for('income.index'))

    return render_template('income/add_edit.html', form=form, title="Record Income")


@income_bp.route('/edit/<int:income_id>', methods=['GET', 'POST'])
@login_required
def edit(income_id):
    income = Income.query.get_or_404(income_id)
    form = IncomeForm(obj=income)
    
    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('income/add_edit.html', form=form, title="Edit Income Record", income=income)

        # Remove old CashBook entry
        CashBook.remove_transaction(source='Income', reference_id=income.id)

        # Update values
        income.date = form.date.data
        income.category = form.category.data
        income.amount = form.amount.data
        income.payment_method = form.payment_method.data
        income.cash_amount = form.cash_amount.data if form.payment_method.data == 'Split' else 0.0
        income.online_amount = form.online_amount.data if form.payment_method.data == 'Split' else 0.0
        income.description = form.description.data
        
        # Log new cashbook entry
        if income.payment_method == 'Split':
            if income.cash_amount > 0:
                CashBook.log_transaction(
                    date=income.date,
                    transaction_type='In',
                    amount=income.cash_amount,
                    source='Income',
                    reference_id=income.id,
                    description=f"Income (Split-Cash): {income.category} - {income.description or ''}",
                    payment_method='Cash'
                )
            if income.online_amount > 0:
                CashBook.log_transaction(
                    date=income.date,
                    transaction_type='In',
                    amount=income.online_amount,
                    source='Income',
                    reference_id=income.id,
                    description=f"Income (Split-Online): {income.category} - {income.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=income.date,
                transaction_type='In',
                amount=income.amount,
                source='Income',
                reference_id=income.id,
                description=f"Income: {income.category} ({income.payment_method}) - {income.description or ''}",
                payment_method=income.payment_method
            )
        
        db.session.commit()
        flash('Income record updated successfully!', 'success')
        return redirect(url_for('income.index'))

    return render_template('income/add_edit.html', form=form, title="Edit Income Record", income=income)


@income_bp.route('/delete/<int:income_id>', methods=['POST'])
@login_required
def delete(income_id):
    income = Income.query.get_or_404(income_id)
    amount = income.amount
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='Income', reference_id=income.id)
    db.session.delete(income)
    db.session.commit()
    
    flash(f'Income of {amount} has been deleted successfully.', 'success')
    return redirect(url_for('income.index'))
