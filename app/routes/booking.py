from flask import Blueprint, request, jsonify, current_app, session
from app.extensions import db
from app.models import Booking, Payment, SeatMap, User, BusSchedule
from app.models.reward import Redemption
import uuid
from flask import send_file
from app.services.pdf_generator import generate_ticket_pdf
from app.services.payment_provider import PaymentProvider

payment_provider = PaymentProvider(use_simulation=True)

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
    data = request.json or {}
    try:
        bookings_data = data.get('bookings')
        if not bookings_data:
            bookings_data = [{
                "seat_number": data.get('seat_number'),
                "fare": data.get('fare'),
                "passenger_name": data.get('passenger_name'),
                "passenger_age": data.get('passenger_age'),
                "passenger_gender": data.get('passenger_gender')
            }]

        user_id = session.get('user_id') or data.get('user_id') or 1
        schedule_id = data.get('schedule_id') or 1
        payment_method = data.get('payment_method', 'UPI')
        payment_receiver = current_app.config.get('PAYMENT_RECEIVER_UPI', '9390378365@axl')
        
        # Calculate total amount to process via payment provider
        original_total = sum(float(b_item.get('fare', 0)) for b_item in bookings_data if b_item.get('fare') is not None)
        total_amount = original_total
        
        # Apply coupon code if provided
        coupon_code = data.get('coupon_code')
        applied_redemption = None
        if coupon_code:
            applied_redemption = Redemption.query.filter_by(coupon_code=coupon_code, user_id=user_id, status='Active').first()
            if applied_redemption:
                discount_pct = 0.10
                if "50%" in applied_redemption.product.name:
                    discount_pct = 0.50
                total_amount = original_total * (1.0 - discount_pct)
        
        # Validate payment via payment provider
        txn_id = f"txn_sim_{uuid.uuid4().hex[:12]}"
        
        if payment_method.startswith('Card'):
            card_number = data.get('card_number', '')
            cvv = data.get('cvv', '')
            expiry = data.get('expiry', '')
            pay_result = payment_provider.process_card_payment(
                amount=total_amount,
                card_number=card_number,
                cvv=cvv,
                expiry=expiry
            )
            if not pay_result.get('success'):
                return jsonify({"msg": "Payment failed", "error": pay_result.get('error')}), 400
            txn_id = pay_result.get('transaction_id')
            
        elif payment_method.startswith('UPI'):
            upi_id = data.get('upi_id', '')
            pay_result = payment_provider.process_upi_payment(
                amount=total_amount,
                upi_id=upi_id
            )
            if not pay_result.get('success'):
                return jsonify({"msg": "Payment failed", "error": pay_result.get('error')}), 400
            txn_id = pay_result.get('transaction_id')
        
        # Unified transaction identifier prefix
        txn_uuid = uuid.uuid4().hex[:10]
        
        booking_ids = []
        payment_details = []

        for idx, b_item in enumerate(bookings_data):
            seat_num = b_item.get('seat_number')
            fare = b_item.get('fare')
            p_name = b_item.get('passenger_name')
            p_age = b_item.get('passenger_age')
            p_gender = b_item.get('passenger_gender')

            if not seat_num or fare is None:
                continue

            new_booking = Booking(
                user_id=user_id,
                schedule_id=schedule_id,
                seat_number=seat_num,
                fare_paid=fare,
                passenger_name=p_name,
                passenger_age=p_age,
                passenger_gender=p_gender,
                status='Confirmed'
            )
            db.session.add(new_booking)
            db.session.flush()
            
            # Gamification: Award Carbon Credits
            eco_points = 50
            try:
                sch = BusSchedule.query.get(schedule_id)
                if sch and sch.bus and sch.bus.eco_rating != 'High':
                    eco_points = 20
            except:
                pass
            
            user = User.query.get(user_id)
            if user:
                user.eco_points = (user.eco_points or 0) + eco_points
                
            db.session.flush()
            
            transaction_id = f"{payment_method}:{txn_id}:{txn_uuid}-{idx+1}"
            payment = Payment(
                booking_id=new_booking.id,
                amount=fare,
                transaction_id=transaction_id,
                payment_method=payment_method,
                status='Completed'
            )
            db.session.add(payment)
            
            booking_ids.append(new_booking.id)
            payment_details.append({
                "booking_id": new_booking.id,
                "seat_number": seat_num,
                "transaction_id": transaction_id,
                "amount": fare
            })

        if applied_redemption:
            applied_redemption.status = 'Used'

        db.session.commit()

        return jsonify({
            "msg": "Bookings confirmed",
            "booking_id": booking_ids[0] if booking_ids else None,
            "booking_ids": booking_ids,
            "payment": {
                "receiver": payment_receiver,
                "method": payment_method,
                "transaction_ids": [p["transaction_id"] for p in payment_details],
                "details": payment_details
            }
        }), 200

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
        payment = Payment.query.filter_by(booking_id=b.id).first()
        results.append({
            "id": b.id,
            "origin": sch.route.origin.title() if sch and sch.route else "Unknown",
            "destination": sch.route.destination.title() if sch and sch.route else "Unknown",
            "date": b.booking_date.strftime('%b %d, %Y'),
            "booking_time": b.booking_date.strftime('%I:%M %p'),
            "seat": b.seat_number,
            "fare": b.fare_paid,
            "status": b.status,
            "bus_number": sch.bus.bus_number if sch and sch.bus else "AI-SMART-707",
            "bus_type": sch.bus.type if sch and sch.bus else "AC Sleeper",
            "departure_time": sch.departure_time.strftime('%I:%M %p') if sch else "09:00 PM",
            "arrival_time": sch.arrival_time.strftime('%I:%M %p') if sch else "06:00 AM",
            "distance_km": sch.route.distance_km if sch and sch.route else 350.0,
            "eco_rating": sch.bus.eco_rating if sch and sch.bus else "High",
            "payment_method": payment.payment_method if payment else "UPI",
            "transaction_id": payment.transaction_id if payment else "N/A",
            "passenger_name": b.passenger_name or "Traveler",
            "passenger_age": b.passenger_age or 25,
            "passenger_gender": b.passenger_gender or "Male",
            "bus_id": sch.bus.id if sch and sch.bus else 1,
            "schedule_id": b.schedule_id
        })
    return jsonify(results), 200

