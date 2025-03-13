from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, ValidationError
import re

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number (with country code)', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_phone(self, phone):
        # Simple validation to ensure phone has country code
        if not re.match(r'^\+?\d{10,15}$', phone.data):
            raise ValidationError('Invalid phone number format. Please include country code (e.g., +254XXX).')

class PackageSelectionForm(FlaskForm):
    package_id = SelectField('Select Package', coerce=int, validators=[DataRequired()])
    phone = StringField('M-Pesa Phone Number', validators=[DataRequired()])
    submit = SubmitField('Purchase Package')

class VoucherRedeemForm(FlaskForm):
    code = StringField('Voucher Code', validators=[DataRequired(), Length(min=8, max=16)])
    submit = SubmitField('Redeem Voucher')

class VoucherCreateForm(FlaskForm):
    package_id = SelectField('Package', coerce=int, validators=[DataRequired()])
    count = IntegerField('Number of Vouchers', validators=[DataRequired(), NumberRange(min=1, max=100)])
    expiry_days = IntegerField('Expiry Days', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Generate Vouchers')

class PackageForm(FlaskForm):
    name = StringField('Package Name', validators=[DataRequired(), Length(max=64)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    duration_hours = IntegerField('Duration (hours)', validators=[DataRequired(), NumberRange(min=1)])
    data_limit_mb = IntegerField('Data Limit (MB)', validators=[Optional(), NumberRange(min=0)])
    download_speed = IntegerField('Download Speed (kbps)', validators=[DataRequired(), NumberRange(min=64)])
    upload_speed = IntegerField('Upload Speed (kbps)', validators=[DataRequired(), NumberRange(min=64)])
    is_active = BooleanField('Active')
    submit = SubmitField('Save Package')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional()])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')], validators=[DataRequired()])
    is_active = BooleanField('Active')
    submit = SubmitField('Save User')

class SearchForm(FlaskForm):
    search = StringField('Search', validators=[Optional()])
    submit = SubmitField('Search')