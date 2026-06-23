from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Email, Optional
from datetime import date

class VendorForm(FlaskForm):
    name = StringField('Vendor / Firm Name', validators=[
        DataRequired(),
        Length(min=3, max=100, message="Vendor name must be between 3 and 100 characters.")
    ])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField('Address', validators=[Optional()])
    submit = SubmitField('Save Vendor Profile')


class VendorBillForm(FlaskForm):
    vendor_id = SelectField('Select Vendor', coerce=int, validators=[DataRequired()])
    bill_number = StringField('Bill / Invoice Number', validators=[
        DataRequired(),
        Length(min=1, max=50, message="Invoice number is required.")
    ])
    date = DateField('Bill Date', default=date.today, validators=[DataRequired()])
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Bill amount must be greater than zero.")
    ])
    description = TextAreaField('Item Details / Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Invoice')


class VendorPaymentForm(FlaskForm):
    vendor_id = SelectField('Select Vendor', coerce=int, validators=[DataRequired()])
    date = DateField('Payment Date', default=date.today, validators=[DataRequired()])
    amount = FloatField('Paid Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Payment amount must be greater than zero.")
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
    description = TextAreaField('Payment Notes / Remarks', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Payment')
