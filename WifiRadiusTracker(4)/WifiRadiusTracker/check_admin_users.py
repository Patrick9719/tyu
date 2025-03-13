
from app import db, create_app
from models import User

app = create_app()
with app.app_context():
    # Find all admin users
    admin_users = User.query.filter_by(role='admin').all()
    
    print("===== ADMIN USERS =====")
    if not admin_users:
        print("No admin users found in the database.")
    else:
        print(f"Found {len(admin_users)} admin users:")
        for user in admin_users:
            print(f"- Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Role: {user.role}")
            print(f"  Active: {user.is_active}")
            print(f"  Created: {user.created_at}")
            print()
    
    # Check specific admin credentials
    usernames_to_check = ['admin', 'superadmin']
    for username in usernames_to_check:
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User '{username}' exists in the database.")
            # Test with default passwords for these users
            test_password = 'admin123' if username == 'admin' else 'superadmin123'
            if user.check_password(test_password):
                print(f"Password '{test_password}' is correct for user '{username}'")
            else:
                print(f"Password '{test_password}' is NOT correct for user '{username}'")
        else:
            print(f"User '{username}' does NOT exist in the database.")
        print()
