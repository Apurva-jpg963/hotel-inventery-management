from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length
from datetime import date

class ExpenseForm(FlaskForm):
    date = DateField('Transaction Date', default=date.today, validators=[DataRequired()])
    type = SelectField('Expense Type', choices=[
        ('Hotel', 'Hotel Expense'),
        ('Other', 'Other Expense'),
        ('Development', 'Development Expense')
    ], validators=[DataRequired()])
    category = StringField('Category', validators=[
        DataRequired(),
        Length(min=2, max=50, message="Category name must be between 2 and 50 characters.")
    ])
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
    submit = SubmitField('Save Expense Record')
