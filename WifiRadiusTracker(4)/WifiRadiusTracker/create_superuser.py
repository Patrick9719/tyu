
from app import db
from models import User
from werkzeug.security import generate_password_hash

# Set your desired superuser credentials
username = "superadmin"
email = "superadmin@example.com"
password = "superadmin123"  # Change this to a secure password

# Check if user already exists
existing_user = User.query.filter_by(username=username).first()
if existing_user:
    print(f"User '{username}' already exists!")
else:
    # Create the superuser
    superuser = User(
        username=username,
        email=email,
        role='admin',
        is_active=True
    )
    superuser.set_password(password)
    
    # Save to database
    db.session.add(superuser)
    db.session.commit()
    
    print(f"Superuser '{username}' created successfully!")
    print(f"Email: {email}")
    print(f"Password: {password}")
