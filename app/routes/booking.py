from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Booking, SeatMap
import uuid

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/lock-seat', methods=['POST'])
def lock_seat():
    # Simulated Redis cache lock mechanism
    # Would use something like: redis_client.set(f"seat_lock_{schedule_id}_{seat}", user_id, ex=300)
    data = request.json
    schedule_id = data.get('schedule_id')
    seat_number = data.get('seat_number')
    
    return jsonify({"msg": "Seat locked temporarily", "lock_expires_in": "300s"}), 200

@booking_bp.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    # Utilizing an atomic transaction block via SQLAlchemy
    try:
        new_booking = Booking(
            user_id=data.get('user_id', 1), # Simulated user ID
            schedule_id=data.get('schedule_id', 1),
            seat_number=data.get('seat_number'),
            fare_paid=data.get('fare'),
            status='Confirmed'
        )
        db.session.add(new_booking)
        db.session.commit()
        return jsonify({"msg": "Booking confirmed", "booking_id": new_booking.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "Double booking detected or logic error", "error": str(e)}), 400

@booking_bp.route('/webhook', methods=['POST'])
def payment_webhook():
    # Handle simulated payment events (e.g. from Razorpay/Stripe)
    payload = request.json
    booking_id = payload.get('booking_id')
    if payload.get('event') == 'payment.captured':
        booking = Booking.query.get(booking_id)
        if booking:
            booking.status = 'Confirmed'
            db.session.commit()
    return jsonify({"status": "acknowledged"}), 200

@booking_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_bookings(user_id):
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.booking_date.desc()).all()
    results = []
    for b in bookings:
        sch = b.schedule
        results.append({
            "id": b.id,
            "origin": sch.route.origin.title() if sch else "Unknown",
            "destination": sch.route.destination.title() if sch else "Unknown",
            "date": b.booking_date.strftime('%b %d, %Y'),
            "seat": b.seat_number,
            "fare": b.fare_paid,
            "status": b.status
        })
    return jsonify(results), 200
