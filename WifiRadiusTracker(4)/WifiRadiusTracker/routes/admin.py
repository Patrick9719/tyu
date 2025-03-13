import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from app import db
from models import User, Package, Session, Payment, Voucher
from forms import PackageForm, UserForm, VoucherCreateForm, SearchForm
from utils.voucher import create_vouchers_batch
from utils.mikrotik import mikrotik

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

# Admin access required decorator
def admin_required(f):
    """Decorator for views that require admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)

@admin_bp.route('/')
@admin_required
def index():
    """Admin dashboard with overview statistics"""
    # Get counts
    active_users_count = Session.query.filter_by(is_active=True).count()
    user_count = User.query.filter_by(role='user').count()

    # Get revenue statistics
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    start_of_week = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    start_of_month = datetime.combine(datetime(today.year, today.month, 1), datetime.min.time())

    daily_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= start_of_day
    ).scalar() or 0

    weekly_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= start_of_week
    ).scalar() or 0

    monthly_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= start_of_month
    ).scalar() or 0

    # Get recent payments
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()

    # Get active sessions
    active_sessions = Session.query.filter_by(is_active=True).order_by(Session.start_time.desc()).all()

    # Get MikroTik active users
    mikrotik_users = mikrotik.get_active_users()

    return render_template(
        'admin/index.html',
        active_users_count=active_users_count,
        user_count=user_count,
        daily_revenue=daily_revenue,
        weekly_revenue=weekly_revenue,
        monthly_revenue=monthly_revenue,
        recent_payments=recent_payments,
        active_sessions=active_sessions,
        mikrotik_users=mikrotik_users
    )

@admin_bp.route('/users')
@admin_required
def users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    search_form = SearchForm()
    search_term = request.args.get('search', '')

    query = User.query
    if search_term:
        query = query.filter(
            (User.username.like(f'%{search_term}%')) |
            (User.email.like(f'%{search_term}%')) |
            (User.phone.like(f'%{search_term}%'))
        )

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('admin/users.html', users=users, search_form=search_form, search_term=search_term)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def new_user():
    """Create a new user"""
    form = UserForm()

    if form.validate_on_submit():
        # Check if username or email already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'danger')
            return render_template('admin/user_form.html', form=form, title='New User')

        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'danger')
            return render_template('admin/user_form.html', form=form, title='New User')

        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            role=form.role.data,
            is_active=form.is_active.data
        )
        # Set default password
        user.set_password('password123')

        db.session.add(user)
        db.session.commit()

        flash('User created successfully', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, title='New User')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit a user"""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        # Check if username or email already exists (if changed)
        if form.username.data != user.username and User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User')

        if form.email.data != user.email and User.query.filter_by(email=form.email.data).first():
            flash('Email already exists', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User')

        # Update user
        user.username = form.username.data
        user.email = form.email.data
        user.phone = form.phone.data
        user.role = form.role.data
        user.is_active = form.is_active.data

        db.session.commit()

        flash('User updated successfully', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, title='Edit User', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting self
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.users'))

    # Delete associated data
    # Sessions will be cascade deleted due to foreign key relationship

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/packages')
@admin_required
def packages():
    """Manage packages"""
    packages = Package.query.order_by(Package.price).all()
    return render_template('admin/packages.html', packages=packages)

@admin_bp.route('/packages/new', methods=['GET', 'POST'])
@admin_required
def new_package():
    """Create a new package"""
    form = PackageForm()

    if form.validate_on_submit():
        package = Package(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            duration_hours=form.duration_hours.data,
            data_limit_mb=form.data_limit_mb.data,
            download_speed=form.download_speed.data,
            upload_speed=form.upload_speed.data,
            is_active=form.is_active.data
        )

        db.session.add(package)
        db.session.commit()

        flash('Package created successfully', 'success')
        return redirect(url_for('admin.packages'))

    return render_template('admin/package_form.html', form=form, title='New Package')

@admin_bp.route('/packages/<int:package_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_package(package_id):
    """Edit a package"""
    package = Package.query.get_or_404(package_id)
    form = PackageForm(obj=package)

    if form.validate_on_submit():
        package.name = form.name.data
        package.description = form.description.data
        package.price = form.price.data
        package.duration_hours = form.duration_hours.data
        package.data_limit_mb = form.data_limit_mb.data
        package.download_speed = form.download_speed.data
        package.upload_speed = form.upload_speed.data
        package.is_active = form.is_active.data

        db.session.commit()

        flash('Package updated successfully', 'success')
        return redirect(url_for('admin.packages'))

    return render_template('admin/package_form.html', form=form, title='Edit Package', package=package)

@admin_bp.route('/packages/<int:package_id>/delete', methods=['POST'])
@admin_required
def delete_package(package_id):
    """Delete a package"""
    package = Package.query.get_or_404(package_id)

    # Check if package is in use
    if Session.query.filter_by(package_id=package_id).count() > 0:
        flash('Cannot delete package that is in use', 'danger')
        return redirect(url_for('admin.packages'))

    db.session.delete(package)
    db.session.commit()

    flash('Package deleted successfully', 'success')
    return redirect(url_for('admin.packages'))

@admin_bp.route('/vouchers')
@admin_required
def vouchers():
    """Manage vouchers"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    search_form = SearchForm()
    search_term = request.args.get('search', '')

    query = Voucher.query

    # Filter by status
    if status == 'active':
        query = query.filter_by(is_used=False)
    elif status == 'used':
        query = query.filter_by(is_used=True)

    # Filter by search term
    if search_term:
        query = query.filter(Voucher.code.like(f'%{search_term}%'))

    vouchers = query.order_by(Voucher.created_at.desc()).paginate(page=page, per_page=20)

    return render_template(
        'admin/vouchers.html', 
        vouchers=vouchers, 
        status=status, 
        search_form=search_form, 
        search_term=search_term
    )

@admin_bp.route('/vouchers/generate', methods=['GET', 'POST'])
@admin_required
def generate_vouchers():
    """Generate new vouchers"""
    form = VoucherCreateForm()
    form.package_id.choices = [(p.id, p.name) for p in Package.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        vouchers = create_vouchers_batch(
            package_id=form.package_id.data,
            count=form.count.data,
            expiry_days=form.expiry_days.data
        )

        if vouchers:
            flash(f'Successfully generated {len(vouchers)} vouchers', 'success')
            return redirect(url_for('admin.vouchers'))
        else:
            flash('Failed to generate vouchers', 'danger')

    return render_template('admin/voucher_form.html', form=form)

@admin_bp.route('/vouchers/<int:voucher_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_voucher(voucher_id):
    """Delete a voucher"""
    voucher = Voucher.query.get_or_404(voucher_id)

    try:
        db.session.delete(voucher)
        db.session.commit()
        flash('Voucher deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting voucher: {str(e)}', 'danger')

    return redirect(url_for('admin.vouchers'))

@admin_bp.route('/vouchers/qrcode/<string:code>')
@login_required
@admin_required
def voucher_qrcode(code):
    """Generate QR code for a voucher"""
    from utils.qrcode import generate_voucher_qr

    voucher = Voucher.query.filter_by(code=code).first_or_404()

    qr_code = generate_voucher_qr(voucher.code, request.base_url)

    return jsonify({
        'success': True,
        'qr_code': qr_code,
        'code': voucher.code
    })

@admin_bp.route('/payments')
@admin_required
def payments():
    """View payment history"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    search_form = SearchForm()
    search_term = request.args.get('search', '')

    query = Payment.query

    # Filter by status
    if status != 'all':
        query = query.filter_by(status=status)

    # Filter by search term
    if search_term:
        query = query.filter(
            (Payment.transaction_id.like(f'%{search_term}%')) |
            (Payment.mpesa_receipt.like(f'%{search_term}%')) |
            (Payment.phone_number.like(f'%{search_term}%'))
        )

    payments = query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=20)

    return render_template(
        'admin/payments.html', 
        payments=payments, 
        status=status, 
        search_form=search_form, 
        search_term=search_term
    )

@admin_bp.route('/sessions')
@admin_required
def sessions():
    """View all sessions"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    search_form = SearchForm()
    search_term = request.args.get('search', '')

    query = Session.query.join(User)

    # Filter by status
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    # Filter by search term
    if search_term:
        query = query.filter(
            (User.username.like(f'%{search_term}%')) |
            (Session.ip_address.like(f'%{search_term}%')) |
            (Session.mac_address.like(f'%{search_term}%'))
        )

    sessions = query.order_by(Session.start_time.desc()).paginate(page=page, per_page=20)

    return render_template(
        'admin/sessions.html', 
        sessions=sessions, 
        status=status, 
        search_form=search_form, 
        search_term=search_term
    )

@admin_bp.route('/sessions/<int:session_id>/disconnect', methods=['POST'])
@admin_required
def disconnect_session(session_id):
    """Disconnect a user session"""
    session = Session.query.get_or_404(session_id)

    if not session.is_active:
        flash('Session is already inactive', 'warning')
        return redirect(url_for('admin.sessions'))

    # Disconnect from MikroTik
    if session.voucher_id:
        voucher = session.voucher
        username = f"voucher_{voucher.code}"
        mikrotik.disconnect_user(username)

    # Update session status
    session.is_active = False
    session.end_time = datetime.utcnow()
    db.session.commit()

    flash('Session disconnected successfully', 'success')
    return redirect(url_for('admin.sessions'))

@admin_bp.route('/bandwidth')
@admin_required
def bandwidth_management():
    """Manage default and user-specific bandwidth settings"""
    # Get all users
    users = User.query.filter_by(role='user').order_by(User.username).all()
    
    return render_template(
        'admin/bandwidth.html',
        users=users
    )

@admin_bp.route('/bandwidth/default', methods=['POST'])
@admin_required
def set_default_bandwidth():
    """Set default bandwidth limits for all users"""
    # Get values from form
    default_download = request.form.get('default_download', type=int)
    default_upload = request.form.get('default_upload', type=int)
    
    if default_download and default_upload:
        # Call MikroTik function to set default bandwidth
        success = mikrotik.set_default_bandwidth(default_download, default_upload)
        
        if success:
            flash('Default bandwidth settings updated', 'success')
        else:
            flash('Failed to update default bandwidth on MikroTik', 'danger')
    else:
        flash('Invalid bandwidth values', 'danger')
        
    return redirect(url_for('admin.bandwidth_management'))

@admin_bp.route('/bandwidth/user/<int:user_id>', methods=['POST'])
@admin_required
def set_user_bandwidth(user_id):
    """Set bandwidth limits for a specific user"""
    user = User.query.get_or_404(user_id)
    
    # Get values from form
    download_speed = request.form.get('download_speed', type=int)
    upload_speed = request.form.get('upload_speed', type=int)
    
    if download_speed and upload_speed:
        # Call MikroTik function to set bandwidth
        success = mikrotik.set_user_bandwidth(user.username, download_speed, upload_speed)
        
        if success:
            flash(f'Bandwidth updated for user {user.username}', 'success')
        else:
            flash('Failed to update bandwidth on MikroTik', 'danger')
    else:
        flash('Invalid bandwidth values', 'danger')
        
    return redirect(url_for('admin.bandwidth_management'))

@admin_bp.route('/reports')
@admin_required
def reports():
    """View reports and statistics"""
    # Get date range from request
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Default to the past 30 days
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)

    # Parse dates if provided
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format', 'warning')

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid end date format', 'warning')

    # Ensure end date is not before start date
    if end_date < start_date:
        end_date = start_date

    # Convert to datetime for queries
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get payment data for the period
    payments = Payment.query.filter(
        Payment.created_at.between(start_datetime, end_datetime),
        Payment.status == 'completed'
    ).all()

    # Calculate total revenue
    total_revenue = sum(payment.amount for payment in payments)

    # Get daily revenue data for chart
    daily_revenue_data = []
    current_date = start_date
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())

        day_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.created_at.between(day_start, day_end),
            Payment.status == 'completed'
        ).scalar() or 0

        daily_revenue_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'revenue': float(day_revenue)
        })

        current_date += timedelta(days=1)

    # Get package popularity data
    package_data = db.session.query(
        Package.name,
        db.func.count(Payment.id).label('count'),
        db.func.sum(Payment.amount).label('revenue')
    ).join(
        Payment, Payment.package_id == Package.id
    ).filter(
        Payment.created_at.between(start_datetime, end_datetime),
        Payment.status == 'completed'
    ).group_by(
        Package.id
    ).all()

    package_popularity = [{
        'name': name,
        'count': count,
        'revenue': float(revenue)
    } for name, count, revenue in package_data]

    # Get session data
    sessions = Session.query.filter(
        Session.start_time.between(start_datetime, end_datetime)
    ).all()

    total_sessions = len(sessions)
    active_sessions = sum(1 for s in sessions if s.is_active)

    return render_template(
        'admin/reports.html',
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        daily_revenue_data=daily_revenue_data,
        package_popularity=package_popularity,
        total_sessions=total_sessions,
        active_sessions=active_sessions
    )