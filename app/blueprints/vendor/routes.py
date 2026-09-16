from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.blueprints.vendor import vendor_bp
from app.blueprints.vendor.forms import VendorForm, VendorBillForm, VendorPaymentForm
from app.models import Vendor, VendorBill, VendorPayment, CashBook
from datetime import datetime, date

@vendor_bp.route('/')
@login_required
def index():
    view = request.args.get('view', 'vendors')
    search_query = request.args.get('search', '')
    
    if view == 'vendors':
        query = Vendor.query
        if search_query:
            query = query.filter(
                (Vendor.name.ilike(f'%{search_query}%')) | 
                (Vendor.contact_person.ilike(f'%{search_query}%'))
            )
        vendors = query.order_by(Vendor.name.asc()).all()
        return render_template('vendor/index.html', view=view, vendors=vendors, search_query=search_query)

    elif view == 'bills':
        query = VendorBill.query
        if search_query:
            query = query.join(Vendor).filter(
                (Vendor.name.ilike(f'%{search_query}%')) | 
                (VendorBill.bill_number.ilike(f'%{search_query}%'))
            )
        bills = query.order_by(VendorBill.date.desc(), VendorBill.id.desc()).all()
        return render_template('vendor/index.html', view=view, bills=bills, search_query=search_query)

    elif view == 'payments':
        query = VendorPayment.query
        if search_query:
            query = query.join(Vendor).filter(
                (Vendor.name.ilike(f'%{search_query}%')) | 
                (VendorPayment.description.ilike(f'%{search_query}%'))
            )
        payments = query.order_by(VendorPayment.date.desc(), VendorPayment.id.desc()).all()
        return render_template('vendor/index.html', view=view, payments=payments, search_query=search_query)

    elif view == 'ledgers':
        # Select vendor list for ledger selection
        vendors = Vendor.query.order_by(Vendor.name.asc()).all()
        vendor_id = request.args.get('vendor_id', type=int)
        
        selected_vendor = None
        display_entries = []
        tot_billed = 0.0
        tot_paid = 0.0
        
        if vendor_id:
            selected_vendor = Vendor.query.get(vendor_id)
            if selected_vendor:
                # Fetch all bills and payments for this vendor
                bills = VendorBill.query.filter_by(vendor_id=vendor_id).all()
                payments = VendorPayment.query.filter_by(vendor_id=vendor_id).all()
                
                def parse_date(d_val):
                    if not d_val:
                        return date.min
                    if isinstance(d_val, str):
                        try:
                            clean_str = d_val.split(' ')[0].split('T')[0]
                            return datetime.strptime(clean_str, '%Y-%m-%d').date()
                        except Exception:
                            return date.min
                    if isinstance(d_val, datetime):
                        return d_val.date()
                    if isinstance(d_val, date):
                        return d_val
                    return date.min

                ledger_entries = []
                # Combine into a chronological ledger
                for b in bills:
                    ledger_entries.append({
                        'date': parse_date(b.date),
                        'type': 'Purchase (Bill)',
                        'reference': b.bill_number or '-',
                        'description': b.description or 'Credit Purchase',
                        'increase': float(b.amount or 0.0),
                        'decrease': 0.0,
                        'sort_id': f"bill-{b.id}"
                    })
                for p in payments:
                    ledger_entries.append({
                        'date': parse_date(p.date),
                        'type': 'Payment',
                        'reference': p.payment_method or 'Cash',
                        'description': p.description or 'Cash/UPI Outflow',
                        'increase': 0.0,
                        'decrease': float(p.amount or 0.0),
                        'sort_id': f"pay-{p.id}"
                    })
                    
                # Sort chronologically by date
                ledger_entries.sort(key=lambda x: (x['date'], x['sort_id']))
                
                # Calculate running outstanding balance
                running = 0.0
                for entry in ledger_entries:
                    tot_billed += entry['increase']
                    tot_paid += entry['decrease']
                    running += (entry['increase'] - entry['decrease'])
                    entry['running_balance'] = running

                display_entries = list(reversed(ledger_entries))

        return render_template(
            'vendor/ledger.html',
            view=view,
            vendors=vendors,
            selected_vendor=selected_vendor,
            ledger_entries=display_entries,
            tot_billed=tot_billed,
            tot_paid=tot_paid,
            datetime_now=datetime.now()
        )

    return redirect(url_for('vendor.index'))


@vendor_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = VendorForm()
    if form.validate_on_submit():
        vendor = Vendor(
            name=form.name.data,
            contact_person=form.contact_person.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data
        )
        db.session.add(vendor)
        db.session.commit()
        flash(f'Vendor "{vendor.name}" created successfully!', 'success')
        return redirect(url_for('vendor.index', view='vendors'))
    return render_template('vendor/form.html', form=form, title="Create Vendor Profile")


