import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_required
from app import db
from models import Package, Payment, Session as UserSession, User
from forms import PackageSelectionForm, VoucherRedeemForm
from utils.mpesa import mpesa
from utils.mikrotik import mikrotik
from utils.voucher import validate_voucher, use_voucher
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Homepage with package selection"""
    packages = Package.query.filter_by(is_active=True).all()
    form = PackageSelectionForm()
    form.package_id.choices = [(p.id, f"{p.name} - KES {p.price} ({p.duration_hours} hours)") for p in packages]
    
    # If user is logged in, pre-fill phone number
    if current_user.is_authenticated and current_user.phone:
        form.phone.data = current_user.phone
    
    # Get user's active session if authenticated
    active_session = None
    if current_user.is_authenticated:
        active_session = UserSession.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).order_by(UserSession.start_time.desc()).first()
    
    voucher_form = VoucherRedeemForm()
    
    return render_template(
        'index.html', 
        packages=packages, 
        form=form, 
        voucher_form=voucher_form,
        active_session=active_session
    )

@main_bp.route('/packages')
def packages():
    """View all available packages"""
    packages = Package.query.filter_by(is_active=True).all()
    return render_template('packages.html', packages=packages)

@main_bp.route('/purchase', methods=['POST'])
def purchase():
    """Handle package purchase via M-Pesa"""
    form = PackageSelectionForm()
    packages = Package.query.filter_by(is_active=True).all()
    form.package_id.choices = [(p.id, p.name) for p in packages]
    
    if form.validate_on_submit():
        package_id = form.package_id.data
        phone_number = form.phone.data
        
        # Get package details
        package = Package.query.get(package_id)
        if not package:
            flash('Invalid package selected', 'danger')
            return redirect(url_for('main.index'))
        
        # Store transaction details in session for callback
        transaction_ref = f"WIFI{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session['transaction'] = {
            'package_id': package_id,
            'phone': phone_number,
            'amount': package.price,
            'reference': transaction_ref,
            'user_id': current_user.id if current_user.is_authenticated else None
        }
        
        # Initiate M-Pesa STK push
        result = mpesa.initiate_stk_push(
            phone_number=phone_number,
            amount=package.price,
            account_reference=transaction_ref,
            transaction_desc=f"Payment for {package.name} package"
        )
        
        if result['success']:
            # Store checkout request ID for verification
            session['checkout_request_id'] = result['checkout_request_id']
            
            # Create payment record
            payment = Payment(
                user_id=current_user.id if current_user.is_authenticated else 1,  # Use admin user ID for anonymous
                package_id=package_id,
                amount=package.price,
                payment_method='mpesa',
                transaction_id=transaction_ref,
                phone_number=phone_number,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            flash('Payment initiated. Please check your phone to complete the transaction.', 'info')
            return redirect(url_for('payment.status', payment_id=payment.id))
        else:
            flash(f'Failed to initiate payment: {result["message"]}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('main.index'))

@main_bp.route('/redeem', methods=['POST'])
def redeem_voucher():
    """Redeem a voucher code"""
    form = VoucherRedeemForm()
    
    if form.validate_on_submit():
        code = form.code.data.strip().upper()
        
        # Validate voucher
        validation = validate_voucher(code)
        if not validation['valid']:
            flash(validation['message'], 'danger')
            return redirect(url_for('main.index'))
        
        # Use voucher
        user_id = current_user.id if current_user.is_authenticated else None
        
        # Get client IP and MAC address
        ip_address = request.remote_addr
        mac_address = mikrotik.extract_mac_from_ip(ip_address)
        
        # If not authenticated, create a temporary user
        if not user_id:
            temp_user = User(
                username=f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                email=f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com",
                mac_address=mac_address
            )
            db.session.add(temp_user)
            db.session.commit()
            user_id = temp_user.id
        
        # Use the voucher
        result = use_voucher(code, user_id, mac_address)
        if not result['success']:
            flash(result['message'], 'danger')
            return redirect(url_for('main.index'))
        
        voucher = result['voucher']
        package = result['package']
        
        # Create user session
        user_session = UserSession(
            user_id=user_id,
            package_id=package.id,
            ip_address=ip_address,
            mac_address=mac_address,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=package.duration_hours),
            is_active=True,
            voucher_id=voucher.id
        )
        db.session.add(user_session)
        db.session.commit()
        
        # Create MikroTik user and login
        rate_limit = f"{package.download_speed}k/{package.upload_speed}k"
        username = f"voucher_{voucher.code}"
        password = voucher.code
        
        # Create profile if it doesn't exist
        profile_name = f"package_{package.id}"
        mikrotik.create_user_profile(profile_name, rate_limit)
        
        # Add user to MikroTik
        mikrotik.add_user(
            username=username,
            password=password,
            limit_uptime=f"{package.duration_hours}:00:00",
            rate_limit=rate_limit
        )
        
        # Generate login URL
        login_url = mikrotik.generate_login_link(mac_address, username, password)
        
        flash(f'Voucher redeemed successfully! Your session is active for {package.duration_hours} hours.', 'success')
        return redirect(login_url)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('main.index'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing active sessions, history and analytics"""
    # Get active session
    active_session = UserSession.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).order_by(UserSession.start_time.desc()).first()
    
    # Get session history
    sessions = UserSession.query.filter_by(
        user_id=current_user.id
    ).order_by(UserSession.start_time.desc()).limit(10).all()
    
    # Get payment history
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).limit(10).all()
    
    # Import analytics utils
    from utils.analytics import get_user_usage_stats, get_usage_history
    
    # Get usage statistics
    usage_stats = get_user_usage_stats(current_user.id)
    
    # Get usage history for charts
    usage_history = get_usage_history(current_user.id)
    
    return render_template(
        'dashboard.html',
        active_session=active_session,
        sessions=sessions,
        payments=payments,
        usage_stats=usage_stats,
        usage_history=usage_history
    )

