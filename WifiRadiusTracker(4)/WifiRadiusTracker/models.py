from datetime import datetime, timedelta
import secrets
import string
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    mac_address = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('Session', backref='user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    vouchers = db.relationship('Voucher', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    duration_hours = db.Column(db.Integer, nullable=False)
    data_limit_mb = db.Column(db.Integer, nullable=True)
    download_speed = db.Column(db.Integer, nullable=False)  # in kbps
    upload_speed = db.Column(db.Integer, nullable=False)    # in kbps
    is_active = db.Column(db.Boolean, default=True)
    is_family_plan = db.Column(db.Boolean, default=False)  # Whether this is a family plan
    device_limit = db.Column(db.Integer, default=1)        # Max devices for family plans
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('Session', backref='package', lazy='dynamic')
    vouchers = db.relationship('Voucher', backref='package', lazy='dynamic')
    
    def __repr__(self):
        return f'<Package {self.name}>'

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    mikrotik_session_id = db.Column(db.String(64), nullable=True)
    ip_address = db.Column(db.String(20), nullable=True)
    mac_address = db.Column(db.String(20), nullable=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    data_used_mb = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('voucher.id'), nullable=True)
    
    def __repr__(self):
        return f'<Session {self.id}>'
    
    def remaining_time(self):
        if not self.is_active or not self.end_time:
            return 0
        
        remaining = (self.end_time - datetime.utcnow()).total_seconds()
        return max(0, remaining)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='mpesa', nullable=False)
    transaction_id = db.Column(db.String(64), nullable=True)
    mpesa_receipt = db.Column(db.String(64), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to package
    package = db.relationship('Package', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.id}>'

class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    code = db.Column(db.String(16), unique=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sessions = db.relationship('Session', backref='voucher', lazy='dynamic')
    
    def __repr__(self):
        return f'<Voucher {self.code}>'
    
    @staticmethod
    def generate_code(length=8):
        """Generate a random voucher code"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def is_valid(self):
        """Check if voucher is valid and not expired"""
        if self.is_used:
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
            
        return True
class FamilyDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    mac_address = db.Column(db.String(20), nullable=False, unique=True)
    data_limit_mb = db.Column(db.Integer, nullable=True)
    data_used_mb = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    mikrotik_username = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FamilyDevice {self.name}>'
