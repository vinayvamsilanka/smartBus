import os
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

def get_database_uri():
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        # Check individual MySQL environment parameters
        mysql_user = os.environ.get('MYSQL_USER')
        mysql_pass = os.environ.get('MYSQL_PASSWORD')
        mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')
        mysql_db = os.environ.get('MYSQL_DB', 'smartbus_db')
        
        if mysql_user and mysql_pass:
            db_url = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
            
    if not db_url:
        db_url = 'sqlite:///smartbus.db'

    # Convert legacy driver prefixes for SQLAlchemy compatibility
    if db_url.startswith('mysql://'):
        db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
    elif db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    return db_url

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartbus_super_secret_dev_key_123')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt_smartbus_secret_key')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    PAYMENT_RECEIVER_NAME = os.environ.get('PAYMENT_RECEIVER_NAME', 'SmartBus AI')
    PAYMENT_RECEIVER_UPI = os.environ.get('PAYMENT_RECEIVER_UPI', '9390378365@axl')

    # SMTP Mail Verification Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@smartbus.com')

