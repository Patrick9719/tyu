import random
import string
import logging
from datetime import datetime, timedelta
from models import Voucher, User, Package
from app import db

logger = logging.getLogger(__name__)

def generate_voucher_code(length=8):
    """Generate a random voucher code with specified length"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_voucher(package_id, expiry_days=30, user_id=None):
    """Create a new voucher for a specified package"""
    try:
        # Validate package
        package = Package.query.get(package_id)
        if not package:
            logger.error(f"Package with ID {package_id} not found")
            return None
        
        # Generate unique code
        code = generate_voucher_code()
        while Voucher.query.filter_by(code=code).first():
            code = generate_voucher_code()
        
        # Calculate expiry date
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        
        # Create voucher
        voucher = Voucher(
            package_id=package_id,
            code=code,
            expires_at=expires_at,
            user_id=user_id
        )
        
        db.session.add(voucher)
        db.session.commit()
        
        return voucher
    except Exception as e:
        logger.error(f"Error creating voucher: {e}")
        db.session.rollback()
        return None

def create_vouchers_batch(package_id, count=10, expiry_days=30):
    """Create a batch of vouchers for a specified package"""
    vouchers = []
    
    try:
        for _ in range(count):
            voucher = create_voucher(package_id, expiry_days)
            if voucher:
                vouchers.append(voucher)
        
        return vouchers
    except Exception as e:
        logger.error(f"Error creating voucher batch: {e}")
        return vouchers

def validate_voucher(code):
    """Validate a voucher code and return the voucher if valid"""
    try:
        voucher = Voucher.query.filter_by(code=code).first()
        
        if not voucher:
            return {
                "valid": False,
                "message": "Invalid voucher code"
            }
        
        if voucher.is_used:
            return {
                "valid": False,
                "message": "Voucher has already been used"
            }
        
        if voucher.expires_at and voucher.expires_at < datetime.utcnow():
            return {
                "valid": False,
                "message": "Voucher has expired"
            }
        
        # Voucher is valid
        return {
            "valid": True,
            "voucher": voucher,
            "package": voucher.package
        }
    except Exception as e:
        logger.error(f"Error validating voucher: {e}")
        return {
            "valid": False,
            "message": f"Error validating voucher: {str(e)}"
        }

def use_voucher(code, user_id=None, mac_address=None):
    """Mark a voucher as used by a user"""
    try:
        validation = validate_voucher(code)
        if not validation["valid"]:
            return validation
        
        voucher = validation["voucher"]
        
        # Update voucher status
        voucher.is_used = True
        voucher.used_at = datetime.utcnow()
        
        if user_id:
            voucher.user_id = user_id
        
        db.session.commit()
        
        return {
            "success": True,
            "voucher": voucher,
            "package": voucher.package,
            "message": "Voucher used successfully"
        }
    except Exception as e:
        logger.error(f"Error using voucher: {e}")
        db.session.rollback()
        return {
            "success": False,
            "message": f"Error using voucher: {str(e)}"
        }

def get_active_vouchers():
    """Get all active (unused and not expired) vouchers"""
    try:
        now = datetime.utcnow()
        return Voucher.query.filter_by(is_used=False).filter(
            (Voucher.expires_at.is_(None)) | (Voucher.expires_at > now)
        ).all()
    except Exception as e:
        logger.error(f"Error getting active vouchers: {e}")
        return []

def get_user_vouchers(user_id):
    """Get all vouchers used by a specific user"""
    try:
        return Voucher.query.filter_by(user_id=user_id).all()
    except Exception as e:
        logger.error(f"Error getting user vouchers: {e}")
        return []
