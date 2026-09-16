import random
import math
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.graph import City, GraphRoute
from app.models.bus import Bus, Route, BusSchedule
from app.models.metrics import SafetyMetrics, EcoMetrics

app = create_app()

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

with app.app_context():
    print("Initializing Real-World Data seeding...")
    
    # 1. Ensure enough buses exist (Let's target 100 buses)
    existing_buses = Bus.query.count()
    if existing_buses < 100:
        types = ['AC Sleeper', 'Multi-Axle Volvo', 'Non-AC Sleeper', 'Luxury Scania', 'Express']
        for i in range(100 - existing_buses):
            b_num = f"AP-{random.randint(0, 99):02d}-{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
            bus = Bus(bus_number=b_num, type=random.choice(types), capacity=random.randint(30, 45))
            db.session.add(bus)
            db.session.flush()
            # Metrics
            sm = SafetyMetrics(bus_id=bus.id, driver_score=random.randint(85, 98), overall_score=random.randint(88, 97))
            em = EcoMetrics(bus_id=bus.id, co2_emissions_per_km=0.03 + random.random()*0.02)
            db.session.add(sm)
            db.session.add(em)
        db.session.commit()
        print(f"Buses created. Total Fleet: 100")

    # 2. Get All Active Cities
    cities = City.query.filter_by(is_active=True).all()
    all_buses = Bus.query.all()
    
    # 3. Pair them and seed Routes
    route_count = 0
    today = datetime.now().date()
    
    for src in cities:
        for dst in cities:
            if src.id == dst.id: continue
            
            dist = calc_dist(src.name, dst.name)
            if dist and dist < 1000: # Only seed routes within 1000km for realism
                # A. Check and Add to 'Routes' (Standard model)
                r = Route.query.filter_by(origin=src.name, destination=dst.name).first()
                if not r:
                    fare = round((dist * 1.6) + 100, -1)
                    r = Route(origin=src.name, destination=dst.name, distance_km=round(dist, 1), base_fare=fare)
                    db.session.add(r)
                    db.session.flush()
                    route_count += 1
                
                # B. Check and Add to 'GraphRoutes' (AI model) for multiple dates
                for d_offset in range(3):
                    travel_date = today + timedelta(days=d_offset)
                    gr = GraphRoute.query.filter_by(source_city_id=src.id, destination_city_id=dst.id, route_date=travel_date).first()
                    if not gr:
                        g_fare = r.base_fare + random.randint(-50, 50)
                        db.session.add(GraphRoute(
                            source_city_id=src.id, destination_city_id=dst.id, 
                            distance=r.distance_km, base_price=g_fare, 
                            estimated_time=dist/55.0, route_date=travel_date
                        ))
                
                # C. Add Bus Schedules (At least 2 per route)
                schedules_exist = BusSchedule.query.filter_by(route_id=r.id).first()
                if not schedules_exist:
                    for _ in range(2):
                        departure = datetime.now() + timedelta(days=random.randint(0, 2), hours=random.randint(0, 23))
                        b_type_lower = bus.type.lower()
                        speed = 55.0
                        if 'volvo' in b_type_lower or 'scania' in b_type_lower or 'luxury' in b_type_lower or 'premium' in b_type_lower:
                            speed = 68.0
                        elif 'express' in b_type_lower:
                            speed = 58.0
                        elif 'sleeper' in b_type_lower:
                            speed = 48.0
                            
                        arrival = departure + timedelta(hours=dist/speed)
                        bus = random.choice(all_buses)
                        db.session.add(BusSchedule(
                            bus_id=bus.id, route_id=r.id, 
                            departure_time=departure, arrival_time=arrival,
                            projected_delay_mins=random.randint(0, 30)
                        ))

        print(f"Seeded logical routes from {src.name.title()}...")
        db.session.commit()

    print(f"Data seeding complete. {route_count} new network edges created.")
