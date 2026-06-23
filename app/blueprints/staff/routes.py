from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.blueprints.staff import staff_bp
from app.blueprints.staff.forms import EmployeeForm, AdvanceForm, PayrollPaymentForm, StaffSalaryPaymentForm
from app.models import Employee, Attendance, EmployeeAdvance, Payroll, CashBook
from datetime import datetime, date
import calendar

@staff_bp.route('/')
@login_required
def index():
    view = request.args.get('view', 'employees')
    search_query = request.args.get('search', '')
    
    if view == 'employees':
        query = Employee.query
        if search_query:
            query = query.filter(
                (Employee.name.ilike(f'%{search_query}%')) | 
                (Employee.designation.ilike(f'%{search_query}%'))
            )
        employees = query.order_by(Employee.name.asc()).all()
        return render_template('staff/index.html', view=view, employees=employees, search_query=search_query)

    elif view == 'attendance':
        flash("Attendance logging is disabled.", "info")
        return redirect(url_for('staff.index'))

    elif view == 'payroll':
        query = Payroll.query
        if search_query:
            query = query.join(Employee).filter(Employee.name.ilike(f'%{search_query}%'))
        payrolls = query.order_by(Payroll.month.desc(), Payroll.id.desc()).all()
        
        # Also grab advances list to show in panel
        advances = EmployeeAdvance.query.order_by(EmployeeAdvance.date.desc()).all()
        
        return render_template(
            'staff/payroll.html',
            view=view,
            payrolls=payrolls,
            advances=advances,
            search_query=search_query
        )

    elif view == 'ledgers':
        # Select employee list
        employees = Employee.query.order_by(Employee.name.asc()).all()
        employee_id = request.args.get('employee_id', type=int)
        
        selected_employee = None
        ledger_entries = []
        
        if employee_id:
            selected_employee = Employee.query.get_or_404(employee_id)
            
            # Fetch advances and payroll records
            advances = EmployeeAdvance.query.filter_by(employee_id=employee_id).all()
            payrolls = Payroll.query.filter_by(employee_id=employee_id).all()
            
            for adv in advances:
                ledger_entries.append({
                    'date': adv.date,
                    'type': 'Advance Salary',
                    'reference': 'Advance Issued',
                    'description': adv.description or 'Salary Advance',
                    'debit': adv.amount,   # Cash given to employee
                    'credit': 0.0,
                    'sort_id': f"adv-{adv.id}"
                })
            for pay in payrolls:
                # Add calculated salary debit (what we owe them)
                try:
                    accrued_date = datetime.strptime(f"{pay.month}-01", "%Y-%m-%d").date()
                except ValueError:
                    accrued_date = pay.payment_date or date.today()

                ledger_entries.append({
                    'date': accrued_date,
                    'type': f"Salary Accrued ({pay.month})",
                    'reference': 'Payroll generated',
                    'description': f"Gross: {pay.calculated_salary} | Adj: {pay.advance_adjusted} | Ded: {pay.deductions}",
                    'debit': pay.net_payable,
                    'credit': 0.0,
                    'sort_id': f"acc-{pay.id}"
                })
                # Add actual payment credit (what we paid them)
                if pay.paid_amount > 0:
                    try:
                        payment_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
                    except ValueError:
                        payment_date = pay.payment_date or date.today()

                    ledger_entries.append({
                        'date': payment_date,
                        'type': f"Salary Payment ({pay.month})",
                        'reference': pay.payment_method or 'Cash',
                        'description': 'Released payroll cash',
                        'debit': 0.0,
                        'credit': pay.paid_amount,
                        'sort_id': f"pay-{pay.id}"
                    })
                # Adjusting advance also acts as a credit against their advance ledger
                if pay.advance_adjusted > 0:
                    try:
                        recovery_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
                    except ValueError:
                        recovery_date = pay.payment_date or date.today()

                    ledger_entries.append({
                        'date': recovery_date,
                        'type': 'Advance Recovery',
                        'reference': 'Payroll adjustment',
                        'description': 'Recovered from basic salary',
                        'debit': 0.0,
                        'credit': pay.advance_adjusted,
                        'sort_id': f"rec-{pay.id}"
                    })
                    
            ledger_entries.sort(key=lambda x: (x['date'], x['sort_id']))
            
            # Running Balance calculation: What we owe the employee
            running = 0.0
            for entry in ledger_entries:
                if 'Accrued' in entry['type']:
                    running += entry['debit']
                elif 'Payment' in entry['type']:
                    running -= entry['credit']
                # For advances, it's cash we gave, so it's a debit to advance balance
                entry['running_balance'] = running

        return render_template(
            'staff/ledger.html',
            view=view,
            employees=employees,
            selected_employee=selected_employee,
            ledger_entries=ledger_entries
        )

    return redirect(url_for('staff.index'))


