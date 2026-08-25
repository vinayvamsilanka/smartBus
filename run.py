from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Create tables automatically for demo purposes if they don't exist
        db.create_all()
    app.run(debug=False, port=8000)
