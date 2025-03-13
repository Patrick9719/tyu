import os
import logging
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with a base class
class Base(DeclarativeBase):
    pass

# Create extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_object=Config):
    # Create the Flask application
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Set M-Pesa callback URL based on request host
    @app.before_request
    def before_request():
        if not app.config['MPESA_CALLBACK_URL'].startswith('https://'):
            host = request.host_url.rstrip('/')
            app.config['MPESA_CALLBACK_URL'] = f"{host}/api/mpesa/callback"

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Set login view
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Import models
    with app.app_context():
        from models import User, Package, Session, Payment, Voucher

        # Register blueprints
        from routes.main import main_bp
        from routes.auth import auth_bp
        from routes.admin import admin_bp
        from routes.payment import payment_bp
        from routes.api import api_bp
        from routes.family import family_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(payment_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(family_bp)

        # Create tables if they don't exist
        db.create_all()

        # Create default admin if it doesn't exist
        from utils.admin import create_default_admin
        create_default_admin()

        # Create default packages if they don't exist
        from utils.packages import create_default_packages
        create_default_packages()

    return app

# Create the app instance
app = create_app()

# Set up the user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))