@staff_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            designation=form.designation.data,
            salary_type='Daily',
            basic_salary=form.basic_salary.data,
            status=form.status.data
        )
        db.session.add(employee)
        db.session.commit()
        flash(f'Employee profile for "{employee.name}" created successfully!', 'success')
        return redirect(url_for('staff.index', view='employees'))
    return render_template('staff/form.html', form=form, title="Create Employee Profile")


@staff_bp.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        employee.name = form.name.data
        employee.phone = form.phone.data
        employee.email = form.email.data
        employee.designation = form.designation.data
        employee.salary_type = 'Daily'
        employee.basic_salary = form.basic_salary.data
        employee.status = form.status.data
        db.session.commit()
        flash(f'Employee profile for "{employee.name}" updated.', 'success')
        return redirect(url_for('staff.index', view='employees'))
    return render_template('staff/form.html', form=form, title="Edit Employee Profile", employee=employee)


@staff_bp.route('/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    name = employee.name
    
    # Clean CashBook entries for advances and payroll payments
    advances = EmployeeAdvance.query.filter_by(employee_id=employee_id).all()
    for adv in advances:
        CashBook.remove_transaction(source='EmployeeAdvance', reference_id=adv.id)
        
    payrolls = Payroll.query.filter_by(employee_id=employee_id).all()
    for pay in payrolls:
        CashBook.remove_transaction(source='Payroll', reference_id=pay.id)

    db.session.delete(employee)
    db.session.commit()
    flash(f'Employee profile for "{name}" and all records deleted.', 'success')
    return redirect(url_for('staff.index', view='employees'))


@staff_bp.route('/attendance/save', methods=['POST'])
@login_required
def attendance_save():
    date_str = request.form.get('date')
    log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    employees = Employee.query.filter_by(status='Active').all()
    for emp in employees:
        status_key = f"status-{emp.id}"
        note_key = f"note-{emp.id}"
        
        status = request.form.get(status_key)
        note = request.form.get(note_key, '')
        
        if status:
            # Check if record already exists for this date and employee
            record = Attendance.query.filter_by(employee_id=emp.id, date=log_date).first()
            if record:
                record.status = status
                record.note = note
            else:
                record = Attendance(
                    employee_id=emp.id,
                    date=log_date,
                    status=status,
                    note=note
                )
                db.session.add(record)
                
    db.session.commit()
    flash(f"Attendance logged successfully for date: {log_date.strftime('%d-%b-%Y')}", "success")
    return redirect(url_for('staff.index', view='attendance', date=date_str))


@staff_bp.route('/advance/add', methods=['GET', 'POST'])
@login_required
def advance_add():
    form = AdvanceForm()
    form.employee_id.choices = [(e.id, f"{e.name} ({e.designation})") for e in Employee.query.filter_by(status='Active').order_by(Employee.name.asc()).all()]
    
    employee_id = request.args.get('employee_id', type=int)
    if employee_id and request.method == 'GET':
        form.employee_id.data = employee_id

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('staff/form.html', form=form, title="Issue Employee Advance")

        advance = EmployeeAdvance(
            employee_id=form.employee_id.data,
            date=form.date.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data
        )
        db.session.add(advance)
        db.session.flush()

        # Recalculate employee balances
        employee = Employee.query.get(advance.employee_id)
        employee.recalculate_balances()

        # Automation Rule: Advance salary payment decreases central balance (log cashbook outflow)
        if advance.payment_method == 'Split':
            if advance.cash_amount > 0:
                CashBook.log_transaction(
                    date=advance.date,
                    transaction_type='Out',
                    amount=advance.cash_amount,
                    source='EmployeeAdvance',
                    reference_id=advance.id,
                    description=f"Staff Advance (Split-Cash): {employee.name} - {advance.description or ''}",
                    payment_method='Cash'
                )
            if advance.online_amount > 0:
                CashBook.log_transaction(
                    date=advance.date,
                    transaction_type='Out',
                    amount=advance.online_amount,
                    source='EmployeeAdvance',
                    reference_id=advance.id,
                    description=f"Staff Advance (Split-Online): {employee.name} - {advance.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=advance.date,
                transaction_type='Out',
                amount=advance.amount,
                source='EmployeeAdvance',
                reference_id=advance.id,
                description=f"Staff Advance: {employee.name} - {advance.description or ''}",
                payment_method=advance.payment_method
            )

        db.session.commit()
        flash(f'Salary advance of {advance.amount} paid to {employee.name}.', 'success')
        return redirect(url_for('staff.index', view='payroll'))

    return render_template('staff/form.html', form=form, title="Issue Employee Advance")


@staff_bp.route('/advance/delete/<int:advance_id>', methods=['POST'])
@login_required
def advance_delete(advance_id):
    advance = EmployeeAdvance.query.get_or_404(advance_id)
    employee_id = advance.employee_id
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='EmployeeAdvance', reference_id=advance.id)
    db.session.delete(advance)
    db.session.flush()
    
    # Recalculate employee balances
    employee = Employee.query.get(employee_id)
    employee.recalculate_balances()
    
    db.session.commit()
    flash('Advance record deleted successfully.', 'success')
    return redirect(url_for('staff.index', view='payroll'))


