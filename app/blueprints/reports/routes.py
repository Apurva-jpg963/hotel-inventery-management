from flask import render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required
from app import db
from app.blueprints.reports import reports_bp
from app.models import (
    Income, Expense, Vendor, VendorBill, VendorPayment,
    Employee, Attendance, EmployeeAdvance, Payroll,
    Savings, Loan, LoanRepayment, CreditAccount,
    CreditTransaction, MDSirAccount, CashBook
)
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
import io

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def clean_sheet_title(title):
    if not title:
        return "Sheet"
    for char in ['\\', '/', '?', '*', '[', ']', ':']:
        title = title.replace(char, '')
    return title[:30].strip()

def apply_openpyxl_styles(wb):
    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )
    
    totals_border = Border(
        top=Side(style='thin', color='000000'),
        bottom=Side(style='double', color='000000')
    )
    
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    
    # Fill colors for specific columns
    fill_green = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    font_green = Font(name="Calibri", size=11, bold=True, color="276A3C")
    
    fill_red = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    font_red = Font(name="Calibri", size=11, bold=True, color="C00000")
    
    fill_blue = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    font_blue = Font(name="Calibri", size=11, bold=True, color="1F4E78")
    
    fill_yellow = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    fill_orange = PatternFill(start_color="FFE6CC", end_color="FFE6CC", fill_type="solid")
    font_orange = Font(name="Calibri", size=11, bold=True, color="B25900")
    fill_purple = PatternFill(start_color="E1D5E7", end_color="E1D5E7", fill_type="solid")

    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        ws.freeze_panes = 'A2'
        
        col_styles = {}
        for col_num in range(1, ws.max_column + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 28
            
            header_text = str(cell.value or "").strip()
            
            if "Deposit" in header_text:
                col_styles[col_num] = ("currency", fill_green, font_green)
            elif "Withdrawal" in header_text:
                col_styles[col_num] = ("currency", fill_red, font_red)
            elif "Running Balance" in header_text:
                col_styles[col_num] = ("currency", fill_blue, font_blue)
            elif "Gross Salary" in header_text:
                col_styles[col_num] = ("currency", fill_blue, None)
            elif "Advance" in header_text:
                col_styles[col_num] = ("currency", fill_yellow, None)
            elif "Deduction" in header_text:
                col_styles[col_num] = ("currency", fill_red, None)
            elif "Net Payable" in header_text:
                col_styles[col_num] = ("currency", fill_green, None)
            elif "Amount Paid" in header_text or "Total Paid" in header_text or "Paid Amount" in header_text:
                col_styles[col_num] = ("currency", fill_orange, None)
            elif "Remaining" in header_text or "Pending" in header_text or "Outstanding" in header_text:
                col_styles[col_num] = ("currency", fill_purple, None)
            elif "(₹)" in header_text or "Amount" in header_text or "Rate" in header_text or "Margin" in header_text or "Profit" in header_text or "Cost" in header_text:
                col_styles[col_num] = ("currency", None, None)
            elif "Status" in header_text:
                col_styles[col_num] = ("status", None, None)
            else:
                col_styles[col_num] = ("text", None, None)

        for row_num in range(2, ws.max_row + 1):
            first_cell = ws.cell(row=row_num, column=1)
            first_val = str(first_cell.value or "").strip().upper()
            is_totals_row = ("TOTAL" in first_val or "GRAND TOTAL" in first_val or "NET CHANGE" in first_val)
            
            ws.row_dimensions[row_num].height = 20
            
            for col_num in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.border = thin_border
                
                kind, fill_override, font_override = col_styles.get(col_num, ("text", None, None))
                
                if is_totals_row:
                    cell.font = Font(name="Calibri", size=11, bold=True)
                    cell.border = totals_border
                    if fill_override:
                        cell.fill = fill_override
                else:
                    if fill_override:
                        cell.fill = fill_override
                    elif row_num % 2 == 1:
                        cell.fill = alt_fill
                        
                    if font_override:
                        cell.font = font_override

                if kind == "currency":
                    cell.number_format = '"₹"#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif kind == "status":
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    val_str = str(cell.value or "").strip()
                    if val_str == "Paid":
                        cell.fill = fill_green
                        cell.font = font_green
                    elif val_str in ["Partially Paid", "Partial"]:
                        cell.fill = fill_orange
                        cell.font = font_orange
                    elif val_str == "Pending":
                        cell.fill = fill_red
                        cell.font = font_red
                else:
                    if col_num == 1:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 5, 14)

