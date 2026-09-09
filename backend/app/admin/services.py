from app.extensions import db
from app.models import AdminLogs, User
from sqlalchemy import func
from datetime import datetime

class AdminService:
    @staticmethod
    def is_authorized(user_id, required_roles=None):
        user = User.query.get(user_id)
        if not user or not user.role:
            return False
        if required_roles and user.role.name not in required_roles:
            return False
        return True

    @staticmethod
    def log_action(admin_id, action, target_table=None, target_id=None, ip_address=None):
        log = AdminLogs(
            admin_id=admin_id,
            action=action,
            target_table=target_table,
            target_id=target_id,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()

admin_service = AdminService()