@booking_bp.route('/process-payment', methods=['POST'])
def process_payment():
    data = request.json or {}
    amount = data.get('amount')
    method = data.get('method')
    
    if method == 'Card':
        card_number = data.get('card_number')
        cvv = data.get('cvv')
        expiry = data.get('expiry')
        result = payment_provider.process_card_payment(amount, card_number, cvv, expiry)
    elif method == 'UPI':
        upi_id = data.get('upi_id')
        result = payment_provider.process_upi_payment(amount, upi_id)
    else:
        # Netbanking or unknown
        result = {"success": True, "transaction_id": f"netb_sim_{uuid.uuid4().hex[:12]}", "status": "succeeded"}
        
    if result.get("success"):
        return jsonify(result), 200
    else:
        return jsonify(result), 400

@booking_bp.route('/download-ticket', methods=['GET'])
def download_ticket():
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return "Missing booking IDs", 400
        
    booking_ids = [int(i) for i in ids_str.split(',') if i.strip().isdigit()]
    if not booking_ids:
        return "Invalid booking IDs", 400

    bookings = Booking.query.filter(Booking.id.in_(booking_ids)).all()
    if not bookings:
        return "Bookings not found", 404
        
    payment = Payment.query.filter_by(booking_id=bookings[0].id).first()
    schedule = BusSchedule.query.get(bookings[0].schedule_id)
    
    pdf_buffer = generate_ticket_pdf(bookings, payment, schedule)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"SmartBus_Ticket_{bookings[0].id}_Group.pdf",
        mimetype='application/pdf'
    )

