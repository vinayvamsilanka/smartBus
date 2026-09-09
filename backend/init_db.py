import os
import sys
import pymysql
from urllib.parse import urlparse

from app import create_app
from app.extensions import db

app = create_app()

def ensure_mysql_database_exists(uri):
    """
    If using MySQL, ensure the target database exists on the server.
    """
    if not uri.startswith("mysql"):
        return

    try:
        parsed = urlparse(uri.replace("mysql+pymysql://", "mysql://"))
        db_name = parsed.path.lstrip('/')
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        username = parsed.username or 'root'
        password = parsed.password or ''

        print(f"Connecting to MySQL server at {host}:{port} as user '{username}'...")
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"Database '{db_name}' verified/created successfully.")
        conn.close()
    except Exception as e:
        print(f"Notice: Could not automatically create MySQL database via pymysql connection: {e}")
        print("Please ensure your MySQL server is running and credentials in .env are correct.")

def initialize_database():
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    print(f"Initializing database using URI: {db_uri}")
    
    ensure_mysql_database_exists(db_uri)
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database schema created successfully!")

if __name__ == '__main__':
    initialize_database()
