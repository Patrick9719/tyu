import logging
from app import db
from models import User, Package
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def create_default_admin():
    """Create a default admin user if no admin exists"""
    try:
        # Check if admin exists
        admin = User.query.filter_by(role='admin').first()
        if admin:
            logger.info("Admin user already exists")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')  # Default password, should be changed after first login
        
        db.session.add(admin)
        db.session.commit()
        
        logger.info("Default admin user created")
    except Exception as e:
        logger.error(f"Error creating default admin: {e}")
        db.session.rollback()
