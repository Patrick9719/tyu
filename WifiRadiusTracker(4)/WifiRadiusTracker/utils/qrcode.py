
import base64
import io
import logging
import qrcode
from flask import url_for

logger = logging.getLogger(__name__)

def generate_qr_code(data, size=10):
    """Generate a QR code as a base64 encoded image"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert image to base64 string
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None

def generate_voucher_qr(voucher_code, request_base_url=None):
    """Generate a QR code for voucher redemption"""
    if request_base_url:
        # If provided with request.base_url, use it to create an absolute URL
        redemption_url = f"{request_base_url.rstrip('/')}/redeem?code={voucher_code}"
    else:
        # Otherwise create a relative URL that will need to be resolved by the frontend
        redemption_url = f"/redeem?code={voucher_code}"
    
    return generate_qr_code(redemption_url)

def generate_session_qr(username, password, request_base_url=None):
    """Generate a QR code for direct login to MikroTik"""
    from utils.mikrotik import mikrotik
    login_url = mikrotik.generate_login_link(None, username, password)
    
    return generate_qr_code(login_url)
