from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length
from datetime import date

class IncomeForm(FlaskForm):
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    category = SelectField('Income Category', choices=[
        ('Old Bill Received', 'Old Bill Received'),
        ('Restaurant Revenue', 'Restaurant Revenue'),
        ('Banquet Revenue', 'Banquet Revenue'),
        ('Opening Balance', 'Opening Balance'),
        ('Other Revenue', 'Other Revenue')
    ], validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than zero.")
    ])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI', 'UPI / QR Code'),
        ('Card', 'Card Payment'),
        ('Bank', 'Direct Bank Transfer'),
        ('Cheque', 'Cheque'),
        ('Split', 'Split (Cash & Online)')
    ], default='Cash', validators=[DataRequired()])
    cash_amount = FloatField('Cash Portion (₹)', default=0.0)
    online_amount = FloatField('Online Portion (₹)', default=0.0)
    description = TextAreaField('Description / Notes', validators=[Length(max=255)])
    submit = SubmitField('Save Income Record')
