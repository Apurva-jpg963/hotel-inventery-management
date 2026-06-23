from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Email, Optional, Regexp
from datetime import date

class EmployeeForm(FlaskForm):
    name = StringField('Employee Name', validators=[
        DataRequired(),
        Length(min=3, max=100, message="Name must be between 3 and 100 characters.")
    ])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    designation = StringField('Designation / Role', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ], render_kw={"placeholder": "e.g. Head Chef, Waiter, Manager"})
    basic_salary = FloatField('Daily Wage (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.0, message="Salary rate cannot be negative.")
    ])
    status = SelectField('Employment Status', choices=[
        ('Active', 'Active'),
        ('Inactive', 'Inactive')
    ], default='Active', validators=[DataRequired()])
    submit = SubmitField('Save Employee Profile')


class AdvanceForm(FlaskForm):
    employee_id = SelectField('Select Employee', coerce=int, validators=[DataRequired()])
    date = DateField('Advance Date', default=date.today, validators=[DataRequired()])
    amount = FloatField('Advance Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Advance amount must be greater than zero.")
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
    description = TextAreaField('Reason / Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Issue Advance')


class PayrollPaymentForm(FlaskForm):
    employee_id = SelectField('Select Employee', coerce=int, validators=[DataRequired()])
    month = StringField('Payment Month/Date Note', validators=[
        DataRequired(),
        Length(max=100, message="Note must be under 100 characters.")
    ])
    days_present = FloatField('Total Days Present', validators=[
        DataRequired(message="Total days present is required."),
        NumberRange(min=0.0, message="Days present must be 0 or more.")
    ])
    calculated_salary = FloatField('Calculated Gross Salary (₹)', validators=[NumberRange(min=0.0)])
    advance_adjusted = FloatField('Adjust Advance Balance (₹)', default=0.0, validators=[NumberRange(min=0.0)])
    deductions = FloatField('Other Deductions (₹)', default=0.0, validators=[NumberRange(min=0.0)])
    net_payable = FloatField('Net Payable Salary (₹)', validators=[NumberRange(min=0.0)])
    paid_amount = FloatField('Amount Paid Now (₹)', default=0.0, validators=[NumberRange(min=0.0)])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    submit = SubmitField('Release Payroll')


class StaffSalaryPaymentForm(FlaskForm):
    amount = FloatField('Amount to Pay (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Payment amount must be greater than zero.")
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
    payment_date = DateField('Payment Date', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Record Payment')
