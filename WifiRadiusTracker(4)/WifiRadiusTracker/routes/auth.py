import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from app import db
from models import User
from forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        logger.debug(f"Login attempt for username: {username}")
        
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            logger.debug(f"User '{username}' not found in database")
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if password is correct
        if not user.check_password(password):
            logger.debug(f"Incorrect password for user: {username}")
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user is active
        if not user.is_active:
            logger.debug(f"User account is inactive: {username}")
            flash('This account has been deactivated. Please contact support.', 'danger')
            return redirect(url_for('auth.login'))
        
        logger.debug(f"Successful login for user: {username}, role: {user.role}")
        
        # Log in the user
        login_user(user, remember=form.remember.data)
        
        # Redirect to the page they were trying to access
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            if user.is_admin():
                next_page = url_for('admin.index')
            else:
                next_page = url_for('main.dashboard')
                
        return redirect(next_page)
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email address.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        # Always show success message even if email not found (for security)
        if user:
            # In a real app, you would send an email with password reset link here
            logger.info(f"Password reset requested for {email}")
            
        flash('If your email is registered with us, you will receive a password reset link shortly.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    form = RegistrationForm(obj=current_user)
    
    if request.method == 'GET':
        # Don't show password on GET
        form.password.data = ''
        form.password2.data = ''
    
    if form.validate_on_submit():
        # Check if username or email already exists (if changed)
        if form.username.data != current_user.username and User.query.filter_by(username=form.username.data).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('auth.profile'))
        
        if form.email.data != current_user.email and User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email address.', 'danger')
            return redirect(url_for('auth.profile'))
        
        # Update user details
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        
        # Update password if provided
        if form.password.data:
            current_user.set_password(form.password.data)
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('profile.html', form=form)
