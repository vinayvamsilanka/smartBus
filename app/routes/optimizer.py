from flask import Blueprint, request, jsonify
import random
from datetime import datetime, timedelta
from app.services.ml_predictor import ml_service
from app.services.split_optimizer import split_optimizer_service
from app.models import AnalyticsLogs, City
from app.extensions import db

optimizer_bp = Blueprint('optimizer', __name__)

@optimizer_bp.route('/cities', methods=['GET'])
def get_cities():
    active_cities = City.query.filter_by(is_active=True).order_by(City.name).all()
    return jsonify([city.name for city in active_cities])

@optimizer_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json or {}
        origin = data.get('origin', 'Hyderabad')
        dest = data.get('dest', 'Bangalore')
        
        # Log the search asynchronously (represented synchronously here for simplicity)
        try:
            log = AnalyticsLogs(endpoint_accessed='/api/optimizer/predict', search_origin=origin, search_dest=dest)
            db.session.add(log)
            db.session.commit()
        except:
            db.session.rollback() # Don't fail if logging fails

        today = datetime.now()
        trends = []
        labels = []
        fares = []
        
        for i in range(1, 8):
            current_date_obj = today + timedelta(days=i)
            date_str = current_date_obj.strftime('%b %d')
            fare = ml_service.predict_fare(i, origin, dest)
            trends.append({'date': date_str, 'fare': fare})
            labels.append(date_str)
            fares.append(fare)
        
        cheapest = min(trends, key=lambda x: x['fare'])
        
        # -------------------------------------------------------------
        # NEW: DYNAMIC RELATIONAL SPLIT JOURNEY OPTIMIZATION GRAPH ENGINE
        # -------------------------------------------------------------
        try:
            travel_date = datetime.strptime(data.get('date', today.strftime('%Y-%m-%d')), "%Y-%m-%d").date()
        except Exception:
            travel_date = today.date()
            
        split_data = split_optimizer_service.optimize_split_route(origin, dest, travel_date)
        
        if split_data.get('split_available'):
            direct_fare = split_data['direct_price']
            optimizer = {
                'labels': labels,
                'fares': fares,
                'cheapest_date': cheapest,
                'ai_confidence': split_data['ai_confidence_score'],
                'split_journey': {
                    'available': True,
                    'via': split_data['intermediate_city'],
                    'route_timeline': split_data['route_timeline'],
                    'direct_fare': split_data['direct_price'],
                    'split_fare': split_data['total_split_price'],
                    'savings': split_data['savings_amount']
                }
            }
        else:
            direct_fare = split_data.get('direct_price') or cheapest['fare']
            optimizer = {
                'labels': labels,
                'fares': fares,
                'cheapest_date': cheapest,
                'ai_confidence': random.randint(82, 98),
                'split_journey': {
                    'available': False
                }
            }
        
        # -------------------------------------------------------------
        # DYNAMIC BUS SEARCH (DATABASE-DRIVEN)
        # -------------------------------------------------------------
        from app.models.bus import BusSchedule, Bus, Route
        from app.models.metrics import SafetyMetrics, EcoMetrics
        
        # Simple match: origin/dest names in the routes table
        # We filter by is_active on all entities (Soft Delete support)
        # Strictly check if both origin and destination cities are active hubs in the system
        origin_city = City.query.filter_by(name=origin.lower(), is_active=True).first()
        dest_city = City.query.filter_by(name=dest.lower(), is_active=True).first()

        if not origin_city or not dest_city:
            # If either 'port' is inactive, we return no schedules for this link
            active_schedules = []
        else:
            active_schedules = db.session.query(BusSchedule).join(Route).join(Bus).filter(
                Route.origin.ilike(origin),
                Route.destination.ilike(dest),
                BusSchedule.is_active == True,
                Bus.is_active == True,
                Route.is_active == True
            ).all()

        buses = []
        badges = ["⭐ Best Value", "🛡️ Safest", "🌱 Greenest", "⚡ Fastest", "💎 Premium"]
        
        for idx, schedule in enumerate(active_schedules):
            bus = schedule.bus
            # Fetch or mock metrics for this bus (Production level uses metrics table)
            safety_m = SafetyMetrics.query.filter_by(bus_id=bus.id).first()
            eco_m = EcoMetrics.query.filter_by(bus_id=bus.id).first()
            
            # Calculate scores or Use placeholders if metrics missing
            safety_score = safety_m.overall_score if safety_m else random.randint(85, 95)
            eco_score_val = eco_m.eco_rating if eco_m else "High"
            
            bus_fare = schedule.route.base_fare + random.randint(-50, 100) # Slight dynamic variance
            badge = badges[idx % len(badges)]
            
            # DYNAMIC AI REASONING GENERATION
            otp = random.randint(80, 99) # Placeholder or from metrics
            reg_otp = schedule.projected_delay_mins <= 5
            
            reasons = []
            if safety_score >= 95:
                reasons.append(f"top-tier safety rating for the {dest.title()} route")
            if eco_score_val == "High":
                reasons.append("superior carbon efficiency for this path")
            if reg_otp:
                reasons.append(f"exceptional on-time record on the {origin.title()} corridor")
            if "Value" in badge:
                reasons.append("best price-to-comfort ratio identified for today")
                
            if not reasons:
                ai_msg = f"SmartBus AI identified this as a consistent and highly reliable choice for your journey to {dest.title()}."
            else:
                ai_msg = f"This bus is selected for its {', '.join(reasons[:-1])}{' and ' + reasons[-1] if len(reasons) > 1 else reasons[0]}. It is the optimal transit solution for {travel_date}."

            buses.append({
                'id': f"bus_{bus.id}",
                'schedule_id': schedule.id,
                'operator': f"SmartTravel {bus.bus_number}",
                'type': bus.type,
                'fare': round(bus_fare, 2),
                'badge': badge,
                'confidence': random.randint(88, 98),
                'carbon_footprint': {
                    'bus_co2': bus.base_carbon_emission_per_km * 500, # mock distance
                    'car_co2': 60.0,
                    'train_co2': 15.0,
                    'eco_score': eco_score_val,
                    'badge': '🌱 Green Choice' if eco_score_val == 'High' else 'Standard'
                },
                'safety_index': {
                    'overall_score': safety_score,
                    'driver_reliability': random.randint(92, 99),
                    'maintenance_score': random.randint(88, 96),
                    'night_travel_safety': random.randint(85, 94),
                    'women_safety_index': random.randint(90, 98)
                },
                'overall_safety': safety_score,
                'delay': {
                    'on_time_probability': otp,
                    'simulated_delay_mins': schedule.projected_delay_mins,
                    'reliability_trend': [random.randint(80, 99) for _ in range(5)]
                },
                'ai_reasoning': ai_msg,
                'departure_time': schedule.departure_time.strftime('%H:%M'),
                'arrival_time': schedule.arrival_time.strftime('%H:%M'),
                'duration': str(schedule.arrival_time - schedule.departure_time).split('.')[0]
            })
        
        return jsonify({
            'optimizer': optimizer,
            'buses': buses
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@optimizer_bp.route('/optimize-split-route', methods=['POST'])
def explicit_split_route():
    data = request.json or {}
    origin = data.get('source')
    dest = data.get('destination')
    date_str = data.get('date')
    
    if not origin or not dest or not date_str:
        return jsonify({"error": "Missing required parameters (source, destination, date)"}), 400
        
    try:
        travel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
    result = split_optimizer_service.optimize_split_route(origin, dest, travel_date)
    return jsonify(result), 200

@optimizer_bp.route('/seats', methods=['GET'])
def get_seats():
    bus_type = request.args.get('type', 'Seater')
    schedule_id = request.args.get('schedule_id', type=int)
    is_sleeper = 'Sleeper' in bus_type
    
    booked_seats = set()
    if schedule_id:
        from app.models.booking import Booking
        confirmed = Booking.query.filter_by(schedule_id=schedule_id, status='Confirmed').all()
        booked_seats = {b.seat_number for b in confirmed}
        
    seat_map = []
    
    if is_sleeper:
        # Generate 2 Decks for Sleeper
        for deck in ['Lower', 'Upper']:
            for row in range(1, 8): # Typically fewer rows for sleepers
                # 2 seats on one side, 1 on other (typical Indian sleeper)
                # Layout: SL (Single Left), DL1 (Double Right 1), DL2 (Double Right 2)
                configurations = [
                    {'id': f'L{row}', 'type': 'Single Berth', 'align': 'left'},
                    {'id': f'R{row}A', 'type': 'Double Berth', 'align': 'right'},
                    {'id': f'R{row}B', 'type': 'Double Berth', 'align': 'right'}
                ]
                for config in configurations:
                    id_full = f"{deck[0]}{config['id']}"
                    zone = 'Front' if row <= 2 else ('Middle' if row <= 5 else 'Back')
                    available = id_full not in booked_seats
                    
                    seat_map.append({
                        'id': id_full,
                        'deck': deck,
                        'type': config['type'],
                        'zone': zone,
                        'noise_db': random.randint(30, 70),
                        'vibration': 'Medium',
                        'available': available,
                        'align': config['align']
                    })
    else:
        # Standard Seater layout
        for row in range(1, 11):
            for col in ['W1', 'A1', 'A2', 'W2']:
                is_window = 'W' in col
                zone = 'Front' if row <= 3 else ('Middle' if row <= 7 else 'Back')
                noise = random.randint(20, 40) if zone == 'Front' else (random.randint(40, 60) if zone == 'Middle' else random.randint(60, 80))
                vibration = 'Low' if zone == 'Front' else ('Medium' if zone == 'Middle' else 'High')
                seat_id = f'{row}{col}'
                available = seat_id not in booked_seats
                
                seat_map.append({
                    'id': seat_id,
                    'deck': 'Lower', # Seaters only have one deck
                    'type': 'Window' if is_window else 'Aisle',
                    'zone': zone,
                    'noise_db': noise,
                    'vibration': vibration,
                    'available': available
                })
                
    return jsonify(seat_map), 200


@optimizer_bp.route('/chat', methods=['POST'])
def chat():
    from flask import session
    from app.models.booking import Booking
    from app.models.bus import BusSchedule, Bus, Route
    from app.models.metrics import SafetyMetrics, EcoMetrics
    
    data = request.json or {}
    query = data.get('message', '').strip().lower()
    
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    
    # 1. Booking History Query
    if any(k in query for k in ['booking', 'ticket', 'my journey', 'my trip', 'my seat']):
        if not user_id:
            return jsonify({
                'response': "🔒 **Access Restricted**\n\nI couldn't detect an active passenger session. Please click **Login** in the top right corner to verify your profile and securely access your ticket history."
            })
        
        bookings = Booking.query.filter_by(user_id=user_id, status='Confirmed').all()
        if not bookings:
            return jsonify({
                'response': f"Hello **{user_name}**! I successfully accessed your passenger records, but you don't have any confirmed travel tickets booked yet.\n\nReady to start your first trip? Search for your route on the home page and choose an AI-optimized seat!"
            })
        
        reply = f"Hi **{user_name}**! 🎫 I found **{len(bookings)}** confirmed booking(s) in your profile:\n\n"
        for idx, b in enumerate(bookings, 1):
            schedule = BusSchedule.query.get(b.schedule_id)
            route = schedule.route if schedule else None
            origin = route.origin.title() if route else "Hub"
            dest = route.destination.title() if route else "Hub"
            reply += f"{idx}. **{origin} ➔ {dest}**\n"
            reply += f"   * **Booking ID:** `#TXN-{b.id}`\n"
            reply += f"   * **Seat Number:** `Seat {b.seat_number}`\n"
            reply += f"   * **Fare Paid:** `₹{b.fare_paid}`\n"
            reply += f"   * **Status:** `Confirmed` ✅\n\n"
        reply += "Let me know if you need to optimize another route or view telemetry statistics!"
        return jsonify({'response': reply})
        
    # 2. Safety Query
    elif any(k in query for k in ['safe', 'reliability', 'accident', 'night travel']):
        top_safety = SafetyMetrics.query.order_by(SafetyMetrics.overall_score.desc()).first()
        if top_safety:
            bus = Bus.query.get(top_safety.bus_id)
            reply = f"🛡️ **Safety Telemetry Insights**\n\nThe safest asset in our fleet is **SmartTravel {bus.bus_number}** ({bus.type}) with a **Safety Rating of {top_safety.overall_score}%**!\n\n"
            reply += f"* **Driver Reliability:** `{top_safety.driver_reliability}%`\n"
            reply += f"* **Maintenance Condition:** `{top_safety.maintenance_score}%`\n"
            reply += f"* **Night Driving Safety:** `{top_safety.night_travel_safety}%`\n"
            reply += f"* **Women's Safety Index:** `{top_safety.women_safety_index}%`\n\n"
            reply += "Would you like me to recommend schedule paths utilizing this safe asset?"
        else:
            reply = "🛡️ **Safety Insights:** All fleet coaches undergo daily comprehensive safety checkups. Fleet safety indices are currently rated at **94.8%** above industry averages!"
        return jsonify({'response': reply})
        
    # 3. Eco Query
    elif any(k in query for k in ['green', 'eco', 'carbon', 'co2', 'nature']):
        top_eco = EcoMetrics.query.filter_by(eco_rating='High').first()
        reply = "🌱 **Eco & Environmental Analytics**\n\n"
        reply += "SmartBus AI optimizes route load factors to reduce carbon emissions by **up to 78%** compared to single-passenger car transit!\n\n"
        if top_eco:
            bus = Bus.query.get(top_eco.bus_id)
            reply += f"Our **{bus.type}** fleet is designated with a **High Eco Rating**, producing the lowest emission ratios per passenger seat. Choosing this green option saves approximately **12.5 kg of CO2** per 100km!"
        else:
            reply += "Look for the **🌱 Green Choice** badge on your search results to secure carbon-neutral seats."
        return jsonify({'response': reply})
        
    # 4. Greeting
    elif any(k in query for k in ['hi', 'hello', 'hey', 'greetings', 'who are you', 'help']):
        name_str = f" **{user_name}**" if user_name else " there"
        reply = f"👋 Hello{name_str}! I am your **SmartBus AI Travel Concierge**.\n\n"
        reply += "I can assist you with:\n"
        reply += "* 🔍 **Finding optimal routes** and cheapest days to travel.\n"
        reply += "* 🛡️ **Accessing safety ratings** and fleet telemetry.\n"
        reply += "* 🌱 **Reducing your carbon footprint** using green optimization.\n"
        reply += "* 🎫 **Retrieving your booking history** directly from our secure database.\n\n"
        reply += "How can I enhance your journey today?"
        return jsonify({'response': reply})
        
    # 5. Default Response
    else:
        reply = f"I've processed your query: *\"{data.get('message')}\"*.\n\n"
        reply += "As your AI companion, I am actively analyzing route parameters, fleet asset safety scores, and fuel efficiencies to find you the best value. Let me know if you would like me to list your tickets, display the safest bus, or show eco ratings!"
        return jsonify({'response': reply})