@vendor_bp.route('/edit/<int:vendor_id>', methods=['GET', 'POST'])
@login_required
def edit(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    form = VendorForm(obj=vendor)
    if form.validate_on_submit():
        vendor.name = form.name.data
        vendor.contact_person = form.contact_person.data
        vendor.phone = form.phone.data
        vendor.email = form.email.data
        vendor.address = form.address.data
        db.session.commit()
        flash(f'Vendor profile for "{vendor.name}" updated.', 'success')
        return redirect(url_for('vendor.index', view='vendors'))
    return render_template('vendor/form.html', form=form, title="Edit Vendor Profile", vendor=vendor)


@vendor_bp.route('/delete/<int:vendor_id>', methods=['POST'])
@login_required
def delete(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    name = vendor.name
    
    # Cascade deletes all bills and payments. 
    # But wait, deleting payments removes cashbook outflows, so we must clean CashBook entries!
    vendor_payments = VendorPayment.query.filter_by(vendor_id=vendor_id).all()
    for p in vendor_payments:
        CashBook.remove_transaction(source='VendorPayment', reference_id=p.id)

    db.session.delete(vendor)
    db.session.commit()
    flash(f'Vendor "{name}" and all related bills/payments deleted successfully.', 'success')
    return redirect(url_for('vendor.index', view='vendors'))


@vendor_bp.route('/bill/add', methods=['GET', 'POST'])
@login_required
def bill_add():
    form = VendorBillForm()
    # Populate vendor choices
    form.vendor_id.choices = [(v.id, v.name) for v in Vendor.query.order_by(Vendor.name.asc()).all()]
    
    # Pre-select if vendor_id is in query params
    vendor_id = request.args.get('vendor_id', type=int)
    if vendor_id and request.method == 'GET':
        form.vendor_id.data = vendor_id

    if form.validate_on_submit():
        bill = VendorBill(
            vendor_id=form.vendor_id.data,
            bill_number=form.bill_number.data,
            date=form.date.data,
            amount=form.amount.data,
            description=form.description.data
        )
        db.session.add(bill)
        db.session.flush()

        # Update vendor outstanding
        vendor = Vendor.query.get(bill.vendor_id)
        vendor.recalculate_outstanding()

        db.session.commit()
        flash(f'Bill {bill.bill_number} for {bill.amount} recorded.', 'success')
        return redirect(url_for('vendor.index', view='bills'))

    return render_template('vendor/form.html', form=form, title="Record Vendor Bill (Credit Purchase)")


@vendor_bp.route('/bill/delete/<int:bill_id>', methods=['POST'])
@login_required
def bill_delete(bill_id):
    bill = VendorBill.query.get_or_404(bill_id)
    vendor_id = bill.vendor_id
    db.session.delete(bill)
    db.session.flush()
    
    # Recalculate outstanding
    vendor = Vendor.query.get(vendor_id)
    vendor.recalculate_outstanding()
    
    db.session.commit()
    flash('Invoice deleted successfully.', 'success')
    return redirect(url_for('vendor.index', view='bills'))


@vendor_bp.route('/payment/add', methods=['GET', 'POST'])
@login_required
def payment_add():
    form = VendorPaymentForm()
    form.vendor_id.choices = [(v.id, v.name) for v in Vendor.query.order_by(Vendor.name.asc()).all()]
    
    vendor_id = request.args.get('vendor_id', type=int)
    if vendor_id and request.method == 'GET':
        form.vendor_id.data = vendor_id

    if form.validate_on_submit():
        if form.payment_method.data == 'Split':
            cash_val = form.cash_amount.data or 0.0
            online_val = form.online_amount.data or 0.0
            if abs((cash_val + online_val) - form.amount.data) > 0.01:
                flash("Error: The sum of Cash Portion and Online Portion must equal the total Amount.", "danger")
                return render_template('vendor/form.html', form=form, title="Record Vendor Payment")

        payment = VendorPayment(
            vendor_id=form.vendor_id.data,
            date=form.date.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            cash_amount=form.cash_amount.data if form.payment_method.data == 'Split' else 0.0,
            online_amount=form.online_amount.data if form.payment_method.data == 'Split' else 0.0,
            description=form.description.data
        )
        db.session.add(payment)
        db.session.flush()

        # Recalculate Vendor Outstanding
        vendor = Vendor.query.get(payment.vendor_id)
        vendor.recalculate_outstanding()

        # Automation Rule: Vendor Payment decreases cash balance (log cashbook outflow)
        if payment.payment_method == 'Split':
            if payment.cash_amount > 0:
                CashBook.log_transaction(
                    date=payment.date,
                    transaction_type='Out',
                    amount=payment.cash_amount,
                    source='VendorPayment',
                    reference_id=payment.id,
                    description=f"Vendor Payment (Split-Cash): {vendor.name} - {payment.description or ''}",
                    payment_method='Cash'
                )
            if payment.online_amount > 0:
                CashBook.log_transaction(
                    date=payment.date,
                    transaction_type='Out',
                    amount=payment.online_amount,
                    source='VendorPayment',
                    reference_id=payment.id,
                    description=f"Vendor Payment (Split-Online): {vendor.name} - {payment.description or ''}",
                    payment_method='UPI'
                )
        else:
            CashBook.log_transaction(
                date=payment.date,
                transaction_type='Out',
                amount=payment.amount,
                source='VendorPayment',
                reference_id=payment.id,
                description=f"Vendor Payment: {vendor.name} ({payment.payment_method}) - {payment.description or ''}",
                payment_method=payment.payment_method
            )

        db.session.commit()
        flash(f'Payment of {payment.amount} to {vendor.name} recorded.', 'success')
        return redirect(url_for('vendor.index', view='payments'))

    return render_template('vendor/form.html', form=form, title="Record Vendor Payment")


@vendor_bp.route('/payment/delete/<int:payment_id>', methods=['POST'])
@login_required
def payment_delete(payment_id):
    payment = VendorPayment.query.get_or_404(payment_id)
    vendor_id = payment.vendor_id
    
    # Remove from CashBook and database
    CashBook.remove_transaction(source='VendorPayment', reference_id=payment.id)
    db.session.delete(payment)
    db.session.flush()
    
    # Recalculate Vendor Outstanding
    vendor = Vendor.query.get(vendor_id)
    vendor.recalculate_outstanding()
    
    db.session.commit()
    flash('Payment record deleted successfully.', 'success')
    return redirect(url_for('vendor.index', view='payments'))
