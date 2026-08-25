import sys
import os
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, City, Bus, Booking, Payment, RewardProduct, Redemption
from app.models.bus import Route, BusSchedule
from app.models.admin_models import Role

class FullBTBTestSuite(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Clean up database records created by tests to guarantee clean run
        user = User.query.filter_by(email="fulltest_user@example.com").first()
        if user:
            bookings = Booking.query.filter_by(user_id=user.id).all()
            for b in bookings:
                Payment.query.filter_by(booking_id=b.id).delete()
                db.session.delete(b)
            Redemption.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()

        # Free up seat L5 on schedule 1 to prevent double-booking failure
        b_L5 = Booking.query.filter_by(schedule_id=1, seat_number="L5").all()
        for b in b_L5:
            Payment.query.filter_by(booking_id=b.id).delete()
            db.session.delete(b)
        db.session.commit()

    def tearDown(self):
        self.app_context.pop()

    # 1. UI PAGES
    def test_01_ui_pages(self):
        pages = ['/', '/results', '/details', '/dashboard', '/eco-rewards', '/safety', '/login']
        for page in pages:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['user_name'] = 'Test User'
            res = self.client.get(page)
            self.assertIn(res.status_code, [200, 302], f"Failed loading page {page}")

    # 2. AUTH API
    def test_02_auth_register_and_login(self):
        # Register new user
        email = "fulltest_user@example.com"
        reg_res = self.client.post('/api/auth/register', json={
            "name": "Full Test User",
            "email": email,
            "password": "TestPassword123"
        })
        self.assertEqual(reg_res.status_code, 201)
        data = reg_res.get_json()
        self.assertTrue(data['success'])

        # Login with new user
        login_res = self.client.post('/api/auth/login', json={
            "email": email,
            "password": "TestPassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data['success'])
        self.assertIn('access_token', login_data)

        # Profile check
        prof_res = self.client.get('/api/auth/profile')
        self.assertEqual(prof_res.status_code, 200)
        self.assertTrue(prof_res.get_json()['success'])

    def test_03_auth_otp_simulation(self):
        phone = "9876543210"
        send_res = self.client.post('/api/auth/send-otp', json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertTrue(send_res.get_json()['success'])

        verify_res = self.client.post('/api/auth/verify-otp', json={"phone": phone, "code": "1234"})
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.get_json()['success'])

    # 3. OPTIMIZER & SEARCH API
    def test_04_optimizer_cities(self):
        res = self.client.get('/api/optimizer/cities')
        self.assertEqual(res.status_code, 200)
        cities = res.get_json()
        self.assertIsInstance(cities, list)

    def test_05_optimizer_predict(self):
        res = self.client.post('/api/optimizer/predict', json={
            "origin": "eluru",
            "dest": "hyderabad",
            "date": "2026-03-31"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('optimizer', data)
        self.assertIn('buses', data)

    def test_06_optimizer_split_route(self):
        res = self.client.post('/api/optimizer/optimize-split-route', json={
            "source": "Eluru",
            "destination": "Hyderabad",
            "date": "2026-03-31"
        })
        self.assertEqual(res.status_code, 200)

    def test_07_optimizer_seats(self):
        # Sleeper
        res_s = self.client.get('/api/optimizer/seats?schedule_id=1&type=Sleeper')
        self.assertEqual(res_s.status_code, 200)
        self.assertGreater(len(res_s.get_json()), 0)

        # Seater
        res_c = self.client.get('/api/optimizer/seats?schedule_id=1&type=Seater')
        self.assertEqual(res_c.status_code, 200)
        self.assertGreater(len(res_c.get_json()), 0)

    def test_08_optimizer_chat(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
        res = self.client.post('/api/optimizer/chat', json={"message": "Show my bookings"})
        self.assertEqual(res.status_code, 200)
        self.assertIn('response', res.get_json())

    # 4. BOOKING & PAYMENTS API
    def test_09_seat_lock(self):
        res = self.client.post('/api/booking/lock-seat', json={
            "schedule_id": 1,
            "seat_number": "L1"
        })
        self.assertEqual(res.status_code, 200)

    def test_10_checkout_and_ticket_download(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # UPI Checkout
        res = self.client.post('/api/booking/checkout', json={
            "schedule_id": 1,
            "payment_method": "UPI",
            "upi_id": "testuser@okaxis",
            "bookings": [{
                "seat_number": "L5",
                "fare": 550,
                "passenger_name": "Alice Smith",
                "passenger_age": 28,
                "passenger_gender": "Female"
            }]
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('booking_id', data)
        booking_id = data['booking_id']

        # Download Ticket PDF
        dl_res = self.client.get(f'/api/booking/download-ticket?ids={booking_id}')
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.headers.get('Content-Type'), 'application/pdf')

        # Get User Bookings
        user_bookings = self.client.get('/api/booking/user/1')
        self.assertEqual(user_bookings.status_code, 200)

    def test_11_card_payment_process(self):
        # Valid Card Payment
        res = self.client.post('/api/booking/process-payment', json={
            "amount": 500,
            "method": "Card",
            "card_number": "4532015112830366", # Standard Visa test card
            "cvv": "123",
            "expiry": "12/28"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get('success'))

    # 5. TRACKING & DELAY PREDICTION API
    def test_12_tracking_live(self):
        res = self.client.get('/api/tracking/live/1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('location', data)
        self.assertIn('speed_kmh', data)

    def test_13_predict_delay(self):
        res = self.client.get('/api/tracking/predict-delay/1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('delay_minutes', data)
        self.assertIn('congestion', data)

    # 6. ECO-REWARDS API
    def test_14_rewards_catalog_and_redemption(self):
        # Fetch products
        p_res = self.client.get('/api/rewards/products')
        self.assertEqual(p_res.status_code, 200)
        products = p_res.get_json().get('products', [])
        self.assertGreater(len(products), 0)

        # Give test user eco points
        user = User.query.get(1)
        if user:
            user.eco_points = 500
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = 1

        # Redeem reward
        p_id = products[0]['id']
        red_res = self.client.post('/api/rewards/redeem', json={"product_id": p_id})
        self.assertEqual(red_res.status_code, 200)
        red_data = red_res.get_json()
        self.assertTrue(red_data['success'])

        coupon_code = red_data.get('coupon_code')
        self.assertIsNotNone(coupon_code)

        # Validate Coupon
        val_res = self.client.post('/api/rewards/validate-coupon', json={"coupon_code": coupon_code})
        self.assertEqual(val_res.status_code, 200)
        self.assertTrue(val_res.get_json()['success'])

    # 7. ADMIN PORTAL API
    def test_15_admin_login_and_pages(self):
        # Ensure Super Admin exists
        admin_role = Role.query.filter_by(name='Super Admin').first()
        if not admin_role:
            admin_role = Role(name='Super Admin')
            db.session.add(admin_role)
            db.session.commit()

        admin_user = User.query.filter_by(email='admin@smartbus.com').first()
        if not admin_user:
            from app.extensions import bcrypt
            admin_user = User(
                name="Admin User",
                email="admin@smartbus.com",
                password_hash=bcrypt.generate_password_hash("admin123").decode('utf-8'),
                role_id=admin_role.id
            )
            db.session.add(admin_user)
            db.session.commit()

        # Admin Login
        login_res = self.client.post('/admin/login', data={
            "email": "admin@smartbus.com",
            "password": "admin123"
        })
        self.assertIn(login_res.status_code, [200, 302])

        # Access Admin Pages with session
        with self.client.session_transaction() as sess:
            sess['admin_id'] = admin_user.id

        admin_routes = ['/admin/dashboard', '/admin/cities', '/admin/routes', '/admin/buses', '/admin/schedules']
        for ar in admin_routes:
            res = self.client.get(ar)
            self.assertEqual(res.status_code, 200, f"Admin page {ar} failed")

        # Route suggestion
        sug_res = self.client.get('/admin/api/suggest-route?origin=eluru&dest=hyderabad')
        self.assertEqual(sug_res.status_code, 200)
        self.assertIn('suggested_fare', sug_res.get_json())

if __name__ == '__main__':
    unittest.main()
