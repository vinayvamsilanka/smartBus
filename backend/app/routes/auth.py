from flask import Blueprint, request, jsonify, session
from app.extensions import db, bcrypt
from app.models.user import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.services.auth_provider import AuthProvider
import random

from app.services.mail_service import MailService
import secrets

auth_provider = AuthProvider(use_simulation=True)

auth_bp = Blueprint('auth', __name__)

# In-memory store for email OTPs
email_otps = {}

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"success": False, "msg": "Email already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    verification_token = secrets.token_hex(16)

    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        password_hash=hashed_pw,
        role_id=None,
        is_verified=False,
        verification_token=verification_token
    )
    db.session.add(new_user)
    db.session.commit()
    
    # Send mail verification via SMTP
    MailService.send_verification_email(new_user.email, verification_token)

    # Store in UI session for seamless login
    session['user_id'] = new_user.id
    session['user_name'] = new_user.name
    
    return jsonify({
        "success": True,
        "msg": "User registered successfully. Verification email sent.",
        "verification_token": verification_token,
        "user_name": new_user.name,
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "is_verified": new_user.is_verified
        }
    }), 201

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    token = None
    if request.method == 'POST':
        data = request.get_json() or {}
        token = data.get('token')
    else:
        token = request.args.get('token')

    if not token:
        return jsonify({"success": False, "msg": "Verification token is required"}), 400
        
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify({"success": False, "msg": "Invalid or expired token"}), 400
        
    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    
    return jsonify({
        "success": True,
        "msg": "Email verified successfully!"
    }), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()

    if user and bcrypt.check_password_hash(user.password_hash, data.get('password')):
        # Store in UI session
        session['user_id'] = user.id
        session['user_name'] = user.name
        
        access_token = create_access_token(identity=str(user.id))
        role_name = user.role.name if user.role else 'User'
        return jsonify({
            "success": True,
            "access_token": access_token,
            "role": role_name,
            "user_name": user.name,
            "user": {
                "id": user.id,
                "name": user.name
            }
        }), 200

    return jsonify({"success": False, "msg": "Invalid credentials"}), 401

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    phone = data.get('phone')
    if not phone:
        return jsonify({"success": False, "msg": "Phone number required"}), 400
        
    success = auth_provider.send_otp(phone)
    if success:
        return jsonify({"success": True, "msg": "OTP sent successfully"}), 200
    return jsonify({"success": False, "msg": "Failed to send OTP"}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    phone = data.get('phone')
    code = data.get('code')
    
    if not auth_provider.verify_otp(phone, code):
        return jsonify({"success": False, "msg": "Invalid or expired OTP"}), 401
        
    # Check if user exists with this phone (using email as mock identifier for now)
    mock_email = f"{phone}@smartbus.auth"
    user = User.query.filter_by(email=mock_email).first()
    
    if not user:
        # Auto-register
        hashed_pw = bcrypt.generate_password_hash(str(random.randint(100000, 999999))).decode('utf-8')
        user = User(
            name=f"User {phone[-4:]}",
            email=mock_email,
            password_hash=hashed_pw,
            eco_points=0
        )
        db.session.add(user)
        db.session.commit()
        
    session['user_id'] = user.id
    session['user_name'] = user.name
    
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "success": True,
        "access_token": access_token,
        "user_name": user.name,
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": phone
        }
    }), 200


@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"success": False, "exists": False}), 400
        
    user = User.query.filter_by(email=email).first()
    return jsonify({"success": True, "exists": user is not None}), 200


@auth_bp.route('/send-email-otp', methods=['POST'])
def send_email_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"success": False, "msg": "Email required"}), 400
        
    otp_code = str(random.randint(1000, 9999))
    email_otps[email] = otp_code
    
    # send via MailService
    sent = False
    try:
        sent = MailService.send_verification_email(email, otp_code)
    except Exception as e:
        sent = False
    
    if not sent:
        return jsonify({
            "success": False,
            "sent": False,
            "msg": "Failed to send verification email. SMTP outbound ports (25, 465, 587) are restricted by the cloud host. Please configure an HTTP Mail API (Brevo/Resend) or run on an unblocked host."
        }), 502

    return jsonify({
        "success": True, 
        "sent": True,
        "msg": "Verification code sent to your email! Please check your Inbox and Spam folder."
    }), 200

@auth_bp.route('/test-mail', methods=['GET'])
def test_mail():
    import smtplib
    from flask import current_app
    to = request.args.get('email', 'charanreddy5638@gmail.com')
    mail_user = current_app.config.get('MAIL_USERNAME', '')
    mail_pass = current_app.config.get('MAIL_PASSWORD', '')
    diag = {
        "user_set": bool(mail_user),
        "pass_set": bool(mail_pass),
        "user_val": (mail_user[:5] + "***") if mail_user else None,
        "pass_len": len(mail_pass) if mail_pass else 0,
    }
    # Test Port 465 SSL
    try:
        s = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5)
        diag['ssl_connect'] = "ok"
        s.login(mail_user, mail_pass)
        diag['ssl_login'] = "ok"
        s.sendmail(mail_user, [to], f"Subject: Test\n\nCode 1234")
        diag['ssl_send'] = "ok"
        s.quit()
        diag['success'] = True
        return jsonify(diag)
    except Exception as e:
        diag['ssl_error'] = str(e)

    # Test Port 587 TLS
    try:
        s2 = smtplib.SMTP('smtp.gmail.com', 587, timeout=5)
        diag['tls_connect'] = "ok"
        s2.starttls()
        diag['tls_starttls'] = "ok"
        s2.login(mail_user, mail_pass)
        diag['tls_login'] = "ok"
        s2.sendmail(mail_user, [to], f"Subject: Test\n\nCode 1234")
        diag['tls_send'] = "ok"
        s2.quit()
        diag['success'] = True
    except Exception as e2:
        diag['tls_error'] = str(e2)
        diag['success'] = False

    return jsonify(diag)

@auth_bp.route('/verify-email-otp', methods=['POST'])
def verify_email_otp():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    
    if not email or not code:
        return jsonify({"success": False, "msg": "Email and code required"}), 400
        
    if email_otps.get(email) == str(code):
        return jsonify({"success": True, "msg": "Email verified successfully!"}), 200
        
    return jsonify({"success": False, "msg": "Invalid or expired Email OTP"}), 400

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    new_password = data.get('new_password')
    
    if not email or not code or not new_password:
        return jsonify({"success": False, "msg": "Missing required fields"}), 400
        
    if email_otps.get(email) != str(code):
        return jsonify({"success": False, "msg": "Invalid or expired OTP"}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "msg": "Account with this email not found"}), 404
        
    hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password_hash = hashed_pw
    db.session.commit()
    
    if email in email_otps:
        del email_otps[email]
    
    return jsonify({"success": True, "msg": "Password reset successfully!"}), 200

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "msg": "Unauthorized"}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "msg": "User not found"}), 404
        
    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "eco_points": user.eco_points if user.eco_points is not None else 0,
            "booking_count": len(user.bookings),
            "role": user.role.name if user.role else "Elite Voyager"
        }
    }), 200


