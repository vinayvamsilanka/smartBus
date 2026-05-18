from app import create_app
from app.extensions import db, bcrypt
from app.models import User, Role

app = create_app()

with app.app_context():
    db.create_all()

    # Create Roles
    super_admin_role = Role.query.filter_by(name='Super Admin').first()
    if not super_admin_role:
        super_admin_role = Role(name='Super Admin', description='Full access')
        db.session.add(super_admin_role)

    operator_role = Role.query.filter_by(name='Operator').first()
    if not operator_role:
        operator_role = Role(name='Operator', description='Manage buses and routes')
        db.session.add(operator_role)

    analyst_role = Role.query.filter_by(name='Analyst').first()
    if not analyst_role:
        analyst_role = Role(name='Analyst', description='View analytics only')
        db.session.add(analyst_role)
    
    db.session.commit()

    # Create Admin User
    admin = User.query.filter_by(email='admin@smartbus.com').first()
    if not admin:
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(name='System Admin', email='admin@smartbus.com', password_hash=hashed_password, role_id=super_admin_role.id)
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin@smartbus.com / admin123")
    else:
        print("Admin user already exists.")
