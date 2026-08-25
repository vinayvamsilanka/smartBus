import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from app import create_app
from app.extensions import db
from app.models import User, City, Bus, Booking, Payment, RewardProduct, Redemption
from app.models.bus import Route, BusSchedule
from app.models.graph import GraphRoute
from app.models.metrics import SafetyMetrics, EcoMetrics

def test_app():
    app = create_app()
    client = app.test_client()

    print("--- 1. Testing UI Routes ---")
    ui_routes = ['/', '/results', '/details', '/dashboard', '/eco-rewards', '/safety', '/login']
    for r in ui_routes:
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
        res = client.get(r)
        print(f"GET {r}: status {res.status_code}")

    print("\n--- 2. Testing Auth Routes ---")
    res = client.post('/api/auth/login', json={"email": "admin@smartbus.com", "password": "adminpassword"})
    print(f"POST /api/auth/login: status {res.status_code}, data: {res.get_json()}")
    
    res = client.post('/api/auth/send-otp', json={"phone": "9999999999"})
    print(f"POST /api/auth/send-otp: status {res.status_code}, data: {res.get_json()}")

    res = client.post('/api/auth/verify-otp', json={"phone": "9999999999", "code": "1234"})
    print(f"POST /api/auth/verify-otp: status {res.status_code}, data: {res.get_json()}")

    print("\n--- 3. Testing Optimizer Routes ---")
    res = client.get('/api/optimizer/cities')
    print(f"GET /api/optimizer/cities: status {res.status_code}, count: {len(res.get_json() or [])}")

    res = client.post('/api/optimizer/predict', json={"origin": "eluru", "dest": "hyderabad", "date": "2026-03-31"})
    print(f"POST /api/optimizer/predict: status {res.status_code}, bus count: {len(res.get_json().get('buses', [])) if res.get_json() else 0}")

    res = client.get('/api/optimizer/seats?schedule_id=1&type=Sleeper')
    print(f"GET /api/optimizer/seats (Sleeper): status {res.status_code}, seat count: {len(res.get_json() or [])}")

    res = client.get('/api/optimizer/seats?schedule_id=1&type=Seater')
    print(f"GET /api/optimizer/seats (Seater): status {res.status_code}, seat count: {len(res.get_json() or [])}")

    res = client.post('/api/optimizer/chat', json={"message": "Show my bookings"})
    print(f"POST /api/optimizer/chat: status {res.status_code}")

    print("\n--- 4. Testing Booking Routes ---")
    with client.session_transaction() as sess:
        sess['user_id'] = 1
    res = client.post('/api/booking/checkout', json={
        "schedule_id": 1,
        "payment_method": "UPI",
        "upi_id": "testuser@okaxis",
        "bookings": [{"seat_number": "L1", "fare": 450, "passenger_name": "John Doe", "passenger_age": 30, "passenger_gender": "Male"}]
    })
    print(f"POST /api/booking/checkout: status {res.status_code}, body: {res.get_json()}")
    booking_resp = res.get_json() or {}
    booking_id = booking_resp.get('booking_id')

    if booking_id:
        res = client.get(f'/api/booking/download-ticket?ids={booking_id}')
        print(f"GET /api/booking/download-ticket?ids={booking_id}: status {res.status_code}, content-type: {res.headers.get('Content-Type')}")

    res = client.get('/api/booking/user/1')
    print(f"GET /api/booking/user/1: status {res.status_code}, count: {len(res.get_json() or [])}")

    print("\n--- 5. Testing Rewards Routes ---")
    res = client.get('/api/rewards/products')
    print(f"GET /api/rewards/products: status {res.status_code}")

    print("\n--- 6. Testing Tracking Routes ---")
    res = client.get('/api/tracking/live/1')
    print(f"GET /api/tracking/live/1: status {res.status_code}, body: {res.get_json()}")

    res = client.get('/api/tracking/predict-delay/1')
    print(f"GET /api/tracking/predict-delay/1: status {res.status_code}, body: {res.get_json()}")

if __name__ == '__main__':
    test_app()
