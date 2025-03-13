import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import current_user, login_required
from app import db
from models import Payment, Package, Session as UserSession, User
from utils.mpesa import mpesa
from utils.mikrotik import mikrotik
from datetime import datetime, timedelta

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')
logger = logging.getLogger(__name__)

@payment_bp.route('/status/<int:payment_id>')
def status(payment_id):
    """Payment status page"""
    payment = Payment.query.get_or_404(payment_id)

    # Check if payment belongs to current user or user is admin
    if current_user.is_authenticated and (payment.user_id == current_user.id or current_user.is_admin()):
        pass
    elif 'transaction' in session and session['transaction'].get('reference') == payment.transaction_id:
        # Anonymous user with matching transaction in session
        pass
    else:
        flash('You do not have permission to view this payment', 'danger')
        return redirect(url_for('main.index'))

    return render_template('payment/status.html', payment=payment)

@payment_bp.route('/check/<int:payment_id>', endpoint='check_status')
def check_status(payment_id):
    """AJAX endpoint to check payment status"""
    payment = Payment.query.get_or_404(payment_id)

    # Check if payment belongs to current user or user is admin
    if current_user.is_authenticated and (payment.user_id == current_user.id or current_user.is_admin()):
        pass
    elif 'transaction' in session and session['transaction'].get('reference') == payment.transaction_id:
        # Anonymous user with matching transaction in session
        pass
    else:
        return jsonify({
            'success': False,
            'message': 'Unauthorized'
        }), 403

    # If payment is already completed or failed, return current status
    if payment.status in ['completed', 'failed']:
        return jsonify({
            'success': True,
            'status': payment.status,
            'message': 'Payment is ' + payment.status
        })

    # Check with M-Pesa for status update
    if 'checkout_request_id' in session:
        result = mpesa.check_payment_status(session['checkout_request_id'])

        if result['success']:
            if result['paid']:
                # Update payment status
                payment.status = 'completed'
                payment.updated_at = datetime.utcnow()
                db.session.commit()

                # Create or extend session
                process_successful_payment(payment)

                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'message': 'Payment completed successfully',
                    'redirect': url_for('main.dashboard')
                })
            else:
                return jsonify({
                    'success': True,
                    'status': 'pending',
                    'message': result['message']
                })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            })
    else:
        return jsonify({
            'success': False,
            'message': 'No checkout request ID found'
        })

@payment_bp.route('/callback', methods=['POST'])
def callback():
    """M-Pesa callback endpoint"""
    # Parse callback data
    try:
        callback_data = request.get_json()
        result = mpesa.process_callback(callback_data)

        if not result['success']:
            logger.error(f"Failed to process M-Pesa callback: {result['message']}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})

        # Get payment by checkout request ID
        checkout_request_id = result['checkout_request_id']
        payment_info = result['payment_info']

        # Find payment with matching transaction ID
        payments = Payment.query.filter_by(status='pending').all()
        payment = None

        for p in payments:
            if 'transaction' in session and session['transaction'].get('reference') == p.transaction_id:
                payment = p
                break

        if not payment:
            logger.error(f"No pending payment found for callback: {checkout_request_id}")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})

        # Update payment details
        payment.status = 'completed'
        payment.mpesa_receipt = payment_info.get('receipt_number')
        payment.updated_at = datetime.utcnow()
        db.session.commit()

        # Create or extend session
        process_successful_payment(payment)

        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        logger.error(f"Error processing M-Pesa callback: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})

def process_successful_payment(payment):
    """Process a successful payment by creating or extending a session"""
    try:
        # Get package details
        package = Package.query.get(payment.package_id)
        if not package:
            logger.error(f"Package not found for payment {payment.id}")
            return False

        # Get user
        user = User.query.get(payment.user_id)
        if not user:
            logger.error(f"User not found for payment {payment.id}")
            return False

        # Get client IP and MAC address
        ip_address = request.remote_addr
        mac_address = mikrotik.extract_mac_from_ip(ip_address) or user.mac_address

        # Check for existing active session
        active_session = UserSession.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(UserSession.start_time.desc()).first()

        if active_session:
            # Extend existing session
            duration = timedelta(hours=package.duration_hours)
            active_session.end_time = active_session.end_time + duration
            db.session.commit()

            logger.info(f"Extended session {active_session.id} by {package.duration_hours} hours")
        else:
            # Create new session
            new_session = UserSession(
                user_id=user.id,
                package_id=package.id,
                ip_address=ip_address,
                mac_address=mac_address,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=package.duration_hours),
                is_active=True
            )
            db.session.add(new_session)
            db.session.commit()

            # Create MikroTik user and login
            rate_limit = f"{package.download_speed}k/{package.upload_speed}k"
            username = f"user_{user.id}"
            password = f"pass_{user.id}"

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

            logger.info(f"Created new session {new_session.id} for user {user.id}")

        return True
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        db.session.rollback()
        return False