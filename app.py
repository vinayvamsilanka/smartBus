from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables exist at start-up
        db.create_all()
    # Allowing for port parity with run.py or separate port if desired, but 8000 is our standard
    app.run(debug=True, port=8000)
