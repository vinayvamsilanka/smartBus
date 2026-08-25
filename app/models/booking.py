from app.extensions import db
from datetime import datetime

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('bus_schedules.id'), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Confirmed, Cancelled
    fare_paid = db.Column(db.Float, nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)

    passenger_name = db.Column(db.String(100), nullable=True)
    passenger_age = db.Column(db.Integer, nullable=True)
    passenger_gender = db.Column(db.String(20), nullable=True)

    # Define unique constraint for seat per schedule so it doesn't double book
    __table_args__ = (db.UniqueConstraint('schedule_id', 'seat_number', name='_schedule_seat_uc'),)

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(100), unique=True)
    payment_method = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Completed')
