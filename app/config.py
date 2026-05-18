import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartbus_super_secret_dev_key_123')
    # Use SQLite for dev since PostgreSQL might not be running locally, but it can be overridden
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///smartbus.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt_smartbus_secret_key')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
