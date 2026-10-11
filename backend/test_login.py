import os
from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models.auth import User
from werkzeug.security import check_password_hash

load_dotenv('backend/.env')
app = create_app()

with app.app_context():
    user = User.query.filter_by(email='chinnufolio@gmail.com').first()
    if user:
        print(f"User found: {user.email}")
        print(f"Is active: {user.is_active}")
        print(f"Email verified: {user.is_email_verified}")
        is_correct = check_password_hash(user.password_hash, 'chinnu')
        print(f"Password correct for 'chinnu'?: {is_correct}")
    else:
        print("User chinnufolio@gmail.com NOT FOUND in the database.")

    # also list all users
    users = User.query.all()
    print("\nAll users in DB:")
    for u in users:
        print(f"- {u.email}")
