from app import create_app
from app.extensions import db
# pyrefly: ignore [missing-import]
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        res = conn.execute(text('SHOW COLUMNS FROM users'))
        cols = [r[0] for r in res.fetchall()]
        print('Existing users columns:', cols)
        
        if 'is_verified' not in cols:
            conn.execute(text('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0'))
            print('Added is_verified to users')
            
        if 'verification_token' not in cols:
            conn.execute(text('ALTER TABLE users ADD COLUMN verification_token VARCHAR(100) NULL'))
            print('Added verification_token to users')
            
        conn.commit()
    print('Migration complete.')
