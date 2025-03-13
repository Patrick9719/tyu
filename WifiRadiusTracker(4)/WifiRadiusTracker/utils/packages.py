import logging
from app import db
from models import Package

logger = logging.getLogger(__name__)

def create_default_packages():
    """Create default packages if none exist"""
    try:
        # Check if packages exist
        if Package.query.count() > 0:
            logger.info("Packages already exist")
            return
        
        # Define default packages
        default_packages = [
            {
                'name': 'Basic',
                'description': 'Basic internet access for browsing and email',
                'price': 50,
                'duration_hours': 1,
                'download_speed': 512,  # 512 kbps
                'upload_speed': 256     # 256 kbps
            },
            {
                'name': 'Standard',
                'description': 'Standard internet access for streaming and downloads',
                'price': 100,
                'duration_hours': 3,
                'download_speed': 1024,  # 1 Mbps
                'upload_speed': 512      # 512 kbps
            },
            {
                'name': 'Premium',
                'description': 'Premium internet access for HD streaming and fast downloads',
                'price': 200,
                'duration_hours': 6,
                'download_speed': 2048,  # 2 Mbps
                'upload_speed': 1024     # 1 Mbps
            },
            {
                'name': 'Daily',
                'description': 'Full day of internet access',
                'price': 300,
                'duration_hours': 24,
                'download_speed': 1024,  # 1 Mbps
                'upload_speed': 512      # 512 kbps
            },
            {
                'name': 'Weekly',
                'description': 'Full week of internet access',
                'price': 1500,
                'duration_hours': 168,  # 7 days
                'download_speed': 1024,  # 1 Mbps
                'upload_speed': 512      # 512 kbps
            }
        ]
        
        # Create packages
        for package_data in default_packages:
            package = Package(**package_data)
            db.session.add(package)
        
        db.session.commit()
        logger.info(f"Created {len(default_packages)} default packages")
    except Exception as e:
        logger.error(f"Error creating default packages: {e}")
        db.session.rollback()