@main_bp.route('/session/<int:session_id>/disconnect')
@login_required
def disconnect_session(session_id):
    """Disconnect an active session"""
    session = UserSession.query.get_or_404(session_id)
    
    # Ensure user owns the session or is admin
    if session.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to disconnect this session', 'danger')
        return redirect(url_for('main.dashboard'))
    
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
    return redirect(url_for('main.dashboard'))

@main_bp.route('/session/<int:session_id>/status')
def session_status(session_id):
    """Get session status as JSON for AJAX updates"""
    session = UserSession.query.get_or_404(session_id)
    
    # Check if session belongs to current user or user is admin
    if not current_user.is_authenticated or (session.user_id != current_user.id and not current_user.is_admin()):
        return jsonify({
            'success': False,
            'message': 'Unauthorized'
        }), 403
    
    # Get session details
    if session.is_active and session.end_time > datetime.utcnow():
        remaining_seconds = (session.end_time - datetime.utcnow()).total_seconds()
        hours, remainder = divmod(int(remaining_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Get usage info from MikroTik if possible
        usage = {'bytes_in': 0, 'bytes_out': 0}
        if session.voucher_id:
            voucher = session.voucher
            username = f"voucher_{voucher.code}"
            mikrotik_usage = mikrotik.get_user_traffic(username)
            if mikrotik_usage:
                usage = mikrotik_usage
        
        return jsonify({
            'success': True,
            'active': True,
            'remaining_time': {
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'total_seconds': remaining_seconds
            },
            'usage': {
                'download': usage['bytes_in'],
                'upload': usage['bytes_out'],
                'download_formatted': format_bytes(usage['bytes_in']),
                'upload_formatted': format_bytes(usage['bytes_out'])
            },
            'package': {
                'name': session.package.name,
                'download_speed': session.package.download_speed,
                'upload_speed': session.package.upload_speed
            }
        })
    else:
        return jsonify({
            'success': True,
            'active': False
        })

def format_bytes(bytes):
    """Format bytes to human-readable format"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1048576:
        return f"{bytes/1024:.2f} KB"
    elif bytes < 1073741824:
        return f"{bytes/1048576:.2f} MB"
    else:
        return f"{bytes/1073741824:.2f} GB"
