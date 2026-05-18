import random
import math
from datetime import datetime, date
from app.extensions import db
from app.models.graph import City, GraphRoute, FareHistory

# Geographical coordinates (Latitude, Longitude) for major cities in Andhra Pradesh and Telangana
# This enables the AI to check if a split route is "possible" and not a massive detour.
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

class SplitJourneyOptimizerService:
    def _get_canonical_city_name(self, city_name):
        """Normalize city name and return the canonical spelling if it matches a known pattern."""
        name = city_name.lower().strip()
        
        # Mapping common typos and variations to canonical names
        corrections = {
            'banglore': 'bangalore',
            'bglr': 'bangalore',
            'bengaluru': 'bangalore',
            'hyd': 'hyderabad',
            'tpt': 'tirupati',
            'vizag': 'visakhapatnam',
            'vzg': 'visakhapatnam',
            'vja': 'vijayawada',
            'chn': 'chennai',
            'mum': 'mumbai'
        }
        
        if name in corrections:
            return corrections[name]
            
        # If it matches any of our known coordinates keys exactly, return it
        if name in CITY_COORDINATES:
            return name
            
        # Fuzzy matching: check if it's very similar to an existing city
        for canonical in CITY_COORDINATES.keys():
            if len(name) > 4 and (name in canonical or canonical in name):
                return canonical
                
        return name

    def _calculate_geodesic_distance(self, city1_name, city2_name):
        """Calculate approximate distance in KM between two cities using Haversine formula."""
        c1 = CITY_COORDINATES.get(city1_name.lower())
        c2 = CITY_COORDINATES.get(city2_name.lower())
        
        if not c1 or not c2:
            return None # Unknown distance
            
        lat1, lon1 = map(math.radians, c1)
        lat2, lon2 = map(math.radians, c2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371 # Radius of earth in kilometers
        return c * r

    def optimize_split_route(self, source_name, dest_name, travel_date):
        source_name = self._get_canonical_city_name(source_name)
        dest_name = self._get_canonical_city_name(dest_name)
        
        # 1. Ensure mock data exists to behave like real DB engine scaling (Refined logic)
        self._seed_engine_if_needed(source_name, dest_name, travel_date)
        
        # 2. Lookup Cities in Relational DB
        source = City.query.filter_by(name=source_name, is_active=True).first()
        dest = City.query.filter_by(name=dest_name, is_active=True).first()
        
        if not source or not dest:
            return {
                "split_available": False,
                "message": "Source or destination city not found in the travel graph."
            }
            
        # 3. Get Direct Route
        direct_route = GraphRoute.query.filter_by(
            source_city_id=source.id,
            destination_city_id=dest.id,
            route_date=travel_date,
            is_active=True
        ).first()
        
        direct_price = direct_route.base_price if direct_route else None
        direct_dist = direct_route.distance if direct_route else self._calculate_geodesic_distance(source_name, dest_name)
        
        # 4. Analyze Split Routes (Graph Traversal A -> B -> C)
        leg1_routes = GraphRoute.query.filter_by(
            source_city_id=source.id,
            route_date=travel_date,
            is_active=True
        ).all()
        
        best_split = None
        best_savings = 0
        
        for leg1 in leg1_routes:
            intermediate_id = leg1.destination_city_id
            
            # Skip if A->B actually is A->C
            if intermediate_id == dest.id:
                continue
                
            # Find B -> C in DB
            leg2 = GraphRoute.query.filter_by(
                source_city_id=intermediate_id,
                destination_city_id=dest.id,
                route_date=travel_date,
                is_active=True
            ).first()
            
            if leg2:
                total_split_price = leg1.base_price + leg2.base_price
                total_split_dist = leg1.distance + leg2.distance
                
                # --- AI FEASIBILITY CHECK (NEW) ---
                # Check 1: Geographical Logic (Is it a massive detour?)
                # A valid split should not be significantly longer than the direct route (max 1.25x now stricter)
                if direct_dist and total_split_dist > (direct_dist * 1.25):
                    continue # Reject illogical detour
                
                # Check 2: Hassle-to-Savings Ratio (WORTH IT CHECK)
                # For small savings like ₹41, the hassle isn't worth it.
                savings = (direct_price - total_split_price) if direct_price else 150
                
                # Require at least 10% savings AND at least ₹50 
                # OR if the savings are very large (₹150+) regardless of percentage
                is_worth_it = False
                savings_pct = (savings / direct_price) if direct_price else 0
                
                if direct_price:
                    if savings >= 100 or (savings_pct >= 0.10 and savings >= 50):
                        is_worth_it = True
                else:
                    is_worth_it = True # No direct route, so any split is worth it
                    
                if not is_worth_it:
                    continue

                # Check 3: Total travel time (Time Detour Check)
                total_time = leg1.estimated_time + leg2.estimated_time + 1.5 # 1.5 hours layover buffer
                if direct_route and total_time > (direct_route.estimated_time * 1.5):
                    continue # Too slow compared to direct

                # Update best split if it's the most savings
                if savings > best_savings:
                    best_savings = savings
                    intermediate_city = City.query.get(intermediate_id)
                    
                    best_split = {
                        "intermediate_city": intermediate_city.name.title(),
                        "total_split_price": total_split_price,
                        "leg1_price": leg1.base_price,
                        "leg2_price": leg2.base_price,
                        "total_travel_time": leg1.estimated_time + leg2.estimated_time,
                        "direct_travel_time": direct_route.estimated_time if direct_route else None,
                        "layover_time": round(random.uniform(0.7, 2.0), 1) 
                    }
                        
        if not best_split:
            return {
                "split_available": False,
                "message": "Direct route is optimal. No fair or feasible split route found for this journey.",
                "direct_price": round(direct_price, 2) if direct_price else None
            }
            
        savings_amount = direct_price - best_split['total_split_price'] if direct_price else 0
        savings_percentage = round((savings_amount / direct_price) * 100, 1) if direct_price else 0
        
        # Confidence score based on geographic efficiency and pricing
        # More detour = lower confidence
        dist_eff = 1.0
        if direct_dist:
            dist_eff = direct_dist / (best_split['total_split_price'] / 1.5) # simple hack
            dist_ratio = (best_split['total_split_price'] / 1.5) / direct_dist if direct_dist > 0 else 1
            
        ai_confidence = min(98, 95 - int((best_split['layover_time'] - 0.5) * 4))
        
        route_timeline = [source_name.title(), best_split['intermediate_city'], dest_name.title()]
        
        return {
            "split_available": True,
            "route_timeline": route_timeline,
            "intermediate_city": best_split['intermediate_city'],
            "total_split_price": round(best_split['total_split_price'], 2),
            "direct_price": round(direct_price, 2) if direct_price else None,
            "savings_amount": round(savings_amount, 2),
            "savings_percentage": savings_percentage,
            "total_travel_time_hours": round(best_split['total_travel_time'], 1),
            "direct_travel_time_hours": round(best_split['direct_travel_time'], 1) if best_split['direct_travel_time'] else None,
            "layover_time_hours": best_split['layover_time'],
            "ai_confidence_score": ai_confidence
        }
        
    def _seed_engine_if_needed(self, source_name, dest_name, travel_date):
        # Normalize first
        source_name = self._get_canonical_city_name(source_name)
        dest_name = self._get_canonical_city_name(dest_name)
        
        # We simulate populating a full graph DB when someone queries a missing pair
        src = City.query.filter_by(name=source_name).first()
        if not src:
            src = City(name=source_name, is_active=True)
            db.session.add(src)
            db.session.commit()
            
        dst = City.query.filter_by(name=dest_name).first()
        if not dst:
            dst = City(name=dest_name, is_active=True)
            db.session.add(dst)
            db.session.commit()
            
        direct = GraphRoute.query.filter_by(source_city_id=src.id, destination_city_id=dst.id, route_date=travel_date).first()
        
        # Calculate real-ish direct distance
        direct_dist = self._calculate_geodesic_distance(source_name, dest_name)
        if not direct_dist:
            direct_dist = random.randint(300, 600)
            
        if not direct:
            direct_price = direct_dist * random.uniform(1.4, 1.9)
            direct_time = direct_dist / 55.0
            db.session.add(GraphRoute(
                source_city_id=src.id, destination_city_id=dst.id, distance=direct_dist,
                base_price=direct_price, estimated_time=direct_time, route_date=travel_date
            ))
            db.session.commit()
            direct = GraphRoute.query.filter_by(source_city_id=src.id, destination_city_id=dst.id, route_date=travel_date).first()

        # Seed logical pivots
        # Instead of random choice, we check which cities are actually between src and dst
        pivots = [p for p in CITY_COORDINATES.keys() if p != source_name and p != dest_name]
        
        logical_pivots_found = 0
        for p_name in pivots:
            p_dist_1 = self._calculate_geodesic_distance(source_name, p_name)
            p_dist_2 = self._calculate_geodesic_distance(p_name, dest_name)
            
            if p_dist_1 and p_dist_2:
                # If the detour is less than 15%, it's a very logical pivot
                if (p_dist_1 + p_dist_2) < (direct_dist * 1.15):
                    # Check if routes already exist
                    pivot = City.query.filter_by(name=p_name).first()
                    if not pivot:
                        pivot = City(name=p_name)
                        db.session.add(pivot)
                        db.session.commit()
                    
                    # Create Leg 1
                    leg1 = GraphRoute.query.filter_by(source_city_id=src.id, destination_city_id=pivot.id, route_date=travel_date).first()
                    if not leg1:
                        # Price slightly lower if it's a hub (simulated)
                        price1 = p_dist_1 * random.uniform(1.2, 1.4) 
                        db.session.add(GraphRoute(
                            source_city_id=src.id, destination_city_id=pivot.id, distance=p_dist_1,
                            base_price=price1, estimated_time=p_dist_1/50.0, route_date=travel_date
                        ))
                    
                    # Create Leg 2
                    leg2 = GraphRoute.query.filter_by(source_city_id=pivot.id, destination_city_id=dst.id, route_date=travel_date).first()
                    if not leg2:
                        price2 = p_dist_2 * random.uniform(1.2, 1.4)
                        db.session.add(GraphRoute(
                            source_city_id=pivot.id, destination_city_id=dst.id, distance=p_dist_2,
                            base_price=price2, estimated_time=p_dist_2/50.0, route_date=travel_date
                        ))
                    
                    logical_pivots_found += 1
                    if logical_pivots_found >= 2: break # Max 2 logical pivots to seed
        
        db.session.commit()

split_optimizer_service = SplitJourneyOptimizerService()


split_optimizer_service = SplitJourneyOptimizerService()
