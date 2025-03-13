import os

class Config(object):
    """Base configuration."""
    APP_NAME = "MikroTik WiFi Hotspot"
    SECRET_KEY = os.environ.get("SESSION_SECRET", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///hotspot.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MikroTik API Configuration
    MIKROTIK_HOST = os.environ.get("MIKROTIK_HOST", "192.168.88.1")
    MIKROTIK_PORT = int(os.environ.get("MIKROTIK_PORT", 8728))
    MIKROTIK_USER = os.environ.get("MIKROTIK_USER", "admin")
    MIKROTIK_PASSWORD = os.environ.get("MIKROTIK_PASSWORD", "")

    # M-Pesa Configuration
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_API_URL = os.environ.get("MPESA_API_URL", "https://sandbox.safaricom.co.ke")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL", "https://example.com/api/mpesa/callback")

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

# Set the configuration
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

current_config = config[os.environ.get('FLASK_ENV', 'default')]