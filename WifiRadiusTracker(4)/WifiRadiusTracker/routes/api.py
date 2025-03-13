import logging
from flask import Blueprint, request, jsonify
from flask_login import current_user
from app import db
from models import User, Package, Session, Payment, Voucher
from utils.mpesa import mpesa
from utils.mikrotik import mikrotik
from utils.voucher import validate_voucher, use_voucher
from datetime import datetime, timedelta
import jwt
from config import current_config

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

def token_required(f):
    """Decorator for views that require a valid token"""
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, current_config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@api_bp.route('/packages', methods=['GET'])
def get_packages():
    """Get all active packages"""
    packages = Package.query.filter_by(is_active=True).all()
    
    result = []
    for package in packages:
        result.append({
            'id': package.id,
            'name': package.name,
            'description': package.description,
            'price': package.price,
            'duration_hours': package.duration_hours,
            'download_speed': package.download_speed,
            'upload_speed': package.upload_speed
        })
    
    return jsonify({'packages': result})

@api_bp.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa callback endpoint"""
    try:
        callback_data = request.get_json()
        logger.debug(f"M-Pesa callback data: {callback_data}")
        
        result = mpesa.process_callback(callback_data)
        
        if not result['success']:
            logger.error(f"Failed to process M-Pesa callback: {result['message']}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})
        
        # Get payment information
        checkout_request_id = result['checkout_request_id']
        payment_info = result['payment_info']
        
        # Find payment by transaction reference
        # In a real implementation, you would store the checkout_request_id with the payment
        payment = Payment.query.filter_by(
            status='pending',
            mpesa_receipt=payment_info.get('receipt_number')
        ).first()
        
        if not payment:
            logger.error(f"No payment found for receipt: {payment_info.get('receipt_number')}")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        # Update payment
        payment.status = 'completed'
        payment.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Get package and user
        package = Package.query.get(payment.package_id)
        user = User.query.get(payment.user_id)
        
        if not package or not user:
            logger.error(f"Missing package or user for payment {payment.id}")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        # Check for active session
        active_session = Session.query.filter_by(
            user_id=user.id,
            is_active=True
        ).first()
        
        if active_session:
            # Extend session
            new_end_time = active_session.end_time + timedelta(hours=package.duration_hours)
            active_session.end_time = new_end_time
            db.session.commit()
            logger.info(f"Extended session {active_session.id} for user {user.id}")
        else:
            # Create session
            session = Session(
                user_id=user.id,
                package_id=package.id,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=package.duration_hours),
                is_active=True
            )
            db.session.add(session)
            db.session.commit()
            logger.info(f"Created session {session.id} for user {user.id}")
        
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        logger.error(f"Error in M-Pesa callback: {e}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Error processing callback'})

@api_bp.route('/voucher/validate', methods=['POST'])
def validate_voucher_api():
    """Validate a voucher code"""
    data = request.get_json()
    
    if not data or 'code' not in data:
        return jsonify({'success': False, 'message': 'Voucher code is required'}), 400
    
    code = data['code'].strip().upper()
    result = validate_voucher(code)
    
    if not result['valid']:
        return jsonify({'success': False, 'message': result['message']}), 400
    
    voucher = result['voucher']
    package = result['package']
    
    return jsonify({
        'success': True,
        'voucher': {
            'code': voucher.code,
            'expires_at': voucher.expires_at.isoformat() if voucher.expires_at else None,
        },
        'package': {
            'id': package.id,
            'name': package.name,
            'duration_hours': package.duration_hours,
            'download_speed': package.download_speed,
            'upload_speed': package.upload_speed
        }
    })

@api_bp.route('/voucher/redeem', methods=['POST'])
def redeem_voucher_api():
    """Redeem a voucher code"""
    data = request.get_json()
    
    if not data or 'code' not in data:
        return jsonify({'success': False, 'message': 'Voucher code is required'}), 400
    
    code = data['code'].strip().upper()
    mac_address = data.get('mac_address')
    
    # If user is authenticated, use their ID
    user_id = current_user.id if current_user.is_authenticated else None
    
    # Use voucher
    result = use_voucher(code, user_id, mac_address)
    
    if not result['success']:
        return jsonify({'success': False, 'message': result['message']}), 400
    
    voucher = result['voucher']
    package = result['package']
    
    # Create session
    session = Session(
        user_id=voucher.user_id if voucher.user_id else 1,  # Use admin user ID if no user
        package_id=package.id,
        voucher_id=voucher.id,
        mac_address=mac_address,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=package.duration_hours),
        is_active=True
    )
    db.session.add(session)
    db.session.commit()
    
    # Create MikroTik user
    username = f"voucher_{voucher.code}"
    password = voucher.code
    rate_limit = f"{package.download_speed}k/{package.upload_speed}k"
    
    mikrotik.add_user(
        username=username,
        password=password,
        limit_uptime=f"{package.duration_hours}:00:00",
        rate_limit=rate_limit
    )
    
    # Generate login URL
    login_url = mikrotik.generate_login_link(mac_address, username, password)
    
    return jsonify({
        'success': True,
        'message': 'Voucher redeemed successfully',
        'session': {
            'id': session.id,
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat(),
            'duration_hours': package.duration_hours
        },
        'login_url': login_url
    })

@api_bp.route('/session/status', methods=['GET'])
def session_status():
    """Get status of current session based on IP or MAC address"""
    # Get client IP and MAC address
    ip_address = request.remote_addr
    mac_address = request.args.get('mac')
    
    # Try to find session by MAC address first
    session = None
    if mac_address:
        session = Session.query.filter_by(
            mac_address=mac_address,
            is_active=True
        ).order_by(Session.start_time.desc()).first()
    
    # If not found, try by IP address
    if not session:
        session = Session.query.filter_by(
            ip_address=ip_address,
            is_active=True
        ).order_by(Session.start_time.desc()).first()
    
    # If session found, return details
    if session:
        remaining_seconds = max(0, (session.end_time - datetime.utcnow()).total_seconds())
        hours, remainder = divmod(int(remaining_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Get bandwidth usage from MikroTik if possible
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
            'session': {
                'id': session.id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'remaining_time': {
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds,
                    'total_seconds': remaining_seconds
                },
                'package': {
                    'id': session.package.id,
                    'name': session.package.name,
                    'download_speed': session.package.download_speed,
                    'upload_speed': session.package.upload_speed
                },
                'usage': {
                    'download': usage['bytes_in'],
                    'upload': usage['bytes_out']
                }
            }
        })
    else:
        return jsonify({
            'success': True,
            'active': False
        })

@api_bp.route('/session/disconnect', methods=['POST'])
def disconnect_session():
    """Disconnect current session"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'success': False, 'message': 'Session ID is required'}), 400
    
    # Get session
    session = Session.query.get(session_id)
    
    if not session:
        return jsonify({'success': False, 'message': 'Session not found'}), 404
    
    # Check if user is authorized (is admin or owns the session)
    if current_user.is_authenticated and (current_user.is_admin() or session.user_id == current_user.id):
        pass
    else:
        # Check if request comes from the same IP address
        if request.remote_addr != session.ip_address:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Disconnect from MikroTik
    if session.voucher_id:
        voucher = session.voucher
        username = f"voucher_{voucher.code}"
        mikrotik.disconnect_user(username)
    
    # Update session
    session.is_active = False
    session.end_time = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Session disconnected successfully'
    })
