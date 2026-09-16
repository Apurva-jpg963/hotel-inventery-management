from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.blueprints.expense import expense_bp
from app.blueprints.expense.forms import ExpenseForm
from app.models import Expense, CashBook
from datetime import datetime
from flask import current_app

@expense_bp.route('/')
@login_required
def index():
    # Fetch Type: Hotel, Other, Development (defaults to Hotel)
    expense_type = request.args.get('type', 'Hotel')
    if expense_type not in ['Hotel', 'Other', 'Development']:
        expense_type = 'Hotel'

    # Search and Filter Parameters
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    query = Expense.query.filter_by(type=expense_type)

    # Apply Filters
    if search_query:
        query = query.filter(Expense.description.ilike(f'%{search_query}%'))
    if category_filter:
        query = query.filter(Expense.category == category_filter)
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= start_date)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= end_date)
        except ValueError:
            pass

    # Pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Expense.date.desc(), Expense.id.desc()).paginate(page=page, per_page=100, error_out=False)
    expenses = pagination.items

    # Fetch Categories for dropdown filter based on type
    available_categories = []
    if expense_type == 'Hotel':
        available_categories = current_app.config['EXPENSE_TYPES']['Hotel']
    elif expense_type == 'Other':
        available_categories = current_app.config['EXPENSE_TYPES']['Other']
    elif expense_type == 'Development':
        available_categories = current_app.config['EXPENSE_TYPES']['Development']

    # Also grab custom categories that already exist in database for this type
    db_categories = db.session.query(Expense.category).filter_by(type=expense_type).distinct().all()
    for cat in db_categories:
        if cat[0] not in available_categories:
            available_categories.append(cat[0])

    return render_template(
        'expense/index.html',
        expenses=expenses,
        pagination=pagination,
        expense_type=expense_type,
        search_query=search_query,
        category_filter=category_filter,
        start_date=start_date_str,
        end_date=end_date_str,
        categories=available_categories
    )


@expense_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    expense_type = request.args.get('type', 'Hotel')
    if expense_type not in ['Hotel', 'Other', 'Development']:
        expense_type = 'Hotel'
        
    form = ExpenseForm()
    # Populate the type field choice or select default
    form.type.data = expense_type

    # Load categories for type to assist autocomplete/dropdown in frontend
    categories = current_app.config['EXPENSE_TYPES'].get(expense_type, [])
    # Also fetch existing custom categories from db
    db_categories = db.session.query(Expense.category).filter_by(type=expense_type).distinct().all()
    for cat in db_categories:
        if cat[0] not in categories:
            categories.append(cat[0])

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template(
                    'expense/add_edit.html',
                    form=form,
                    title="Record Expense",
                    expense_type=expense_type,
                    categories=categories
                )

        expense = Expense(
            date=form.date.data,
            type=form.type.data,
            category=form.category.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data,
            created_by_id=current_user.id
        )
        db.session.add(expense)
        db.session.flush()

        # Automation Rule: Expense decreases cash balance (log outflow in CashBook)
        if expense.payment_method == 'Split':
            if expense.cash_amount > 0:
                CashBook.log_transaction(
                    date=expense.date,
                    transaction_type='Out',
                    amount=expense.cash_amount,
                    source='Expense',
                    reference_id=expense.id,
                    description=f"Expense (Split-Cash) ({expense.type}): {expense.category} - {expense.description or ''}",
                    payment_method='Cash'
                )
            if expense.online_amount > 0:
                CashBook.log_transaction(
                    date=expense.date,
                    transaction_type='Out',
                    amount=expense.online_amount,
                    source='Expense',
                    reference_id=expense.id,
                    description=f"Expense (Split-Online) ({expense.type}): {expense.category} - {expense.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=expense.date,
                transaction_type='Out',
                amount=expense.amount,
                source='Expense',
                reference_id=expense.id,
                description=f"Expense ({expense.type}): {expense.category} ({expense.payment_method}) - {expense.description or ''}",
                payment_method=expense.payment_method
            )

        db.session.commit()
        flash(f'Expense of {expense.amount} recorded successfully under {expense.type}!', 'success')
        return redirect(url_for('expense.index', type=expense.type))

    return render_template(
        'expense/add_edit.html',
        form=form,
        title="Record Expense",
        expense_type=expense_type,
        categories=categories
    )


@expense_bp.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    
    # Load categories for autocomplete
    categories = current_app.config['EXPENSE_TYPES'].get(expense.type, [])
    db_categories = db.session.query(Expense.category).filter_by(type=expense.type).distinct().all()
    for cat in db_categories:
        if cat[0] not in categories:
            categories.append(cat[0])

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template(
                    'expense/add_edit.html',
                    form=form,
                    title="Edit Expense Record",
                    expense_type=expense.type,
                    categories=categories,
                    expense=expense
                )

        # Remove old CashBook log
        CashBook.remove_transaction(source='Expense', reference_id=expense.id)

        # Update values
        expense.date = form.date.data
        expense.type = form.type.data
        expense.category = form.category.data
        expense.amount = form.amount.data
        expense.payment_method = form.payment_method.data
        expense.cash_amount = form.cash_amount.data if form.payment_method.data == 'Split' else 0.0
        expense.online_amount = form.online_amount.data if form.payment_method.data == 'Split' else 0.0
        expense.description = form.description.data
        
        # Log new cashbook entry
        if expense.payment_method == 'Split':
            if expense.cash_amount > 0:
                CashBook.log_transaction(
                    date=expense.date,
                    transaction_type='Out',
                    amount=expense.cash_amount,
                    source='Expense',
                    reference_id=expense.id,
                    description=f"Expense (Split-Cash) ({expense.type}): {expense.category} - {expense.description or ''}",
                    payment_method='Cash'
                )
            if expense.online_amount > 0:
                CashBook.log_transaction(
                    date=expense.date,
                    transaction_type='Out',
                    amount=expense.online_amount,
                    source='Expense',
                    reference_id=expense.id,
                    description=f"Expense (Split-Online) ({expense.type}): {expense.category} - {expense.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=expense.date,
                transaction_type='Out',
                amount=expense.amount,
                source='Expense',
                reference_id=expense.id,
                description=f"Expense ({expense.type}): {expense.category} ({expense.payment_method}) - {expense.description or ''}",
                payment_method=expense.payment_method
            )

        db.session.commit()
        flash('Expense record updated successfully!', 'success')
        return redirect(url_for('expense.index', type=expense.type))

    return render_template(
        'expense/add_edit.html',
        form=form,
        title="Edit Expense Record",
        expense_type=expense.type,
        categories=categories,
        expense=expense
    )


@expense_bp.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    amount = expense.amount
    expense_type = expense.type
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='Expense', reference_id=expense.id)
    db.session.delete(expense)
    db.session.commit()
    
    flash(f'Expense of {amount} has been deleted.', 'success')
    return redirect(url_for('expense.index', type=expense_type))
