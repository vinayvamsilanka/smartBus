from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import jsonify
from app.models import User

def role_required(role='Admin'):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(int(user_id))
            if not user or user.role != role:
                return jsonify({'msg': 'Access forbidden: Insufficient permissions'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