@staff_bp.route('/payroll/calculate', methods=['GET'])
@login_required
def payroll_calculate():
    employee_id = request.args.get('employee_id', type=int)
    
    if not employee_id:
        return jsonify({'error': 'Missing employee_id'}), 400
        
    employee = Employee.query.get_or_404(employee_id)
    
    # Fetch outstanding advance balance
    advance_bal = employee.advance_balance
    
    return jsonify({
        'basic_salary': employee.basic_salary,
        'salary_type': employee.salary_type,
        'advance_balance': advance_bal
    })


@staff_bp.route('/payroll/add', methods=['GET', 'POST'])
@login_required
def payroll_add():
    form = PayrollPaymentForm()
    form.employee_id.choices = [(e.id, f"{e.name} ({e.designation})") for e in Employee.query.filter_by(status='Active').order_by(Employee.name.asc()).all()]
    
    employee_id = request.args.get('employee_id', type=int)
    
    if employee_id and request.method == 'GET':
        form.employee_id.data = employee_id

    if form.validate_on_submit():
        emp_id = form.employee_id.data
        payroll_month = form.month.data

        days_present = form.days_present.data
        calculated_salary = form.calculated_salary.data
        advance_adjusted = form.advance_adjusted.data
        deductions = form.deductions.data
        net_payable = form.net_payable.data
        paid_amount = form.paid_amount.data
        
        if paid_amount > 0 and form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - paid_amount) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the released Paid Amount.", "danger")
                return render_template('staff/form.html', form=form, title="Release Employee Payroll")
        
        # Calculate pending amount
        pending_amount = max(0.0, net_payable - paid_amount)
        
        # Determine status
        if pending_amount == 0:
            status = 'Paid'
        elif paid_amount > 0:
            status = 'Partial'
        else:
            status = 'Pending'
            
        payroll = Payroll(
            employee_id=emp_id,
            month=payroll_month,
            days_present=days_present,
            calculated_salary=calculated_salary,
            advance_adjusted=advance_adjusted,
            deductions=deductions,
            net_payable=net_payable,
            paid_amount=paid_amount,
            pending_amount=pending_amount,
            payment_status=status,
            payment_date=date.today() if paid_amount > 0 else None,
            payment_method=form.payment_method.data if paid_amount > 0 else None,
            cash_amount=form.cash_amount.data if (paid_amount > 0 and form.payment_method.data == 'Split') else 0.0,
            online_amount=form.online_amount.data if (paid_amount > 0 and form.payment_method.data == 'Split') else 0.0,
            created_at=datetime.utcnow()
        )
        
        db.session.add(payroll)
        db.session.flush()

        # Recalculate employee advance and outstanding balances
        employee = Employee.query.get(emp_id)
        employee.recalculate_balances()

        # Automation Rule: Payroll salary payment decreases central balance (log cashbook outflow if paid > 0)
        if paid_amount > 0:
            if payroll.payment_method == 'Split':
                if payroll.cash_amount > 0:
                    CashBook.log_transaction(
                        date=date.today(),
                        transaction_type='Out',
                        amount=payroll.cash_amount,
                        source='Payroll',
                        reference_id=payroll.id,
                        description=f"Staff Salary (Split-Cash): {employee.name} ({payroll.month})",
                        payment_method='Cash'
                    )
                if payroll.online_amount > 0:
                    CashBook.log_transaction(
                        date=date.today(),
                        transaction_type='Out',
                        amount=payroll.online_amount,
                        source='Payroll',
                        reference_id=payroll.id,
                        description=f"Staff Salary (Split-Online): {employee.name} ({payroll.month})",
                        payment_method='UPI'
                    )
            else:
                CashBook.log_transaction(
                    date=date.today(),
                    transaction_type='Out',
                    amount=paid_amount,
                    source='Payroll',
                    reference_id=payroll.id,
                    description=f"Staff Salary: {employee.name} ({payroll.month}) via {payroll.payment_method}",
                    payment_method=payroll.payment_method or 'Cash'
                )

        db.session.commit()
        flash(f"Payroll created for {employee.name}. Paid: {paid_amount}, Pending: {pending_amount}", "success")
        return redirect(url_for('staff.index', view='payroll'))

    return render_template('staff/form.html', form=form, title="Release Employee Payroll")


