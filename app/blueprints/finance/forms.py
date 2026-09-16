from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from datetime import date

class SavingsTransactionForm(FlaskForm):
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    transaction_type = SelectField('Type', choices=[
        ('Deposit', 'Deposit to Bank (Cash Outflow)'),
        ('Withdrawal', 'Withdrawal from Bank (Cash Inflow)')
    ], validators=[DataRequired()])
    payment_method = SelectField('Payment Channel', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ])
    bank_name = StringField('Bank Name', validators=[
        DataRequired(),
        Length(min=2, max=100, message="Bank name is required.")
    ])
    description = TextAreaField('Description / Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Savings Entry')


class LoanRepaymentForm(FlaskForm):
    bank_name = StringField('Bank / Lender Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    date = DateField('Payment Date', default=date.today, validators=[DataRequired()])
    amount = FloatField('Installment Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ])
    payment_method = SelectField('Payment Channel', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    description = TextAreaField('Remarks / Details', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Installment Paid')


class CreditAccountForm(FlaskForm):
    party_name = StringField('Party / Person Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address Details', validators=[Optional()])
    submit = SubmitField('Create Credit Party')


class CreditTransactionForm(FlaskForm):
    credit_account_id = SelectField('Select Credit Party', coerce=int, validators=[DataRequired()])
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[
        ('Given', 'Bill Pending (Lena - Credit Given / Money Owed to Us)'),
        ('Received', 'Payment Received (Clear Lena Bill - Money Received)'),
        ('Taken', 'Bill Payable (Dena - Credit Taken / Money We Owe)'),
        ('Paid', 'Payment Paid (Clear Dena Bill - Money Paid Out)')
    ], validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ], render_kw={"placeholder": "Enter positive amount in ₹"})
    payment_method = SelectField('Payment Channel', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    description = TextAreaField('Transaction Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Transaction')


class FinanceLedgerForm(FlaskForm):
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    type = SelectField('Entry Type', choices=[
        ('Deposit', 'Deposit (+)'),
        ('Withdrawal', 'Withdrawal (-)')
    ], default='Deposit', validators=[DataRequired()])
    description = StringField('Description', validators=[
        DataRequired(),
        Length(min=2, max=255, message="Description is required.")
    ], render_kw={"placeholder": "e.g. Daily Cash Collection, Grocery Purchase"})
    category = SelectField('Category', choices=[
        ('Cash Collection', 'Cash Collection'),
        ('Online Collection', 'Online Collection'),
        ('Bank Deposit', 'Bank Deposit'),
        ('Owner Investment', 'Owner Investment'),
        ('Other Income', 'Other Income'),
        ('Grocery', 'Grocery'),
        ('Dairy', 'Dairy'),
        ('Gas', 'Gas'),
        ('Wood', 'Wood'),
        ('Staff Salary', 'Staff Salary'),
        ('Vendor Payment', 'Vendor Payment'),
        ('Maintenance', 'Maintenance'),
        ('Rent', 'Rent'),
        ('Electricity', 'Electricity'),
        ('Miscellaneous', 'Miscellaneous')
    ], validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Card', 'Card'),
        ('Cheque', 'Cheque'),
        ('Other', 'Other')
    ], default='Cash', validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ], render_kw={"placeholder": "0.00"})
    remarks = TextAreaField('Remarks', validators=[Optional(), Length(max=255)], render_kw={"placeholder": "Optional notes"})
    submit = SubmitField('Save Ledger Entry')


class MDSirTransactionForm(FlaskForm):
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    transaction_type = SelectField('Type', choices=[
        ('Deposit', 'Deposit / Capital Contribution (Cash Inflow)'),
        ('Withdraw', 'Withdrawal / Drawings (Cash Outflow)')
    ], validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    description = TextAreaField('Purpose / Details', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record MD Entry')
