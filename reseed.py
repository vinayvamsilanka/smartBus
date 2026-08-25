import random
import math
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db, bcrypt
from app.models.graph import City, GraphRoute
from app.models.bus import Bus, Route, BusSchedule
from app.models.metrics import SafetyMetrics, EcoMetrics
from app.models import User, Role, Booking, Payment

app = create_app()

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    
    # 1. Create Roles
    print("Creating roles...")
    super_admin_role = Role(name='Super Admin', description='Full access')
    operator_role = Role(name='Operator', description='Manage buses and routes')
    analyst_role = Role(name='Analyst', description='View analytics only')
    db.session.add_all([super_admin_role, operator_role, analyst_role])
    db.session.flush()
    
    # 2. Create Admin User
    print("Creating System Admin...")
    hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
    admin = User(name='System Admin', email='admin@smartbus.com', password_hash=hashed_password, role_id=super_admin_role.id)
    db.session.add(admin)
    
    # 3. Create regular user (Charan)
    print("Creating User Charan...")
    charan_password = bcrypt.generate_password_hash('password123').decode('utf-8')
    charan = User(name='Charan Kumar', email='charan@example.com', password_hash=charan_password, eco_points=150)
    db.session.add(charan)
    db.session.flush()
    
    # 4. Create Cities
    print("Creating cities...")
    NEW_CITIES = [
        'Bangalore', 'Chennai', 'Mumbai', 'Pune', 'Mysore', 'Vellore', 
        'Chittoor', 'Eluru', 'Hyderabad', 'Vijayawada', 'Guntur', 
        'Tirupati', 'Visakhapatnam', 'Vizianagaram', 'Nellore', 
        'Kurnool', 'Rajahmundry', 'Ongole', 'Warangal', 'Anantapur', 
        'Kadapa', 'Kakinada'
    ]
    city_objs = []
    for city_name in NEW_CITIES:
        city = City(name=city_name.lower(), is_active=True)
        db.session.add(city)
        city_objs.append(city)
    db.session.flush()
    
    # 5. Create Buses (100 buses)
    print("Creating 100 fleet buses...")
    types = ['AC Sleeper', 'Multi-Axle Volvo', 'Non-AC Sleeper', 'Luxury Scania', 'Express']
    all_buses = []
    for i in range(100):
        b_num = f"AP-{random.randint(0, 99):02d}-{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
        bus = Bus(bus_number=b_num, type=random.choice(types), capacity=random.randint(30, 45))
        db.session.add(bus)
        db.session.flush()
        # Metrics
        sm = SafetyMetrics(bus_id=bus.id, driver_score=random.randint(85, 98), overall_score=random.randint(88, 97))
        em = EcoMetrics(bus_id=bus.id, co2_emissions_per_km=0.03 + random.random()*0.02)
        db.session.add_all([sm, em])
        all_buses.append(bus)
    
    # 6. Create Routes & Schedules
    print("Creating logical routes and schedules...")
    CITY_COORDINATES = {
        'hyderabad': (17.3850, 78.4867),
        'vijayawada': (16.5062, 80.6480),
        'guntur': (16.3067, 80.4365),
        'tirupati': (13.6285, 79.4192),
        'visakhapatnam': (17.6868, 83.2185),
        'vizianagaram': (18.1067, 83.3950),
        'nellore': (14.4426, 79.9865),
        'kurnool': (15.8281, 78.0373),
        'rajahmundry': (17.0005, 81.7835),
        'ongole': (15.5057, 80.0499),
        'warangal': (17.9689, 79.5941),
        'anantapur': (14.6819, 77.6006),
        'kadapa': (14.4673, 78.8242),
        'kakinada': (16.9891, 82.2475),
        'bangalore': (12.9716, 77.5946),
        'chennai': (13.0827, 80.2707),
        'mumbai': (19.0760, 72.8777),
        'pune': (18.5204, 73.8567),
        'mysore': (12.2958, 76.6394),
        'vellore': (12.9165, 79.1325),
        'chittoor': (13.2048, 79.1003),
        'eluru': (16.7107, 81.1030)
    }

    def calc_dist(c1_name, c2_name):
        c1 = CITY_COORDINATES.get(c1_name.lower())
        c2 = CITY_COORDINATES.get(c2_name.lower())
        if not c1 or not c2: return None
        lat1, lon1 = map(math.radians, c1)
        lat2, lon2 = map(math.radians, c2)
        dlat, dlon = lat2-lat1, lon2-lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))

    today = datetime.now().date()
    route_count = 0
    
    for src in city_objs:
        for dst in city_objs:
            if src.id == dst.id: continue
            
            dist = calc_dist(src.name, dst.name)
            if dist and dist < 1000:
                fare = round((dist * 1.6) + 100, -1)
                r = Route(origin=src.name, destination=dst.name, distance_km=round(dist, 1), base_fare=fare)
                db.session.add(r)
                db.session.flush()
                route_count += 1
                
                # Graph routes for AI optimizer
                for d_offset in range(3):
                    travel_date = today + timedelta(days=d_offset)
                    g_fare = r.base_fare + random.randint(-50, 50)
                    db.session.add(GraphRoute(
                        source_city_id=src.id, destination_city_id=dst.id, 
                        distance=r.distance_km, base_price=g_fare, 
                        estimated_time=dist/55.0, route_date=travel_date
                    ))
                
                # Schedules
                for _ in range(2):
                    departure = datetime.now() + timedelta(days=random.randint(0, 2), hours=random.randint(0, 23))
                    arrival = departure + timedelta(hours=dist/55.0 + 0.5)
                    bus = random.choice(all_buses)
                    db.session.add(BusSchedule(
                        bus_id=bus.id, route_id=r.id, 
                        departure_time=departure, arrival_time=arrival,
                        projected_delay_mins=random.randint(0, 30)
                    ))
                    
    # 7. Create Demo Bookings for Charan Kumar
    print("Seeding active bookings for Charan Kumar...")
    import uuid
    some_schedules = BusSchedule.query.limit(3).all()
    for idx, schedule in enumerate(some_schedules):
        seat_num = f"{idx+4}A"
        booking = Booking(
            user_id=charan.id,
            schedule_id=schedule.id,
            seat_number=seat_num,
            status='Confirmed' if idx > 0 else 'Pending',
            fare_paid=schedule.route.base_fare,
            passenger_name='Charan Kumar',
            passenger_age=24,
            passenger_gender='Male'
        )
        db.session.add(booking)
        db.session.flush()
        
        payment = Payment(
            booking_id=booking.id,
            amount=booking.fare_paid,
            transaction_id=f"UPI:upi_sim_charan{idx}:{uuid.uuid4().hex[:8]}",
            payment_method='UPI',
            status='Completed'
        )
        db.session.add(payment)

    db.session.commit()
    print(f"Database recreation & seeding complete! Total logical routes created: {route_count}")