@reports_bp.route('/')
@login_required
def index():
    view = request.args.get('view', 'reports')
    period = request.args.get('period', 'monthly')  # daily, weekly, monthly, quarterly, yearly
    
    # Selected date anchor (defaults to today)
    date_str = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))
    try:
        anchor_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        anchor_date = datetime.today().date()

    # Determine start and end date of reporting period
    if period == 'daily':
        start_date = anchor_date
        end_date = anchor_date
    elif period == 'weekly':
        # Start of week (Monday) to Sunday
        start_date = anchor_date - timedelta(days=anchor_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'quarterly':
        # Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec
        quarter = (anchor_date.month - 1) // 3 + 1
        start_date = datetime(anchor_date.year, 3 * quarter - 2, 1).date()
        if quarter == 4:
            end_date = date(anchor_date.year, 12, 31)
        else:
            end_date = (datetime(anchor_date.year, 3 * quarter + 1, 1) - timedelta(days=1)).date()
    elif period == 'yearly':
        start_date = datetime(anchor_date.year, 1, 1).date()
        end_date = datetime(anchor_date.year, 12, 31).date()
    else: # monthly (default)
        start_date = datetime(anchor_date.year, anchor_date.month, 1).date()
        last_day = calendar_days = 31 # fallback
        try:
            import calendar
            last_day = calendar.monthrange(anchor_date.year, anchor_date.month)[1]
        except:
            pass
        end_date = datetime(anchor_date.year, anchor_date.month, last_day).date()

    # 1. Fetch data in the date range
    incomes = Income.query.filter(Income.date >= start_date, Income.date <= end_date).all()
    expenses = Expense.query.filter(Expense.date >= start_date, Expense.date <= end_date).all()
    vendor_payments = VendorPayment.query.filter(VendorPayment.date >= start_date, VendorPayment.date <= end_date).all()
    payroll_payments = Payroll.query.filter(Payroll.payment_date >= start_date, Payroll.payment_date <= end_date).all()
    employee_advances = EmployeeAdvance.query.filter(EmployeeAdvance.date >= start_date, EmployeeAdvance.date <= end_date).all()
    savings_txs = Savings.query.filter(Savings.date >= start_date, Savings.date <= end_date).all()
    loan_repays = LoanRepayment.query.filter(LoanRepayment.date >= start_date, LoanRepayment.date <= end_date).all()
    credit_txs = CreditTransaction.query.filter(CreditTransaction.date >= start_date, CreditTransaction.date <= end_date).all()
    md_txs = MDSirAccount.query.filter(MDSirAccount.date >= start_date, MDSirAccount.date <= end_date).all()
    vendor_bills = VendorBill.query.filter(VendorBill.date >= start_date, VendorBill.date <= end_date).all()
    loans_given = Loan.query.filter(Loan.date_taken >= start_date, Loan.date_taken <= end_date).all()

    # Summary calculations
    bill_pending = db.session.query(db.func.sum(CreditAccount.receivable_balance)).scalar() or 0.0
    bill_received = db.session.query(db.func.sum(CreditAccount.payable_balance)).scalar() or 0.0

    total_income = (
        sum(i.amount for i in incomes) +
        sum(m.amount for m in md_txs if m.transaction_type == 'Deposit') +
        sum(s.amount for s in savings_txs if s.transaction_type == 'Withdrawal') +
        sum(c.amount for c in credit_txs if c.transaction_type == 'Received') +
        sum(-c.amount for c in credit_txs if c.transaction_type == 'Given' and c.amount < 0) +
        bill_received
    )
    total_expense = (
        sum(e.amount for e in expenses) +
        sum(vp.amount for vp in vendor_payments) +
        sum(p.paid_amount for p in payroll_payments) +
        sum(adv.amount for adv in employee_advances) +
        sum(s.amount for s in savings_txs if s.transaction_type == 'Deposit') +
        sum(c.amount for c in credit_txs if c.transaction_type == 'Paid') +
        sum(-c.amount for c in credit_txs if c.transaction_type == 'Taken' and c.amount < 0) +
        sum(m.amount for m in md_txs if m.transaction_type == 'Withdraw') +
        sum(lr.principal_paid + lr.interest_paid for lr in loan_repays) +
        bill_pending
    )
    net_margin = total_income - total_expense

    # Outbound Cash Breakdown
    vendor_paid = sum(vp.amount for vp in vendor_payments)
    hotel_exp = sum(e.amount for e in expenses if e.type == 'Hotel') + vendor_paid
    other_exp = sum(e.amount for e in expenses if e.type == 'Other')
    dev_exp = sum(e.amount for e in expenses if e.type == 'Development')
    payroll_paid = sum(p.paid_amount for p in payroll_payments)

    # Balance Sheet snapshot totals
    cash_bal = CashBook.get_current_balance()
    savings_bal = Savings.get_balance()
    total_bank_installments = db.session.query(db.func.sum(LoanRepayment.principal_paid + LoanRepayment.interest_paid)).scalar() or 0.0

    if view == 'exports':
        today_val = datetime.today().date()
        default_start = date(today_val.year, today_val.month, 1).strftime('%Y-%m-%d')
        default_end = today_val.strftime('%Y-%m-%d')
        return render_template(
            'reports/exports.html',
            view=view,
            default_start=default_start,
            default_end=default_end
        )

    return render_template(
        'reports/index.html',
        view=view,
        period=period,
        anchor_date=anchor_date,
        start_date=start_date,
        end_date=end_date,
        total_income=total_income,
        total_expense=total_expense,
        net_margin=net_margin,
        hotel_exp=hotel_exp,
        other_exp=other_exp,
        dev_exp=dev_exp,
        payroll_paid=payroll_paid,
        vendor_paid=vendor_paid,
        cash_bal=cash_bal,
        savings_bal=savings_bal,
        total_bank_installments=total_bank_installments,
        bill_pending=bill_pending,
        bill_received=bill_received
    )


def format_date(d):
    if d is None:
        return ""
    if isinstance(d, (datetime, date)):
        return d.strftime('%Y-%m-%d')
    return str(d)

def resolve_cash_online(payment_method, amount, cash_amount, online_amount):
    method = (payment_method or "").strip().lower()
    if method == 'split':
        return float(cash_amount or 0.0), float(online_amount or 0.0)
    elif 'cash' in method:
        return float(amount or 0.0), 0.0
    elif any(x in method for x in ['upi', 'card', 'bank', 'cheque', 'online', 'net', 'transfer', 'gpay', 'phonepe', 'paytm']):
        return 0.0, float(amount or 0.0)
    else:
        if (cash_amount or 0.0) > 0 or (online_amount or 0.0) > 0:
            return float(cash_amount or 0.0), float(online_amount or 0.0)
        if not method:
            return 0.0, 0.0
        return 0.0, float(amount or 0.0)


@reports_bp.route('/export')
@login_required
def export():
    export_type = request.args.get('type', 'complete')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    if export_type == 'complete':
        filename = 'Complete_ERP_Financial_Book.xlsx'
        if start_date and end_date:
            filename = f"Complete_ERP_Financial_Book_{start_date_str}_to_{end_date_str}.xlsx"
        
        # 1. Executive Summary Sheet
        rev_q = db.session.query(db.func.sum(Income.amount))
        exp_q = db.session.query(db.func.sum(Expense.amount))
        vp_q = db.session.query(db.func.sum(VendorPayment.amount))
        payroll_q = db.session.query(db.func.sum(Payroll.paid_amount))
        adv_q = db.session.query(db.func.sum(EmployeeAdvance.amount))
        
        if start_date:
            rev_q = rev_q.filter(Income.date >= start_date)
            exp_q = exp_q.filter(Expense.date >= start_date)
            vp_q = vp_q.filter(VendorPayment.date >= start_date)
            payroll_q = payroll_q.filter(Payroll.payment_date >= start_date)
            adv_q = adv_q.filter(EmployeeAdvance.date >= start_date)
        if end_date:
            rev_q = rev_q.filter(Income.date <= end_date)
            exp_q = exp_q.filter(Expense.date <= end_date)
            vp_q = vp_q.filter(VendorPayment.date <= end_date)
            payroll_q = payroll_q.filter(Payroll.payment_date <= end_date)
            adv_q = adv_q.filter(EmployeeAdvance.date <= end_date)

        total_rev = rev_q.scalar() or 0.0
        total_exp = exp_q.scalar() or 0.0
        vendor_payments_total = vp_q.scalar() or 0.0
        staff_payroll_total = payroll_q.scalar() or 0.0
        staff_advances_total = adv_q.scalar() or 0.0
        
        grand_total_expenses = total_exp + vendor_payments_total + staff_payroll_total + staff_advances_total
        net_profit = total_rev - grand_total_expenses
        
        cash_balance = CashBook.get_current_balance()
        savings_balance = Savings.get_balance()
        
        receivables_total = db.session.query(db.func.sum(CreditAccount.receivable_balance)).scalar() or 0.0
        payables_total = db.session.query(db.func.sum(CreditAccount.payable_balance)).scalar() or 0.0
        
        period_str = f"{format_date(start_date)} to {format_date(end_date)}" if (start_date or end_date) else "All Time"
        exec_data = [
            {'Key Financial Indicator': 'Report Compiled Period', 'Value': period_str, 'Notes': 'Date range for compiled details'},
            {'Key Financial Indicator': 'Total Revenue / Income (₹)', 'Value': total_rev, 'Notes': 'Direct revenue logged'},
            {'Key Financial Indicator': 'Direct Operating Expenses (₹)', 'Value': total_exp, 'Notes': 'Hotel, Other, Development'},
            {'Key Financial Indicator': 'Vendor Payments Released (₹)', 'Value': vendor_payments_total, 'Notes': 'Suppliers payouts'},
            {'Key Financial Indicator': 'Staff Salaries Paid (₹)', 'Value': staff_payroll_total, 'Notes': 'Payroll payouts'},
            {'Key Financial Indicator': 'Staff Advances Issued (₹)', 'Value': staff_advances_total, 'Notes': 'HR advances outstanding'},
            {'Key Financial Indicator': 'TOTAL OUTFLOWS (EXPENSES) (₹)', 'Value': grand_total_expenses, 'Notes': 'Sum of direct + HR + vendor costs'},
            {'Key Financial Indicator': 'NET PROFIT / MARGIN (₹)', 'Value': net_profit, 'Notes': 'Total Revenue - Total Outflows'},
            {'Key Financial Indicator': 'Central Cash Book Balance (₹)', 'Value': cash_balance, 'Notes': 'Liquid cash on hand'},
            {'Key Financial Indicator': 'Savings Account Balance (₹)', 'Value': savings_balance, 'Notes': 'Bank deposits balance'},
            {'Key Financial Indicator': 'Total Outstanding Receivables (Lena) (₹)', 'Value': receivables_total, 'Notes': 'Credit accounts money owed to us'},
            {'Key Financial Indicator': 'Total Outstanding Payables (Dena) (₹)', 'Value': payables_total, 'Notes': 'Credit accounts money we owe'}
        ]
        pd.DataFrame(exec_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # 2. Finance Deposit & Withdrawal Ledger Sheet
        cb_query = CashBook.query
        if start_date:
            cb_query = cb_query.filter(CashBook.date >= start_date)
        if end_date:
            cb_query = cb_query.filter(CashBook.date <= end_date)
        cb_entries = cb_query.order_by(CashBook.date.asc(), CashBook.id.asc()).all()
        
        running_bal = 0.0
        total_dep = 0.0
        total_with = 0.0
        cb_rows = []
        for e in cb_entries:
            is_dep = e.transaction_type in ['In', 'Deposit']
            dep = e.deposit_amount if e.deposit_amount > 0 else (e.amount if is_dep else 0.0)
            wit = e.withdrawal_amount if e.withdrawal_amount > 0 else (e.amount if not is_dep else 0.0)
            running_bal += (dep - wit)
            total_dep += dep
            total_with += wit
            
            cat = e.category
            if not cat:
                if e.source == 'Income':
                    cat = 'Cash Collection'
                elif e.source == 'Expense':
                    cat = 'Miscellaneous'
                elif e.source == 'Payroll':
                    cat = 'Staff Salary'
                elif e.source == 'VendorPayment':
                    cat = 'Vendor Payment'
                elif is_dep:
                    cat = 'Other Income'
                else:
                    cat = 'Miscellaneous'

            cb_rows.append({
                'Date': format_date(e.date),
                'Description': e.description or f"{e.source} entry",
                'Category': cat,
                'Payment Method': e.payment_method or 'Cash',
                'Deposit (₹)': dep,
                'Withdrawal (₹)': wit,
                'Running Balance (₹)': running_bal,
                'Remarks': e.remarks or ''
            })
            
        if cb_rows:
            cb_rows.append({
                'Date': 'TOTALS',
                'Description': f"Net Change: {total_dep - total_with}",
                'Category': '',
                'Payment Method': '',
                'Deposit (₹)': total_dep,
                'Withdrawal (₹)': total_with,
                'Running Balance (₹)': running_bal,
                'Remarks': ''
            })
            df_cb = pd.DataFrame(cb_rows)
        else:
            df_cb = pd.DataFrame(columns=[
                'Date', 'Description', 'Category', 'Payment Method',
                'Deposit (₹)', 'Withdrawal (₹)', 'Running Balance (₹)', 'Remarks'
            ])
        df_cb.to_excel(writer, sheet_name='Finance Ledger', index=False)

        # 3. All Income Logs
        inc_query = Income.query
        if start_date:
            inc_query = inc_query.filter(Income.date >= start_date)
        if end_date:
            inc_query = inc_query.filter(Income.date <= end_date)
        inc_entries = inc_query.order_by(Income.date.asc()).all()
        df_all_inc = pd.DataFrame([{
            'Date': format_date(e.date),
            'Category': e.category,
            'Total Amount (₹)': e.amount,
            'Payment Method': e.payment_method,
            'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
            'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
            'Description / Remarks': e.description
        } for e in inc_entries])
        if not df_all_inc.empty:
            total_row = pd.DataFrame([{
                'Date': 'TOTAL',
                'Category': 'All Categories',
                'Total Amount (₹)': df_all_inc['Total Amount (₹)'].sum(),
                'Payment Method': '',
                'Cash Amount (₹)': df_all_inc['Cash Amount (₹)'].sum(),
                'Online Amount (₹)': df_all_inc['Online Amount (₹)'].sum(),
                'Description / Remarks': 'Total Direct Income'
            }])
            df_all_inc = pd.concat([df_all_inc, total_row], ignore_index=True)
        df_all_inc.to_excel(writer, sheet_name='All Income Logs', index=False)

        # 4. Revenue Category sheets (separate room revenue etc datewise + total)
        categories = sorted(list(set(e.category for e in inc_entries))) if inc_entries else []
        for cat in categories:
            cat_entries = [e for e in inc_entries if e.category == cat]
            df_cat = pd.DataFrame([{
                'Date': format_date(e.date),
                'Category': e.category,
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Description / Remarks': e.description
            } for e in cat_entries])
            if not df_cat.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Category': cat,
                    'Total Amount (₹)': df_cat['Total Amount (₹)'].sum(),
                    'Payment Method': '',
                    'Cash Amount (₹)': df_cat['Cash Amount (₹)'].sum(),
                    'Online Amount (₹)': df_cat['Online Amount (₹)'].sum(),
                    'Description / Remarks': f"Total Revenue for {cat}"
                }])
                df_cat = pd.concat([df_cat, total_row], ignore_index=True)
            sheet_title = clean_sheet_title(f"Rev - {cat}")
            df_cat.to_excel(writer, sheet_name=sheet_title, index=False)

        # 5. All Expense Logs
        exp_query = Expense.query
        if start_date:
            exp_query = exp_query.filter(Expense.date >= start_date)
        if end_date:
            exp_query = exp_query.filter(Expense.date <= end_date)
        exp_entries = exp_query.order_by(Expense.date.asc()).all()
        df_all_exp = pd.DataFrame([{
            'Date': format_date(e.date),
            'Type (Scope)': e.type,
            'Category': e.category,
            'Total Amount (₹)': e.amount,
            'Payment Method': e.payment_method,
            'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
            'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
            'Description / Remarks': e.description
        } for e in exp_entries])
        if not df_all_exp.empty:
            total_row = pd.DataFrame([{
                'Date': 'TOTAL',
                'Type (Scope)': 'All Scopes',
                'Category': '',
                'Total Amount (₹)': df_all_exp['Total Amount (₹)'].sum(),
                'Payment Method': '',
                'Cash Amount (₹)': df_all_exp['Cash Amount (₹)'].sum(),
                'Online Amount (₹)': df_all_exp['Online Amount (₹)'].sum(),
                'Description / Remarks': 'Total General Expenses'
            }])
            df_all_exp = pd.concat([df_all_exp, total_row], ignore_index=True)
        df_all_exp.to_excel(writer, sheet_name='All Expense Logs', index=False)

        # 6. Expense Category/Scope sheets
        scopes = sorted(list(set(e.type for e in exp_entries))) if exp_entries else []
        for scope in scopes:
            scope_entries = [e for e in exp_entries if e.type == scope]
            df_scope = pd.DataFrame([{
                'Date': format_date(e.date),
                'Scope': e.type,
                'Category': e.category,
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Description / Remarks': e.description
            } for e in scope_entries])
            if not df_scope.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Scope': scope,
                    'Category': '',
                    'Total Amount (₹)': df_scope['Total Amount (₹)'].sum(),
                    'Payment Method': '',
                    'Cash Amount (₹)': df_scope['Cash Amount (₹)'].sum(),
                    'Online Amount (₹)': df_scope['Online Amount (₹)'].sum(),
                    'Description / Remarks': f"Total Expense for {scope}"
                }])
                df_scope = pd.concat([df_scope, total_row], ignore_index=True)
            sheet_title = clean_sheet_title(f"Exp - {scope}")
            df_scope.to_excel(writer, sheet_name=sheet_title, index=False)

        # 7. Vendor Payments detailed sheet
        vp_query = VendorPayment.query
        if start_date:
            vp_query = vp_query.filter(VendorPayment.date >= start_date)
        if end_date:
            vp_query = vp_query.filter(VendorPayment.date <= end_date)
        vp_entries = vp_query.order_by(VendorPayment.date.asc()).all()
        if vp_entries:
            df_vp = pd.DataFrame([{
                'Date': format_date(e.date),
                'Vendor': e.vendor.name if e.vendor else 'Unknown',
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Remarks': e.description
            } for e in vp_entries])
            if not df_vp.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Vendor': '',
                    'Total Amount (₹)': df_vp['Total Amount (₹)'].sum(),
                    'Payment Method': '',
                    'Cash Paid (₹)': df_vp['Cash Paid (₹)'].sum(),
                    'Online Paid (₹)': df_vp['Online Paid (₹)'].sum(),
                    'Remarks': 'Total Vendor Payments'
                }])
                df_vp = pd.concat([df_vp, total_row], ignore_index=True)
            df_vp.to_excel(writer, sheet_name='Vendor Payments Logs', index=False)

        # 8. Staff Salaries detailed sheet
        payroll_query = Payroll.query
        if start_date:
            payroll_query = payroll_query.filter(Payroll.payment_date >= start_date)
        if end_date:
            payroll_query = payroll_query.filter(Payroll.payment_date <= end_date)
        payroll_entries = payroll_query.order_by(Payroll.payment_date.asc()).all()
        paid_payrolls = [p for p in payroll_entries if p.paid_amount > 0]
        if paid_payrolls:
            df_sal = pd.DataFrame([{
                'Date': format_date(p.payment_date),
                'Employee': p.employee.name if p.employee else 'Unknown',
                'Month': p.month,
                'Gross Salary': p.calculated_salary,
                'Deductions': p.deductions + p.advance_adjusted,
                'Net Payable': p.net_payable,
                'Paid Amount (₹)': p.paid_amount,
                'Cash Paid (₹)': resolve_cash_online(p.payment_method, p.paid_amount, p.cash_amount, p.online_amount)[0],
                'Online Paid (₹)': resolve_cash_online(p.payment_method, p.paid_amount, p.cash_amount, p.online_amount)[1]
            } for p in paid_payrolls])
            if not df_sal.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Employee': '',
                    'Month': '',
                    'Gross Salary': df_sal['Gross Salary'].sum(),
                    'Deductions': df_sal['Deductions'].sum(),
                    'Net Payable': df_sal['Net Payable'].sum(),
                    'Paid Amount (₹)': df_sal['Paid Amount (₹)'].sum(),
                    'Cash Paid (₹)': df_sal['Cash Paid (₹)'].sum(),
                    'Online Paid (₹)': df_sal['Online Paid (₹)'].sum()
                }])
                df_sal = pd.concat([df_sal, total_row], ignore_index=True)
            df_sal.to_excel(writer, sheet_name='Staff Salaries Logs', index=False)

        # 9. Staff Advances detailed sheet
        adv_query = EmployeeAdvance.query
        if start_date:
            adv_query = adv_query.filter(EmployeeAdvance.date >= start_date)
        if end_date:
            adv_query = adv_query.filter(EmployeeAdvance.date <= end_date)
        adv_entries = adv_query.order_by(EmployeeAdvance.date.asc()).all()
        if adv_entries:
            df_adv = pd.DataFrame([{
                'Date': format_date(e.date),
                'Employee': e.employee.name if e.employee else 'Unknown',
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Remarks': e.description
            } for e in adv_entries])
            if not df_adv.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Employee': '',
                    'Total Amount (₹)': df_adv['Total Amount (₹)'].sum(),
                    'Payment Method': '',
                    'Cash Paid (₹)': df_adv['Cash Paid (₹)'].sum(),
                    'Online Paid (₹)': df_adv['Online Paid (₹)'].sum(),
                    'Remarks': 'Total Salary Advances Issued'
                }])
                df_adv = pd.concat([df_adv, total_row], ignore_index=True)
            df_adv.to_excel(writer, sheet_name='Staff Advances Logs', index=False)

        # 10. Savings logs
        sav_query = Savings.query
        if start_date:
            sav_query = sav_query.filter(Savings.date >= start_date)
        if end_date:
            sav_query = sav_query.filter(Savings.date <= end_date)
        sav_entries = sav_query.order_by(Savings.date.asc()).all()
        if sav_entries:
            df_sav = pd.DataFrame([{
                'Date': format_date(e.date),
                'Type': e.transaction_type,
                'Bank Name': e.bank_name,
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Portion (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Portion (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Description': e.description
            } for e in sav_entries])
            if not df_sav.empty:
                total_deposits = df_sav[df_sav['Type'] == 'Deposit']['Total Amount (₹)'].sum()
                total_withdrawals = df_sav[df_sav['Type'] == 'Withdrawal']['Total Amount (₹)'].sum()
                total_row = pd.DataFrame([{
                    'Date': 'TOTALS',
                    'Type': f"Deposits: {total_deposits} | Withdrawals: {total_withdrawals}",
                    'Bank Name': 'Net change:',
                    'Total Amount (₹)': total_withdrawals - total_deposits,
                    'Payment Method': '',
                    'Cash Portion (₹)': df_sav['Cash Portion (₹)'].sum(),
                    'Online Portion (₹)': df_sav['Online Portion (₹)'].sum(),
                    'Description': ''
                }])
                df_sav = pd.concat([df_sav, total_row], ignore_index=True)
            df_sav.to_excel(writer, sheet_name='Bank Savings', index=False)

        # 11. Loan Installments logs
        lr_query = LoanRepayment.query
        if start_date:
            lr_query = lr_query.filter(LoanRepayment.date >= start_date)
        if end_date:
            lr_query = lr_query.filter(LoanRepayment.date <= end_date)
        loan_repays = lr_query.order_by(LoanRepayment.date.asc()).all()
        if loan_repays:
            df_lr = pd.DataFrame([{
                'Bank Name': e.loan.lender_name if e.loan else 'SBI Bank',
                'Date Paid': format_date(e.date),
                'Amount Paid': e.principal_paid + e.interest_paid,
                'Payment Method': e.payment_method,
                'Cash Paid (₹)': resolve_cash_online(e.payment_method, e.principal_paid + e.interest_paid, e.cash_amount, e.online_amount)[0],
                'Online Paid (₹)': resolve_cash_online(e.payment_method, e.principal_paid + e.interest_paid, e.cash_amount, e.online_amount)[1],
                'Remarks': e.description
            } for e in loan_repays])
            if not df_lr.empty:
                total_row = pd.DataFrame([{
                    'Bank Name': 'TOTAL',
                    'Date Paid': '',
                    'Amount Paid': df_lr['Amount Paid'].sum(),
                    'Payment Method': '',
                    'Cash Paid (₹)': df_lr['Cash Paid (₹)'].sum(),
                    'Online Paid (₹)': df_lr['Online Paid (₹)'].sum(),
                    'Remarks': 'Total Installments Paid'
                }])
                df_lr = pd.concat([df_lr, total_row], ignore_index=True)
            df_lr.to_excel(writer, sheet_name='Loan Installments', index=False)

        # 12. MD Sir Account logs (6 Columns: Date, Deposit, Withdrawal, Payment Method, Balance, Remark)
        md_query = MDSirAccount.query
        if start_date:
            md_query = md_query.filter(MDSirAccount.date >= start_date)
        if end_date:
            md_query = md_query.filter(MDSirAccount.date <= end_date)
        md_entries = md_query.order_by(MDSirAccount.date.asc(), MDSirAccount.id.asc()).all()
        
        md_rows = []
        running_bal = 0.0
        tot_dep = 0.0
        tot_wit = 0.0
        
        for e in md_entries:
            is_dep = e.transaction_type in ['Deposit', 'In', 'Capital Deposit']
            dep = e.amount if is_dep else 0.0
            wit = e.amount if not is_dep else 0.0
            running_bal += (dep - wit)
            tot_dep += dep
            tot_wit += wit
            
            md_rows.append({
                'Date': format_date(e.date),
                'Deposit': dep if dep > 0 else "",
                'Withdrawal': wit if wit > 0 else "",
                'Payment Method': e.payment_method or 'Cash',
                'Balance': running_bal,
                'Remark': e.description or ''
            })
            
        if md_rows:
            md_rows.append({
                'Date': 'TOTAL',
                'Deposit': tot_dep,
                'Withdrawal': tot_wit,
                'Payment Method': '',
                'Balance': tot_dep - tot_wit,
                'Remark': ''
            })
            df_md = pd.DataFrame(md_rows)
        else:
            df_md = pd.DataFrame(columns=['Date', 'Deposit', 'Withdrawal', 'Payment Method', 'Balance', 'Remark'])
            
        df_md.to_excel(writer, sheet_name='MD Sir Account', index=False)

    elif export_type == 'revenue':
        filename = 'Revenue_Workbook.xlsx'
        if start_date and end_date:
            filename = f"Revenue_Workbook_{start_date_str}_to_{end_date_str}.xlsx"
            
        inc_query = Income.query
        if start_date:
            inc_query = inc_query.filter(Income.date >= start_date)
        if end_date:
            inc_query = inc_query.filter(Income.date <= end_date)
        inc_entries = inc_query.order_by(Income.date.asc()).all()
        
        # 1. Executive Summary Sheet
        period_str = f"{format_date(start_date)} to {format_date(end_date)}" if (start_date or end_date) else "All Time"
        exec_data = [
            {'Key Financial Indicator': 'Report Compiled Period', 'Value': period_str, 'Notes': 'Date range for compiled details'},
            {'Key Financial Indicator': 'Total Revenue Amount (₹)', 'Value': sum(e.amount for e in inc_entries) if inc_entries else 0.0, 'Notes': 'Sum of all categories'},
            {'Key Financial Indicator': 'Total Transactions Count', 'Value': len(inc_entries) if inc_entries else 0, 'Notes': 'Number of income logs'}
        ]
        pd.DataFrame(exec_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # Summary Sheet - Category Breakdown
        summary_rows = []
        if inc_entries:
            categories = sorted(list(set(e.category for e in inc_entries)))
            for cat in categories:
                cat_entries = [e for e in inc_entries if e.category == cat]
                summary_rows.append({
                    'Revenue Category': cat,
                    'Transaction Count': len(cat_entries),
                    'Total Amount (₹)': sum(e.amount for e in cat_entries)
                })
            df_sum = pd.DataFrame(summary_rows)
            grand_total_row = pd.DataFrame([{
                'Revenue Category': 'GRAND TOTAL',
                'Transaction Count': df_sum['Transaction Count'].sum(),
                'Total Amount (₹)': df_sum['Total Amount (₹)'].sum()
            }])
            df_sum = pd.concat([df_sum, grand_total_row], ignore_index=True)
            df_sum.to_excel(writer, sheet_name='Summary', index=False)
            
            # All Revenue Logs Sheet (combined detailed logs)
            df_all_rev = pd.DataFrame([{
                'Date': format_date(e.date),
                'Category': e.category,
                'Total Amount (₹)': e.amount,
                'Payment Method': e.payment_method,
                'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                'Description / Remarks': e.description
            } for e in inc_entries])
            if not df_all_rev.empty:
                total_row = pd.DataFrame([{
                    'Date': 'TOTAL',
                    'Category': 'All Categories',
                    'Total Amount (₹)': df_all_rev['Total Amount (₹)'].sum(),
                    'Payment Method': '',
                    'Cash Amount (₹)': df_all_rev['Cash Amount (₹)'].sum(),
                    'Online Amount (₹)': df_all_rev['Online Amount (₹)'].sum(),
                    'Description / Remarks': 'Total Revenue'
                }])
                df_all_rev = pd.concat([df_all_rev, total_row], ignore_index=True)
            df_all_rev.to_excel(writer, sheet_name='All Revenue Logs', index=False)

            # Category Sheets: Separate sheets for each category, date-wise + Total
            for cat in categories:
                cat_entries = [e for e in inc_entries if e.category == cat]
                df_cat = pd.DataFrame([{
                    'Date': format_date(e.date),
                    'Category': e.category,
                    'Total Amount (₹)': e.amount,
                    'Payment Method': e.payment_method,
                    'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                    'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                    'Description / Remarks': e.description
                } for e in cat_entries])
                if not df_cat.empty:
                    total_row = pd.DataFrame([{
                        'Date': 'TOTAL',
                        'Category': cat,
                        'Total Amount (₹)': df_cat['Total Amount (₹)'].sum(),
                        'Payment Method': '',
                        'Cash Amount (₹)': df_cat['Cash Amount (₹)'].sum(),
                        'Online Amount (₹)': df_cat['Online Amount (₹)'].sum(),
                        'Description / Remarks': f"Total Revenue for {cat}"
                    }])
                    df_cat = pd.concat([df_cat, total_row], ignore_index=True)
                sheet_title = clean_sheet_title(cat)
                df_cat.to_excel(writer, sheet_name=sheet_title, index=False)
        else:
            pd.DataFrame([{'Revenue Category': 'No Revenue Found', 'Transaction Count': 0, 'Total Amount (₹)': 0.0}]).to_excel(writer, sheet_name='Summary', index=False)

    elif export_type == 'expenses':
        filename = 'Expense_Workbook.xlsx'
        if start_date and end_date:
            filename = f"Expense_Workbook_{start_date_str}_to_{end_date_str}.xlsx"
            
        exp_query = Expense.query
        vp_query = VendorPayment.query
        payroll_query = Payroll.query
        adv_query = EmployeeAdvance.query
        
        if start_date:
            exp_query = exp_query.filter(Expense.date >= start_date)
            vp_query = vp_query.filter(VendorPayment.date >= start_date)
            payroll_query = payroll_query.filter(Payroll.payment_date >= start_date)
            adv_query = adv_query.filter(EmployeeAdvance.date >= start_date)
        if end_date:
            exp_query = exp_query.filter(Expense.date <= end_date)
            vp_query = vp_query.filter(VendorPayment.date <= end_date)
            payroll_query = payroll_query.filter(Payroll.payment_date <= end_date)
            adv_query = adv_query.filter(EmployeeAdvance.date <= end_date)
            
        exp_entries = exp_query.order_by(Expense.date.asc()).all()
        vendor_payments_list = vp_query.order_by(VendorPayment.date.asc()).all()
        payroll_payments_list = payroll_query.order_by(Payroll.payment_date.asc()).all()
        employee_advances_list = adv_query.order_by(EmployeeAdvance.date.asc()).all()

        # 1. Executive Summary Sheet
        period_str = f"{format_date(start_date)} to {format_date(end_date)}" if (start_date or end_date) else "All Time"
        total_exp_val = sum(e.amount for e in exp_entries) if exp_entries else 0.0
        total_vp_val = sum(vp.amount for vp in vendor_payments_list) if vendor_payments_list else 0.0
        total_payroll_val = sum(p.paid_amount for p in payroll_payments_list) if payroll_payments_list else 0.0
        total_adv_val = sum(adv.amount for adv in employee_advances_list) if employee_advances_list else 0.0
        grand_total = total_exp_val + total_vp_val + total_payroll_val + total_adv_val
        
        exec_data = [
            {'Key Financial Indicator': 'Report Compiled Period', 'Value': period_str, 'Notes': 'Date range for compiled details'},
            {'Key Financial Indicator': 'Total Operating Expenses (₹)', 'Value': total_exp_val, 'Notes': 'Direct scope costs (Hotel, Other, Dev)'},
            {'Key Financial Indicator': 'Total Vendor Payments (₹)', 'Value': total_vp_val, 'Notes': 'Payments released to suppliers'},
            {'Key Financial Indicator': 'Total Staff Salaries Paid (₹)', 'Value': total_payroll_val, 'Notes': 'Salary payouts released'},
            {'Key Financial Indicator': 'Total Staff Advances Issued (₹)', 'Value': total_adv_val, 'Notes': 'Advances issued to employees'},
            {'Key Financial Indicator': 'GRAND TOTAL EXPENSES (₹)', 'Value': grand_total, 'Notes': 'Sum of direct + HR + vendor outflows'}
        ]
        pd.DataFrame(exec_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # Summary Sheet - Expense Components Breakdown
        summary_rows = []
        if exp_entries:
            scopes = sorted(list(set(e.type for e in exp_entries)))
            for scope in scopes:
                scope_entries = [e for e in exp_entries if e.type == scope]
                summary_rows.append({
                    'Expense Component': f"General Expense ({scope})",
                    'Transaction Count': len(scope_entries),
                    'Total Amount (₹)': sum(e.amount for e in scope_entries)
                })
        if vendor_payments_list:
            summary_rows.append({
                'Expense Component': 'Vendor Payments Released',
                'Transaction Count': len(vendor_payments_list),
                'Total Amount (₹)': sum(vp.amount for vp in vendor_payments_list)
            })
        salaries_count = len([p for p in payroll_payments_list if p.paid_amount > 0])
        salaries_sum = sum(p.paid_amount for p in payroll_payments_list)
        if salaries_sum > 0:
            summary_rows.append({
                'Expense Component': 'Staff Payroll Released',
                'Transaction Count': salaries_count,
                'Total Amount (₹)': salaries_sum
            })
        if employee_advances_list:
            summary_rows.append({
                'Expense Component': 'Staff Salary Advances',
                'Transaction Count': len(employee_advances_list),
                'Total Amount (₹)': sum(adv.amount for adv in employee_advances_list)
            })

        if summary_rows:
            df_sum = pd.DataFrame(summary_rows)
            grand_total_row = pd.DataFrame([{
                'Expense Component': 'GRAND TOTAL',
                'Transaction Count': df_sum['Transaction Count'].sum(),
                'Total Amount (₹)': df_sum['Total Amount (₹)'].sum()
            }])
            df_sum = pd.concat([df_sum, grand_total_row], ignore_index=True)
            df_sum.to_excel(writer, sheet_name='Summary', index=False)
            
            # All Expense Logs (combined general direct expenses)
            if exp_entries:
                df_all_exp = pd.DataFrame([{
                    'Date': format_date(e.date),
                    'Type (Scope)': e.type,
                    'Category': e.category,
                    'Total Amount (₹)': e.amount,
                    'Payment Method': e.payment_method,
                    'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                    'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                    'Description / Remarks': e.description
                } for e in exp_entries])
                if not df_all_exp.empty:
                    total_row = pd.DataFrame([{
                        'Date': 'TOTAL',
                        'Type (Scope)': 'All Scopes',
                        'Category': '',
                        'Total Amount (₹)': df_all_exp['Total Amount (₹)'].sum(),
                        'Payment Method': '',
                        'Cash Amount (₹)': df_all_exp['Cash Amount (₹)'].sum(),
                        'Online Amount (₹)': df_all_exp['Online Amount (₹)'].sum(),
                        'Description / Remarks': 'Total Direct Expenses'
                    }])
                    df_all_exp = pd.concat([df_all_exp, total_row], ignore_index=True)
                df_all_exp.to_excel(writer, sheet_name='All Expense Logs', index=False)

            # Component Sheets: Separate sheets for each component type, date-wise + Total
            # 1. Direct Expense scopes
            if exp_entries:
                for scope in scopes:
                    scope_entries = [e for e in exp_entries if e.type == scope]
                    df_scope = pd.DataFrame([{
                        'Date': format_date(e.date),
                        'Scope': e.type,
                        'Category': e.category,
                        'Total Amount (₹)': e.amount,
                        'Payment Method': e.payment_method,
                        'Cash Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                        'Online Amount (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                        'Description / Remarks': e.description
                    } for e in scope_entries])
                    if not df_scope.empty:
                        total_row = pd.DataFrame([{
                            'Date': 'TOTAL',
                            'Scope': scope,
                            'Category': '',
                            'Total Amount (₹)': df_scope['Total Amount (₹)'].sum(),
                            'Payment Method': '',
                            'Cash Amount (₹)': df_scope['Cash Amount (₹)'].sum(),
                            'Online Amount (₹)': df_scope['Online Amount (₹)'].sum(),
                            'Description / Remarks': f"Total Expense for {scope}"
                        }])
                        df_scope = pd.concat([df_scope, total_row], ignore_index=True)
                    sheet_title = clean_sheet_title(scope)
                    df_scope.to_excel(writer, sheet_name=sheet_title, index=False)
                    
            # 2. Vendor Payments
            if vendor_payments_list:
                df_vp = pd.DataFrame([{
                    'Date': format_date(e.date),
                    'Vendor': e.vendor.name if e.vendor else 'Unknown',
                    'Total Amount (₹)': e.amount,
                    'Payment Method': e.payment_method,
                    'Cash Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                    'Online Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                    'Remarks': e.description
                } for e in vendor_payments_list])
                if not df_vp.empty:
                    total_row = pd.DataFrame([{
                        'Date': 'TOTAL',
                        'Vendor': '',
                        'Total Amount (₹)': df_vp['Total Amount (₹)'].sum(),
                        'Payment Method': '',
                        'Cash Paid (₹)': df_vp['Cash Paid (₹)'].sum(),
                        'Online Paid (₹)': df_vp['Online Paid (₹)'].sum(),
                        'Remarks': 'Total Vendor Payments'
                    }])
                    df_vp = pd.concat([df_vp, total_row], ignore_index=True)
                df_vp.to_excel(writer, sheet_name='Vendor Payments', index=False)
                
            # 3. Staff Salaries
            paid_payrolls = [p for p in payroll_payments_list if p.paid_amount > 0]
            if paid_payrolls:
                df_sal = pd.DataFrame([{
                    'Date': format_date(p.payment_date),
                    'Employee': p.employee.name if p.employee else 'Unknown',
                    'Month': p.month,
                    'Gross Salary': p.calculated_salary,
                    'Deductions': p.deductions + p.advance_adjusted,
                    'Net Payable': p.net_payable,
                    'Paid Amount (₹)': p.paid_amount,
                    'Cash Paid (₹)': resolve_cash_online(p.payment_method, p.paid_amount, p.cash_amount, p.online_amount)[0],
                    'Online Paid (₹)': resolve_cash_online(p.payment_method, p.paid_amount, p.cash_amount, p.online_amount)[1]
                } for p in paid_payrolls])
                if not df_sal.empty:
                    total_row = pd.DataFrame([{
                        'Date': 'TOTAL',
                        'Employee': '',
                        'Month': '',
                        'Gross Salary': df_sal['Gross Salary'].sum(),
                        'Deductions': df_sal['Deductions'].sum(),
                        'Net Payable': df_sal['Net Payable'].sum(),
                        'Paid Amount (₹)': df_sal['Paid Amount (₹)'].sum(),
                        'Cash Paid (₹)': df_sal['Cash Paid (₹)'].sum(),
                        'Online Paid (₹)': df_sal['Online Paid (₹)'].sum()
                    }])
                    df_sal = pd.concat([df_sal, total_row], ignore_index=True)
                df_sal.to_excel(writer, sheet_name='Staff Salaries', index=False)
                
            # 4. Staff Advances
            if employee_advances_list:
                df_adv = pd.DataFrame([{
                    'Date': format_date(e.date),
                    'Employee': e.employee.name if e.employee else 'Unknown',
                    'Total Amount (₹)': e.amount,
                    'Payment Method': e.payment_method,
                    'Cash Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[0],
                    'Online Paid (₹)': resolve_cash_online(e.payment_method, e.amount, e.cash_amount, e.online_amount)[1],
                    'Remarks': e.description
                } for e in employee_advances_list])
                if not df_adv.empty:
                    total_row = pd.DataFrame([{
                        'Date': 'TOTAL',
                        'Employee': '',
                        'Total Amount (₹)': df_adv['Total Amount (₹)'].sum(),
                        'Payment Method': '',
                        'Cash Paid (₹)': df_adv['Cash Paid (₹)'].sum(),
                        'Online Paid (₹)': df_adv['Online Paid (₹)'].sum(),
                        'Remarks': 'Total Salary Advances Issued'
                    }])
                    df_adv = pd.concat([df_adv, total_row], ignore_index=True)
                df_adv.to_excel(writer, sheet_name='Staff Advances', index=False)
        else:
            pd.DataFrame([{'Expense Component': 'No Expenses Found', 'Transaction Count': 0, 'Total Amount (₹)': 0.0}]).to_excel(writer, sheet_name='Summary', index=False)

    elif export_type == 'vendors':
        filename = 'Vendor_Accounts_Workbook.xlsx'
        vendors = Vendor.query.all()
        
        # 1. Executive Summary Sheet
        period_str = f"{format_date(start_date)} to {format_date(end_date)}" if (start_date or end_date) else "All Time"
        total_billed_all = sum(sum(b.amount for b in v.bills.all()) for v in vendors) if vendors else 0.0
        total_paid_all = sum(sum(p.amount for p in v.payments.all()) for v in vendors) if vendors else 0.0
        total_outstanding_all = sum(v.outstanding_balance for v in vendors) if vendors else 0.0
        
        exec_data = [
            {'Key Financial Indicator': 'Report Compiled Period', 'Value': period_str, 'Notes': 'Date range for compiled details'},
            {'Key Financial Indicator': 'Total Suppliers Count', 'Value': len(vendors), 'Notes': 'Number of active vendor accounts'},
            {'Key Financial Indicator': 'Total Invoiced / Billed (₹)', 'Value': total_billed_all, 'Notes': 'Total credit purchases billed'},
            {'Key Financial Indicator': 'Total Payments Released (₹)', 'Value': total_paid_all, 'Notes': 'Total amount paid to vendors'},
            {'Key Financial Indicator': 'Total Outstanding Balance (₹)', 'Value': total_outstanding_all, 'Notes': 'Net outstanding supplier payables (Dena)'}
        ]
        pd.DataFrame(exec_data).to_excel(writer, sheet_name='Executive Summary', index=False)

        # Vendor Summary Sheet
        v_summary = []
        for v in vendors:
            v.recalculate_balances()
            # Calculate filtered total bills and payments for the period if filtered
            bills_query = v.bills
            payments_query = v.payments
            if start_date:
                bills_query = bills_query.filter(VendorBill.date >= start_date)
                payments_query = payments_query.filter(VendorPayment.date >= start_date)
            if end_date:
                bills_query = bills_query.filter(VendorBill.date <= end_date)
                payments_query = payments_query.filter(VendorPayment.date <= end_date)
                
            total_billed_val = sum(b.amount for b in bills_query.all())
            total_paid_val = sum(p.amount for p in payments_query.all())
            
            v_summary.append({
                'Vendor Name': v.name,
                'Contact Person': v.contact_person or '',
                'Phone': v.phone or '',
                'Total Billed (₹)': total_billed_val,
                'Total Paid (₹)': total_paid_val,
                'Outstanding Balance (₹)': v.outstanding_balance
            })
            
        if v_summary:
            df_sum = pd.DataFrame(v_summary)
            # Add grand totals row
            grand_total_row = pd.DataFrame([{
                'Vendor Name': 'GRAND TOTAL',
                'Contact Person': '',
                'Phone': '',
                'Total Billed (₹)': df_sum['Total Billed (₹)'].sum(),
                'Total Paid (₹)': df_sum['Total Paid (₹)'].sum(),
                'Outstanding Balance (₹)': df_sum['Outstanding Balance (₹)'].sum()
            }])
            df_sum = pd.concat([df_sum, grand_total_row], ignore_index=True)
            df_sum.to_excel(writer, sheet_name='Vendor Summary', index=False)
        else:
            pd.DataFrame([{'Vendor Name': 'No Vendors Found'}]).to_excel(writer, sheet_name='Vendor Summary', index=False)
            
        for v in vendors:
            bills_q = VendorBill.query.filter_by(vendor_id=v.id)
            payments_q = VendorPayment.query.filter_by(vendor_id=v.id)
            if start_date:
                bills_q = bills_q.filter(VendorBill.date >= start_date)
                payments_q = payments_q.filter(VendorPayment.date >= start_date)
            if end_date:
                bills_q = bills_q.filter(VendorBill.date <= end_date)
                payments_q = payments_q.filter(VendorPayment.date <= end_date)
                
            bills = bills_q.all()
            payments = payments_q.all()
            
            ledger = []
            for b in bills:
                ledger.append({
                    'Date': format_date(b.date),
                    'Type': 'Invoice',
                    'Ref': b.bill_number,
                    'Details': b.description or '',
                    'Debit (Billed) (₹)': b.amount,
                    'Credit (Paid) (₹)': 0.0,
                    'Cash Paid (₹)': 0.0,
                    'Online Paid (₹)': 0.0
                })
            for p in payments:
                ledger.append({
                    'Date': format_date(p.date),
                    'Type': 'Payment',
                    'Ref': p.payment_method,
                    'Details': p.description or '',
                    'Debit (Billed) (₹)': 0.0,
                    'Credit (Paid) (₹)': p.amount,
                    'Cash Paid (₹)': resolve_cash_online(p.payment_method, p.amount, p.cash_amount, p.online_amount)[0],
                    'Online Paid (₹)': resolve_cash_online(p.payment_method, p.amount, p.cash_amount, p.online_amount)[1]
                })
            ledger.sort(key=lambda x: x['Date'])
            
            # Recalculate outstanding running balance
            running = 0.0
            for item in ledger:
                running += item['Debit (Billed) (₹)'] - item['Credit (Paid) (₹)']
                item['Outstanding (₹)'] = running
                
            # Append a total row to individual ledger
            if ledger:
                total_debit = sum(item['Debit (Billed) (₹)'] for item in ledger)
                total_credit = sum(item['Credit (Paid) (₹)'] for item in ledger)
                total_cash = sum(item['Cash Paid (₹)'] for item in ledger)
                total_online = sum(item['Online Paid (₹)'] for item in ledger)
                final_outstanding = ledger[-1]['Outstanding (₹)']
                total_row = {
                    'Date': 'TOTALS',
                    'Type': '',
                    'Ref': '',
                    'Details': f"Total Invoiced: {total_debit} | Total Paid: {total_credit}",
                    'Debit (Billed) (₹)': total_debit,
                    'Credit (Paid) (₹)': total_credit,
                    'Cash Paid (₹)': total_cash,
                    'Online Paid (₹)': total_online,
                    'Outstanding (₹)': final_outstanding
                }
                ledger.append(total_row)
                
            if not ledger:
                df_vendor = pd.DataFrame(columns=[
                    'Date', 'Type', 'Ref', 'Details', 'Debit (Billed) (₹)',
                    'Credit (Paid) (₹)', 'Cash Paid (₹)', 'Online Paid (₹)', 'Outstanding (₹)'
                ])
            else:
                df_vendor = pd.DataFrame(ledger)
            sheet_title = clean_sheet_title(v.name)
            df_vendor.to_excel(writer, sheet_name=sheet_title or 'Vendor', index=False)

    elif export_type == 'employees':
        filename = 'Employee_Payroll_Workbook.xlsx'
        if start_date and end_date:
            filename = f"Employee_Payroll_Workbook_{start_date_str}_to_{end_date_str}.xlsx"
            
        employees = Employee.query.all()
        
        # 1. HR Summary Sheet (3 Core Columns per Employee)
        emp_summary = []
        for emp in employees:
            emp.recalculate_balances()
            advances_q = EmployeeAdvance.query.filter_by(employee_id=emp.id)
            payrolls_q = Payroll.query.filter_by(employee_id=emp.id)
            if start_date:
                advances_q = advances_q.filter(EmployeeAdvance.date >= start_date)
                payrolls_q = payrolls_q.filter(Payroll.date >= start_date)
            if end_date:
                advances_q = advances_q.filter(EmployeeAdvance.date <= end_date)
                payrolls_q = payrolls_q.filter(Payroll.date <= end_date)
                
            tot_sal = sum(p.calculated_salary for p in payrolls_q.all())
            tot_adv = sum(adv.amount for adv in advances_q.all())
            rem_amt = tot_sal - tot_adv
            
            emp_summary.append({
                'Employee Name': emp.name,
                'Designation': emp.designation or '',
                'Total Salary (₹)': tot_sal,
                'Advance Paid (₹)': tot_adv,
                'Remaining Amount (₹)': rem_amt
            })
            
        if emp_summary:
            df_hr_sum = pd.DataFrame(emp_summary)
            tot_s = df_hr_sum['Total Salary (₹)'].sum()
            tot_a = df_hr_sum['Advance Paid (₹)'].sum()
            tot_r = tot_s - tot_a
            
            grand_row = pd.DataFrame([{
                'Employee Name': 'GRAND TOTAL',
                'Designation': 'Outstanding Summary',
                'Total Salary (₹)': tot_s,
                'Advance Paid (₹)': tot_a,
                'Remaining Amount (₹)': tot_r
            }])
            df_hr_sum = pd.concat([df_hr_sum, grand_row], ignore_index=True)
            df_hr_sum.to_excel(writer, sheet_name='HR Summary', index=False)
        else:
            pd.DataFrame([{'Employee Name': 'No Employees Found'}]).to_excel(writer, sheet_name='HR Summary', index=False)

        # 2. Main Payroll & Advances Register Sheet
        all_payroll_rows = []
        
        # Include all payrolls
        payrolls_q = Payroll.query
        if start_date:
            payrolls_q = payrolls_q.filter(Payroll.date >= start_date)
        if end_date:
            payrolls_q = payrolls_q.filter(Payroll.date <= end_date)
        payrolls = payrolls_q.order_by(Payroll.date.asc(), Payroll.id.asc()).all()
        
        for p in payrolls:
            rem = max(0.0, p.net_payable - p.paid_amount)
            stat = p.payment_status or ('Paid' if rem <= 0.01 else ('Partially Paid' if p.paid_amount > 0 else 'Pending'))
            all_payroll_rows.append({
                'Date': format_date(p.date or p.payment_date or p.created_at.date()),
                'Employee': p.employee.name if p.employee else 'Staff',
                'Type': f'Payroll ({p.month})',
                'Total Salary (₹)': p.calculated_salary,
                'Advance Paid (₹)': p.advance_adjusted,
                'Remaining Amount (₹)': p.calculated_salary - p.advance_adjusted,
                'Net Payable (₹)': p.net_payable,
                'Amount Paid (₹)': p.paid_amount,
                'Payment Method': p.payment_method or 'Cash',
                'Status': stat,
                'Remarks': p.remarks or 'Regular Salary'
            })

        # Include all advances issued
        all_advances_q = EmployeeAdvance.query
        if start_date:
            all_advances_q = all_advances_q.filter(EmployeeAdvance.date >= start_date)
        if end_date:
            all_advances_q = all_advances_q.filter(EmployeeAdvance.date <= end_date)
        advances = all_advances_q.order_by(EmployeeAdvance.date.asc(), EmployeeAdvance.id.asc()).all()

        for adv in advances:
            all_payroll_rows.append({
                'Date': format_date(adv.date),
                'Employee': adv.employee.name if adv.employee else 'Staff',
                'Type': 'Salary Advance Given',
                'Total Salary (₹)': 0.0,
                'Advance Paid (₹)': adv.amount,
                'Remaining Amount (₹)': -adv.amount,
                'Net Payable (₹)': 0.0,
                'Amount Paid (₹)': adv.amount,
                'Payment Method': adv.payment_method or 'Cash',
                'Status': 'Paid',
                'Remarks': adv.description or 'Salary advance issued'
            })

        all_payroll_rows.sort(key=lambda x: x['Date'])

        if all_payroll_rows:
            tot_gross = sum(r['Total Salary (₹)'] for r in all_payroll_rows)
            tot_adv_iss = sum(r['Advance Paid (₹)'] for r in all_payroll_rows)
            tot_rem_calc = tot_gross - tot_adv_iss
            tot_net = sum(r['Net Payable (₹)'] for r in all_payroll_rows)
            tot_paid = sum(r['Amount Paid (₹)'] for r in all_payroll_rows)
            
            all_payroll_rows.append({
                'Date': 'TOTALS',
                'Employee': 'Outstanding Balance',
                'Type': '',
                'Total Salary (₹)': tot_gross,
                'Advance Paid (₹)': tot_adv_iss,
                'Remaining Amount (₹)': tot_rem_calc,
                'Net Payable (₹)': tot_net,
                'Amount Paid (₹)': tot_paid,
                'Payment Method': '',
                'Status': '',
                'Remarks': f'Outstanding Total: ₹{tot_rem_calc:,.2f}'
            })
            df_pay = pd.DataFrame(all_payroll_rows)
        else:
            df_pay = pd.DataFrame(columns=[
                'Date', 'Employee', 'Type', 'Total Salary (₹)', 'Advance Paid (₹)',
                'Remaining Amount (₹)', 'Net Payable (₹)', 'Amount Paid (₹)',
                'Payment Method', 'Status', 'Remarks'
            ])
            
        df_pay.to_excel(writer, sheet_name='Payroll Register', index=False)

        # 3. Dedicated Salary Advances Log Sheet
        adv_rows = []
        for adv in advances:
            adv_rows.append({
                'Date': format_date(adv.date),
                'Employee Name': adv.employee.name if adv.employee else 'Staff',
                'Advance Paid (₹)': adv.amount,
                'Payment Method': adv.payment_method or 'Cash',
                'Description / Remarks': adv.description or 'Salary advance issued'
            })
        if adv_rows:
            tot_adv_log = sum(r['Advance Paid (₹)'] for r in adv_rows)
            adv_rows.append({
                'Date': 'TOTALS',
                'Employee Name': 'Outstanding Advances Total',
                'Advance Paid (₹)': tot_adv_log,
                'Payment Method': '',
                'Description / Remarks': f'Total Advance Paid: ₹{tot_adv_log:,.2f}'
            })
            df_adv_log = pd.DataFrame(adv_rows)
        else:
            df_adv_log = pd.DataFrame(columns=[
                'Date', 'Employee Name', 'Advance Paid (₹)', 'Payment Method', 'Description / Remarks'
            ])
        df_adv_log.to_excel(writer, sheet_name='Salary Advances Log', index=False)

        # 4. Per Employee Detailed Statements (Debit, Credit & Running Balance)
        for emp in employees:
            emp.recalculate_balances()
            advances_q = EmployeeAdvance.query.filter_by(employee_id=emp.id)
            emp_payrolls_q = Payroll.query.filter_by(employee_id=emp.id)
            if start_date:
                advances_q = advances_q.filter(EmployeeAdvance.date >= start_date)
                emp_payrolls_q = emp_payrolls_q.filter(Payroll.date >= start_date)
            if end_date:
                advances_q = advances_q.filter(EmployeeAdvance.date <= end_date)
                emp_payrolls_q = emp_payrolls_q.filter(Payroll.date <= end_date)

            emp_entries = []
            for adv in advances_q.all():
                emp_entries.append({
                    'date': adv.date,
                    'reference': 'Advance Issued',
                    'description': adv.description or 'Salary Advance',
                    'debit': adv.amount,
                    'credit': 0.0,
                    'sort_id': f"adv-{adv.id}"
                })
            for pay in emp_payrolls_q.all():
                try:
                    accrued_date = datetime.strptime(f"{pay.month}-01", "%Y-%m-%d").date()
                except ValueError:
                    accrued_date = pay.payment_date or pay.date or date.today()

                emp_entries.append({
                    'date': accrued_date,
                    'reference': 'Payroll generated',
                    'description': f"Gross: {pay.calculated_salary} | Adj: {pay.advance_adjusted} | Ded: {pay.deductions}",
                    'debit': pay.net_payable,
                    'credit': 0.0,
                    'sort_id': f"acc-{pay.id}"
                })

                if pay.paid_amount > 0:
                    try:
                        payment_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
                    except ValueError:
                        payment_date = pay.payment_date or pay.date or date.today()

                    emp_entries.append({
                        'date': payment_date,
                        'reference': pay.payment_method or 'Cash',
                        'description': 'Released payroll cash',
                        'debit': 0.0,
                        'credit': pay.paid_amount,
                        'sort_id': f"pay-{pay.id}"
                    })

                if pay.advance_adjusted > 0:
                    try:
                        recovery_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
                    except ValueError:
                        recovery_date = pay.payment_date or pay.date or date.today()

                    emp_entries.append({
                        'date': recovery_date,
                        'reference': 'Payroll adjustment',
                        'description': 'Recovered from basic salary',
                        'debit': 0.0,
                        'credit': pay.advance_adjusted,
                        'sort_id': f"rec-{pay.id}"
                    })

            emp_entries.sort(key=lambda x: (x['date'], x['sort_id']))

            running = 0.0
            tot_d = 0.0
            tot_c = 0.0
            records = []

            for entry in emp_entries:
                tot_d += entry['debit']
                tot_c += entry['credit']
                if 'acc' in entry['sort_id'] or 'adv' in entry['sort_id']:
                    running += entry['debit']
                elif 'pay' in entry['sort_id'] or 'rec' in entry['sort_id']:
                    running -= entry['credit']

                records.append({
                    'Date': entry['date'].strftime('%d-%b-%Y') if hasattr(entry['date'], 'strftime') else str(entry['date']),
                    'Reference': entry['reference'],
                    'Description': entry['description'],
                    'Salary Accrued / Advance (Debit) (₹)': entry['debit'] if entry['debit'] > 0 else '-',
                    'Payment Released (Credit) (₹)': entry['credit'] if entry['credit'] > 0 else '-',
                    'Running Balance (₹)': running
                })

            if records:
                records.append({
                    'Date': 'TOTALS',
                    'Reference': 'Ending Balance',
                    'Description': 'Statement Total',
                    'Salary Accrued / Advance (Debit) (₹)': tot_d,
                    'Payment Released (Credit) (₹)': tot_c,
                    'Running Balance (₹)': emp.outstanding_salary
                })
                df_emp = pd.DataFrame(records)
            else:
                df_emp = pd.DataFrame(columns=[
                    'Date', 'Reference', 'Description',
                    'Salary Accrued / Advance (Debit) (₹)',
                    'Payment Released (Credit) (₹)',
                    'Running Balance (₹)'
                ])
            sheet_title = clean_sheet_title(emp.name)
            df_emp.to_excel(writer, sheet_name=sheet_title or 'Employee', index=False)

    elif export_type == 'finance':
        filename = 'Finance_Ledger_Book.xlsx'
        if start_date and end_date:
            filename = f"Finance_Ledger_Book_{start_date_str}_to_{end_date_str}.xlsx"
            
        entries_q = CashBook.query
        if start_date:
            entries_q = entries_q.filter(CashBook.date >= start_date)
        if end_date:
            entries_q = entries_q.filter(CashBook.date <= end_date)
        entries = entries_q.order_by(CashBook.date.asc(), CashBook.id.asc()).all()
        
        running_bal = 0.0
        total_dep = 0.0
        total_with = 0.0
        rows = []
        for e in entries:
            is_dep = e.transaction_type in ['In', 'Deposit']
            dep = e.deposit_amount if e.deposit_amount > 0 else (e.amount if is_dep else 0.0)
            wit = e.withdrawal_amount if e.withdrawal_amount > 0 else (e.amount if not is_dep else 0.0)
            running_bal += (dep - wit)
            total_dep += dep
            total_with += wit
            
            cat = e.category
            if not cat:
                if e.source == 'Income':
                    cat = 'Cash Collection'
                elif e.source == 'Expense':
                    cat = 'Miscellaneous'
                elif e.source == 'Payroll':
                    cat = 'Staff Salary'
                elif e.source == 'VendorPayment':
                    cat = 'Vendor Payment'
                elif is_dep:
                    cat = 'Other Income'
                else:
                    cat = 'Miscellaneous'

            rows.append({
                'Date': format_date(e.date),
                'Deposit (₹)': dep if dep > 0 else "",
                'Withdrawal (₹)': wit if wit > 0 else "",
                'Payment Method': e.payment_method or 'Cash',
                'Balance (₹)': running_bal,
                'Remarks': e.remarks or e.description or '',
                'Category': cat
            })
            
        if rows:
            rows.append({
                'Date': 'TOTAL',
                'Deposit (₹)': total_dep,
                'Withdrawal (₹)': total_with,
                'Payment Method': '',
                'Balance (₹)': running_bal,
                'Remarks': '',
                'Category': ''
            })
            df_fin = pd.DataFrame(rows)
        else:
            df_fin = pd.DataFrame(columns=[
                'Date', 'Deposit (₹)', 'Withdrawal (₹)', 'Payment Method',
                'Balance (₹)', 'Remarks', 'Category'
            ])
            
        df_fin.to_excel(writer, sheet_name='Finance Ledger', index=False)

    else:  # credit
        filename = 'Credit_Lena-Dena_Workbook.xlsx'
        parties = CreditAccount.query.all()
        
        # Calculate summaries first
        p_summary = []
        for party in parties:
            party.recalculate_balances()
            p_summary.append({
                'Party Name': party.party_name,
                'Phone': party.phone or '',
                'Total Receivable (Lena) (₹)': party.receivable_balance,
                'Total Payable (Dena) (₹)': party.payable_balance
            })
            
        # 1. Executive Summary Sheet
        period_str = f"{format_date(start_date)} to {format_date(end_date)}" if (start_date or end_date) else "All Time"
        total_receivables_all = sum(p['Total Receivable (Lena) (₹)'] for p in p_summary) if p_summary else 0.0
        total_payables_all = sum(p['Total Payable (Dena) (₹)'] for p in p_summary) if p_summary else 0.0
        
        exec_data = [
            {'Key Financial Indicator': 'Report Compiled Period', 'Value': period_str, 'Notes': 'Date range for compiled details'},
            {'Key Financial Indicator': 'Total Credit Accounts Count', 'Value': len(parties), 'Notes': 'Number of active credit accounts'},
            {'Key Financial Indicator': 'Total Outstanding Receivables (Lena) (₹)', 'Value': total_receivables_all, 'Notes': 'Amount owed to the hotel'},
            {'Key Financial Indicator': 'Total Outstanding Payables (Dena) (₹)', 'Value': total_payables_all, 'Notes': 'Amount hotel owes to credit parties'}
        ]
        pd.DataFrame(exec_data).to_excel(writer, sheet_name='Executive Summary', index=False)
            
        # 2. Credit Summary Sheet
        if p_summary:
            df_sum = pd.DataFrame(p_summary)
            # Add grand totals row
            grand_total_row = pd.DataFrame([{
                'Party Name': 'GRAND TOTAL',
                'Phone': '',
                'Total Receivable (Lena) (₹)': df_sum['Total Receivable (Lena) (₹)'].sum(),
                'Total Payable (Dena) (₹)': df_sum['Total Payable (Dena) (₹)'].sum()
            }])
            df_sum = pd.concat([df_sum, grand_total_row], ignore_index=True)
            df_sum.to_excel(writer, sheet_name='Credit Summary', index=False)
        else:
            pd.DataFrame([{'Party Name': 'No Credit Accounts Found'}]).to_excel(writer, sheet_name='Credit Summary', index=False)
            
        for party in parties:
            txs_q = CreditTransaction.query.filter_by(credit_account_id=party.id)
            if start_date:
                txs_q = txs_q.filter(CreditTransaction.date >= start_date)
            if end_date:
                txs_q = txs_q.filter(CreditTransaction.date <= end_date)
            txs = txs_q.order_by(CreditTransaction.date.asc()).all()
            
            ledger = [{
                'Date': format_date(t.date),
                'Type': t.transaction_type,
                'Payment Channel': t.payment_method,
                'Total Amount (₹)': t.amount,
                'Cash Amount (₹)': resolve_cash_online(t.payment_method, t.amount, t.cash_amount, t.online_amount)[0],
                'Online Amount (₹)': resolve_cash_online(t.payment_method, t.amount, t.cash_amount, t.online_amount)[1],
                'Remarks': t.description or ''
            } for t in txs]
            
            # Append a total row to credit party ledger
            if ledger:
                total_amount = sum(item['Total Amount (₹)'] for item in ledger)
                total_cash = sum(item['Cash Amount (₹)'] for item in ledger)
                total_online = sum(item['Online Amount (₹)'] for item in ledger)
                total_row = {
                    'Date': 'TOTAL',
                    'Type': '',
                    'Payment Channel': 'Net outstanding balance:',
                    'Total Amount (₹)': total_amount,
                    'Cash Amount (₹)': total_cash,
                    'Online Amount (₹)': total_online,
                    'Remarks': ''
                }
                ledger.append(total_row)
                
            if not ledger:
                df_party = pd.DataFrame(columns=[
                    'Date', 'Type', 'Payment Channel', 'Total Amount (₹)',
                    'Cash Amount (₹)', 'Online Amount (₹)', 'Remarks'
                ])
            else:
                df_party = pd.DataFrame(ledger)
            sheet_title = clean_sheet_title(party.party_name)
            df_party.to_excel(writer, sheet_name=sheet_title or 'Party', index=False)

    # Apply openpyxl styling across all worksheets before saving
    apply_openpyxl_styles(writer.book)

    writer.close()
    output.seek(0)
    response = send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@reports_bp.route('/export/employee_ledger/<int:employee_id>')
@reports_bp.route('/export/employee_ledger')
@login_required
def export_employee_ledger(employee_id=None):
    if not employee_id:
        employee_id = request.args.get('employee_id', type=int)
    if not employee_id:
        flash("Please select an employee to export statement.", "warning")
        return redirect(url_for('staff.index', view='ledgers'))
        
    employee = Employee.query.get_or_404(employee_id)
    employee.recalculate_balances()

    advances = EmployeeAdvance.query.filter_by(employee_id=employee_id).all()
    payrolls = Payroll.query.filter_by(employee_id=employee_id).all()

    ledger_entries = []
    tot_adv_issued = sum(a.amount for a in advances)
    tot_adv_adjusted = sum(p.advance_adjusted for p in payrolls)
    net_adv_loan = max(0.0, tot_adv_issued - tot_adv_adjusted)

    for adv in advances:
        ledger_entries.append({
            'date': adv.date,
            'type': 'Advance Salary',
            'reference': 'Advance Issued',
            'description': adv.description or 'Salary Advance',
            'debit': adv.amount,
            'credit': 0.0,
            'sort_id': f"adv-{adv.id}"
        })

    for pay in payrolls:
        try:
            accrued_date = datetime.strptime(f"{pay.month}-01", "%Y-%m-%d").date()
        except ValueError:
            accrued_date = pay.payment_date or pay.date or date.today()

        ledger_entries.append({
            'date': accrued_date,
            'type': f"Salary Accrued ({pay.month})",
            'reference': 'Payroll generated',
            'description': f"Gross: {pay.calculated_salary} | Adj: {pay.advance_adjusted} | Ded: {pay.deductions}",
            'debit': pay.net_payable,
            'credit': 0.0,
            'sort_id': f"acc-{pay.id}"
        })

        if pay.paid_amount > 0:
            try:
                payment_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
            except ValueError:
                payment_date = pay.payment_date or pay.date or date.today()

            ledger_entries.append({
                'date': payment_date,
                'type': f"Salary Payment ({pay.month})",
                'reference': pay.payment_method or 'Cash',
                'description': 'Released payroll cash',
                'debit': 0.0,
                'credit': pay.paid_amount,
                'sort_id': f"pay-{pay.id}"
            })

        if pay.advance_adjusted > 0:
            try:
                recovery_date = pay.payment_date or datetime.strptime(f"{pay.month}-28", "%Y-%m-%d").date()
            except ValueError:
                recovery_date = pay.payment_date or pay.date or date.today()

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

    running = 0.0
    tot_debit = 0.0
    tot_credit = 0.0

    rows_data = []
    for entry in ledger_entries:
        tot_debit += entry['debit']
        tot_credit += entry['credit']
        if 'Accrued' in entry['type'] or 'Advance' in entry['type']:
            running += entry['debit']
        elif 'Payment' in entry['type'] or 'Recovery' in entry['type']:
            running -= entry['credit']

        rows_data.append({
            'Date': entry['date'].strftime('%d-%b-%Y') if hasattr(entry['date'], 'strftime') else str(entry['date']),
            'Reference': entry['reference'],
            'Description': entry['description'],
            'Salary Accrued / Advance (Debit) (₹)': entry['debit'] if entry['debit'] > 0 else '-',
            'Payment Released (Credit) (₹)': entry['credit'] if entry['credit'] > 0 else '-',
            'Running Balance (₹)': running
        })

    rows_data.append({
        'Date': 'TOTALS',
        'Reference': 'Ending Balance',
        'Description': 'Statement Total',
        'Salary Accrued / Advance (Debit) (₹)': tot_debit,
        'Payment Released (Credit) (₹)': tot_credit,
        'Running Balance (₹)': employee.outstanding_salary
    })

    import openpyxl
    output = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = clean_sheet_title(f"Statement - {employee.name}")

    # Title Banner
    ws.merge_cells('A1:F1')
    ws['A1'] = f"EMPLOYEE ACCOUNT LEDGER STATEMENT - {employee.name.upper()}"
    ws['A1'].font = Font(name='Calibri', size=13, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    # Summary Info Box
    ws['A3'] = "Employee Name:"
    ws['B3'] = employee.name
    ws['D3'] = "Net Advance Loan:"
    ws['E3'] = net_adv_loan

    ws['A4'] = "Designation:"
    ws['B4'] = employee.designation or 'N/A'
    ws['D4'] = "Unpaid Net Salary:"
    ws['E4'] = employee.outstanding_salary

    ws['A5'] = "Daily Wage Rate:"
    ws['B5'] = employee.basic_salary
    ws['D5'] = "Net Account Position:"
    if employee.net_balance > 0:
        net_pos_str = f"+ ₹{employee.net_balance:,.2f} (We Pay Employee)"
    elif employee.net_balance < 0:
        net_pos_str = f"- ₹{abs(employee.net_balance):,.2f} (Employee Owes Hotel)"
    else:
        net_pos_str = "₹0.00 (Settled)"
    ws['E5'] = net_pos_str

    for r_idx in range(3, 6):
        ws[f'A{r_idx}'].font = Font(bold=True)
        ws[f'D{r_idx}'].font = Font(bold=True)

    # Headers at Row 7
    headers = [
        'Date', 'Reference', 'Description',
        'Salary Accrued / Advance (Debit) (₹)',
        'Payment Released (Credit) (₹)',
        'Running Balance (₹)'
    ]
    ws.append([]) # Row 6 empty
    ws.append(headers) # Row 7

    header_fill = PatternFill(start_color='0F172A', end_color='0F172A', fill_type='solid')
    header_font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')

    for col_idx in range(1, 7):
        c = ws.cell(row=7, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center' if col_idx <= 2 else ('right' if col_idx >= 4 else 'left'))

    # Append rows
    row_num = 8
    for r in rows_data:
        ws.append([
            r['Date'],
            r['Reference'],
            r['Description'],
            r['Salary Accrued / Advance (Debit) (₹)'],
            r['Payment Released (Credit) (₹)'],
            r['Running Balance (₹)']
        ])
        
        if r['Date'] == 'TOTALS':
            for c_idx in range(1, 7):
                cell = ws.cell(row=row_num, column=c_idx)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')
        row_num += 1

    # Auto-width
    for col in ws.columns:
        max_l = max(len(str(cell.value or '')) for cell in col)
        col_let = get_column_letter(col[0].column)
        ws.column_dimensions[col_let].width = max(max_l + 3, 12)

    wb.save(output)
    output.seek(0)

    clean_emp_name = "".join(c for c in employee.name if c.isalnum() or c in (' ', '_', '-')).strip()
    filename = f"Employee_Ledger_Statement_{clean_emp_name.replace(' ', '_')}.xlsx"

    response = send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