@staff_bp.route('/payroll/delete/<int:payroll_id>', methods=['POST'])
@login_required
def payroll_delete(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)
    employee_id = payroll.employee_id
    
    # Remove from CashBook if salary was paid
    if payroll.paid_amount > 0:
        CashBook.remove_transaction(source='Payroll', reference_id=payroll.id)
        
    db.session.delete(payroll)
    db.session.flush()
    
    # Recalculate balances
    employee = Employee.query.get(employee_id)
    employee.recalculate_balances()
    
    db.session.commit()
    flash('Payroll sheet deleted successfully.', 'success')
    return redirect(url_for('staff.index', view='payroll'))


@staff_bp.route('/payroll/pay/<int:payroll_id>', methods=['GET', 'POST'])
@login_required
def payroll_pay(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)
    employee = Employee.query.get(payroll.employee_id)
    
    if payroll.pending_amount <= 0:
        flash("This payroll is already fully paid.", "warning")
        return redirect(url_for('staff.index', view='payroll'))
        
    form = StaffSalaryPaymentForm()
    
    # Prefill the amount with the remaining pending amount on GET
    if request.method == 'GET':
        form.amount.data = payroll.pending_amount
        
    if form.validate_on_submit():
        amount_to_pay = form.amount.data
        payment_date = form.payment_date.data
        payment_method = form.payment_method.data
        
        if payment_method == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - amount_to_pay) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the Payment Amount.", "danger")
                return render_template('staff/pay_payroll.html', form=form, payroll=payroll, employee=employee)

        # Validation: check that the payment amount does not exceed the remaining pending amount
        if amount_to_pay > payroll.pending_amount + 0.01:
            flash(f"Payment amount ({amount_to_pay}) cannot exceed outstanding pending salary ({payroll.pending_amount}).", "danger")
            return render_template('staff/pay_payroll.html', form=form, payroll=payroll, employee=employee)
            
        amount_to_pay = min(amount_to_pay, payroll.pending_amount)
        
        # Update payroll fields
        payroll.paid_amount += amount_to_pay
        payroll.pending_amount -= amount_to_pay
        
        if payroll.pending_amount <= 0.01:
            payroll.pending_amount = 0.0
            payroll.payment_status = 'Paid'
        else:
            payroll.payment_status = 'Partial'
            
        payroll.payment_date = payment_date
        payroll.payment_method = payment_method
        payroll.cash_amount = form.cash_amount.data if payment_method == 'Split' else 0.0
        payroll.online_amount = form.online_amount.data if payment_method == 'Split' else 0.0
        
        # Log transaction to CashBook
        if payment_method == 'Split':
            if payroll.cash_amount > 0:
                CashBook.log_transaction(
                    date=payment_date,
                    transaction_type='Out',
                    amount=payroll.cash_amount,
                    source='Payroll',
                    reference_id=payroll.id,
                    description=f"Staff Salary Payment (Split-Cash): {employee.name} ({payroll.month})",
                    payment_method='Cash'
                )
            if payroll.online_amount > 0:
                CashBook.log_transaction(
                    date=payment_date,
                    transaction_type='Out',
                    amount=payroll.online_amount,
                    source='Payroll',
                    reference_id=payroll.id,
                    description=f"Staff Salary Payment (Split-Online): {employee.name} ({payroll.month})",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=payment_date,
                transaction_type='Out',
                amount=amount_to_pay,
                source='Payroll',
                reference_id=payroll.id,
                description=f"Staff Salary Payment: {employee.name} ({payroll.month}) via {payment_method}",
                payment_method=payment_method
            )
        
        # Recalculate employee balances
        employee.recalculate_balances()
        db.session.commit()
        
        flash(f"Recorded payment of {amount_to_pay} to {employee.name}.", "success")
        return redirect(url_for('staff.index', view='payroll'))
        
    return render_template('staff/pay_payroll.html', form=form, payroll=payroll, employee=employee)
