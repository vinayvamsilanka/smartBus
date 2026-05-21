from flask import Blueprint, request, jsonify, session
from app.extensions import db, bcrypt
from app.models.user import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"success": False, "msg": "Email already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        password_hash=hashed_pw,
        role_id=None
    )
    db.session.add(new_user)
    db.session.commit()
    
    # Store in UI session for seamless login
    session['user_id'] = new_user.id
    session['user_name'] = new_user.name
    
    return jsonify({
        "success": True,
        "msg": "User registered successfully",
        "user_name": new_user.name,
        "user": {
            "id": new_user.id,
            "name": new_user.name
        }
    }), 201

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

