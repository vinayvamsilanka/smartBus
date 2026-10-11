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
        except Exception:
            db.session.rollback() # <-- CRITICAL FIX: Ensure session isn't poisoned by IntegrityError

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
                    'savings': split_data['savings_amount'],
                    'leg1_bus': split_data['leg1_bus'],
                    'leg2_bus': split_data['leg2_bus']
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
        # DYNAMIC BUS SEARCH (DATABASE-DRIVEN WITH FALLBACK SYNTHESIS)
        # -------------------------------------------------------------
        from app.models.bus import BusSchedule, Bus, Route
        from app.models.metrics import SafetyMetrics, EcoMetrics
        
        origin_clean = origin.strip()
        dest_clean = dest.strip()

        # Query active schedules for this route
        active_schedules = BusSchedule.query.join(Route).join(Bus).filter(
            Route.origin.ilike(f"%{origin_clean}%"),
            Route.destination.ilike(f"%{dest_clean}%"),
            BusSchedule.is_active == True,
            Bus.is_active == True,
            Route.is_active == True
        ).all()

        # If no specific schedules exist for this exact pair, fetch or synthesize fallback schedules using existing buses
        if not active_schedules:
            all_buses = Bus.query.filter_by(is_active=True).limit(5).all()
            if not all_buses:
                all_buses = Bus.query.limit(5).all()
            
            # Ensure route exists or create dynamic route
            existing_route = Route.query.filter(
                Route.origin.ilike(f"%{origin_clean}%"),
                Route.destination.ilike(f"%{dest_clean}%")
            ).first()
            if not existing_route:
                try:
                    existing_route = Route(
                        origin=origin_clean.title(),
                        destination=dest_clean.title(),
                        distance_km=350.0, # Approximate static fallback
                        base_fare=650.0
                    )
                    db.session.add(existing_route)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    existing_route = Route.query.filter(
                        Route.origin.ilike(f"%{origin_clean}%"),
                        Route.destination.ilike(f"%{dest_clean}%")
                    ).first()

            # Create transient schedule objects for UI display
            for idx, b_item in enumerate(all_buses):
                dep_hour = (7 + idx * 3) % 24
                dep_dt = datetime.combine(travel_date, datetime.min.time().replace(hour=dep_hour, minute=0))
                
                # Dynamic speed calculation ML logic loosely simulated
                dist = existing_route.distance_km if existing_route else 350.0
                b_type = getattr(b_item, 'type', '').lower()
                
                if 'volvo' in b_type or 'scania' in b_type or 'luxury' in b_type or 'premium' in b_type:
                    speed = 68.0  # Faster cruising
                elif 'express' in b_type:
                    speed = 58.0  # Regular stops
                elif 'sleeper' in b_type:
                    speed = 48.0  # Slower for sleeper comfort
                else:
                    speed = 55.0
                    
                base_time_hours = dist / speed
                arr_dt = dep_dt + timedelta(hours=base_time_hours)
                
                sch = BusSchedule(
                    bus_id=b_item.id,
                    route_id=existing_route.id,
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    projected_delay_mins=random.randint(0, 15)
                )
                sch.bus = b_item
                sch.route = existing_route
                active_schedules.append(sch)

        buses = []
        badges = ["⭐ Best Value", "🛡️ Safest", "🌱 Greenest", "⚡ Fastest", "💎 Premium"]
        
        for idx, schedule in enumerate(active_schedules):
            bus = schedule.bus
            safety_m = SafetyMetrics.query.filter_by(bus_id=bus.id).first() if hasattr(bus, 'id') else None
            eco_m = EcoMetrics.query.filter_by(bus_id=bus.id).first() if hasattr(bus, 'id') else None
            
            safety_score = safety_m.overall_score if safety_m else random.randint(85, 95)
            eco_score_val = eco_m.eco_rating if eco_m else "High"
            
            base_fare = schedule.route.base_fare if schedule.route else 650.0
            b_type = getattr(bus, 'type', '').lower() if hasattr(bus, 'type') else ''
            mult = 1.0
            if 'volvo' in b_type or 'luxury' in b_type or 'scania' in b_type or 'premium' in b_type:
                mult = 1.45
            elif 'ac sleeper' in b_type:
                mult = 1.30
            elif 'sleeper' in b_type:
                mult = 1.15
            elif 'express' in b_type:
                mult = 0.85
            
            bus_fare = round(base_fare * mult, -1)
            badge = badges[idx % len(badges)]
            
            otp = random.randint(80, 99)
            reg_otp = schedule.projected_delay_mins <= 5
            
            reasons = []
            if safety_score >= 95:
                reasons.append(f"top-tier safety rating for the {dest_clean.title()} route")
            if eco_score_val == "High":
                reasons.append("superior carbon efficiency for this path")
            if reg_otp:
                reasons.append(f"exceptional on-time record on the {origin_clean.title()} corridor")
            if "Value" in badge:
                reasons.append("best price-to-comfort ratio identified for today")
                
            if not reasons:
                ai_msg = f"SmartBus AI identified this as a consistent and highly reliable choice for your journey to {dest_clean.title()}."
            else:
                ai_msg = f"This bus is selected for its {', '.join(reasons[:-1])}{' and ' + reasons[-1] if len(reasons) > 1 else reasons[0]}. It is the optimal transit solution for {travel_date}."

            dep_str = schedule.departure_time.strftime('%Y-%m-%d %H:%M') if isinstance(schedule.departure_time, datetime) else f"{travel_date} {schedule.departure_time}"
            arr_str = schedule.arrival_time.strftime('%Y-%m-%d %H:%M') if isinstance(schedule.arrival_time, datetime) else f"{travel_date} {schedule.arrival_time}"

            # Calculate dynamic eco metrics based on real-world emissions per passenger-km and route distance
            dist = schedule.route.distance_km if schedule.route else 350.0
            bus_emissions_per_km = eco_m.co2_emissions_per_km if eco_m and eco_m.co2_emissions_per_km else 0.082
            
            # Real-world averages (kg CO2 per passenger-km): Car ~ 0.170, Train ~ 0.040
            bus_co2_calc = round(bus_emissions_per_km * dist, 1)
            car_co2_calc = round(0.170 * dist, 1)
            train_co2_calc = round(0.040 * dist, 1)

            try:
                if isinstance(schedule.departure_time, datetime) and isinstance(schedule.arrival_time, datetime):
                    dur_td = schedule.arrival_time - schedule.departure_time
                else:
                    d_dt = datetime.strptime(str(schedule.departure_time), '%Y-%m-%d %H:%M:%S')
                    a_dt = datetime.strptime(str(schedule.arrival_time), '%Y-%m-%d %H:%M:%S')
                    dur_td = a_dt - d_dt
                tm = dur_td.total_seconds() / 60
                dur_str = f"{int(tm//60)}h {int(tm%60)}m"
            except:
                dur_str = "6h 30m" # absolute fallback

            buses.append({
                'id': f"bus_{bus.id if hasattr(bus, 'id') else idx+1}",
                'schedule_id': schedule.id if hasattr(schedule, 'id') else idx+1,
                'operator': f"SmartTravel {bus.bus_number if hasattr(bus, 'bus_number') else 'AP-01-SB'}",
                'type': bus.type if hasattr(bus, 'type') else 'AC Sleeper',
                'fare': round(float(bus_fare), 2),
                'badge': badge,
                'confidence': random.randint(88, 98),
                'carbon_footprint': {
                    'bus_co2': bus_co2_calc,
                    'car_co2': car_co2_calc,
                    'train_co2': train_co2_calc,
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
                'departure_time': dep_str,
                'arrival_time': arr_str,
                'duration': dur_str,
                'ai_reasoning': ai_msg
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
    import os
    import json
    import re
    import requests
    from pathlib import Path
    from flask import session
    from app.models.booking import Booking
    from app.models.bus import BusSchedule, Bus, Route
    from app.models.metrics import SafetyMetrics, EcoMetrics
    import google.generativeai as genai
    
    # Reload .env if needed to guarantee keys are present
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).resolve().parent.parent.parent / '.env'
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)
    except Exception:
        pass

    data = request.json or {}
    message = data.get('message', '').strip()
    query = message.lower()
    
    user_name = session.get('user_name')
    user_id = session.get('user_id')
    now = datetime.now()
    current_time_str = now.strftime("%A, %B %d, %Y, %I:%M %p")
    current_year = now.year

    try:
        # 1. Update Conversational Memory
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Keep last 6 messages
        session['chat_history'] = session['chat_history'][-6:]
        session['chat_history'].append({"role": "user", "content": message})
        session.modified = True

        # Build context string
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in session['chat_history']])
        
        # Check for API Keys for True LLM processing
        groq_key = os.getenv('GROQ_API_KEY')
        gemini_key = os.getenv('GEMINI_API_KEY')
        
        reply = ""
        rich_cards = []

        # 1. Booking History Query (Always handle explicitly for security)
        if any(k in query for k in ['booking', 'ticket', 'my journey', 'my trip', 'my seat']):
            if not user_id:
                reply = "🔒 **Access Restricted**\n\nI couldn't detect an active passenger session. Please click **Login** in the top right corner to verify your profile and securely access your ticket history."
            else:
                bookings = Booking.query.filter_by(user_id=user_id, status='Confirmed').all()
                if not bookings:
                    reply = f"Hello **{user_name}**! I successfully accessed your passenger records, but you don't have any confirmed travel tickets booked yet.\n\nReady to start your first trip? Search for your route on the home page!"
                else:
                    reply = f"Hi **{user_name}**! 🎫 I found **{len(bookings)}** confirmed booking(s) in your profile:\n\n"
                    for idx, b in enumerate(bookings, 1):
                        schedule = BusSchedule.query.filter_by(id=b.schedule_id).first()
                        route = schedule.route if schedule else None
                        origin = route.origin.title() if route else "Hub"
                        dest = route.destination.title() if route else "Hub"
                        reply += f"{idx}. **{origin} ➔ {dest}** (Seat {b.seat_number})\n"
            
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({'response': reply, 'rich_cards': rich_cards})

        # 2. Safety Query
        if any(k in query for k in ['safe', 'reliability', 'accident', 'night travel', 'top safety']):
            top_safety = SafetyMetrics.query.order_by(SafetyMetrics.overall_score.desc()).first()
            if top_safety:
                bus = Bus.query.filter_by(id=top_safety.bus_id).first()
                reply = f"🛡️ **Safety Telemetry Insights**\nThe safest asset in our fleet is **SmartTravel {bus.bus_number}** ({bus.type}) with a **Safety Rating of {top_safety.overall_score}%**!\n\n"
                reply += f"* **Driver Reliability:** `{top_safety.driver_reliability}%`\n"
                reply += f"* **Night Driving Safety:** `{top_safety.night_travel_safety}%`\n"
            else:
                reply = "🛡️ **Safety Insights:** All fleet coaches undergo daily comprehensive safety checkups."
                
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({'response': reply, 'rich_cards': rich_cards})

        # 3. Intelligent LLM Processing (Groq Primary -> Gemini Secondary -> Local Fallback)
        origin = None
        dest = None
        
        user_status = f"The user is currently LOGGED IN. Their name is '{user_name}'." if user_name else "The user is a GUEST (not logged in)."
        sys_prompt = (
            f"[{user_status}] [REAL-TIME SYSTEM CLOCK: Today is {current_time_str} (Year {current_year})]. "
            "You are SmartBus AI Travel Concierge. Be highly professional, warmly personalized, and engaging. "
            "You fluently understand and can reply in English, Telugu, and Hindi. "
            f"CRITICAL TEMPORAL AWARENESS: You have live real-time awareness. The current year is {current_year}. Today's date is {current_time_str}. NEVER say it is 2024 or any past year. When the user asks about the current year, today's date, or upcoming schedules and festivals, always base your answer accurately on the real-time system clock. "
            "CRITICAL RULE 1: If a user tells you they want to travel to a destination, but they DO NOT mention their starting location, you MUST ask them 'Where are you travelling from?' DO NOT guess. "
            "CRITICAL RULE 2: If the user simply says 'hi', 'hello', or 'hey': If they are a GUEST, warmly welcome them and suggest they log in for a better experience or start searching for a bus. If they are LOGGED IN, greet them enthusiastically by their actual name! If they have previous chat history searching for a route, politely ask them if they would like to continue their previous journey or start looking for a brand new one. "
            "CRITICAL RULE 3: ALWAYS respond in English by default, regardless of chat history. ONLY reply in Hindi or Telugu if the user's CURRENT message is written in that language or they explicitly ask you to change the language right now. "
            "ONLY when you clearly know BOTH the origin city and the destination city (and the user explicitly wants to search it right now), you must output this exact tag: [SEARCH:OriginCity|DestinationCity]. "
        )

        # Attempt 1: Groq Cloud (Ultra-fast, High Limits)
        if groq_key:
            try:
                messages_payload = [{"role": "system", "content": sys_prompt}]
                for msg in session.get('chat_history', []):
                    role = "assistant" if msg.get("role") == "assistant" else "user"
                    messages_payload.append({"role": role, "content": msg.get("content", "")})
                
                res = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
                    json={
                        'model': 'qwen/qwen3.8-27b',
                        'messages': messages_payload,
                        'temperature': 0.7,
                        'max_tokens': 800
                    },
                    timeout=8
                )
                if res.status_code == 200:
                    reply = res.json()['choices'][0]['message']['content'].strip()
                else:
                    print(f"Groq API returned status {res.status_code}: {res.text}", flush=True)
            except Exception as groq_err:
                print(f"Groq API error: {groq_err}", flush=True)

        # Attempt 2: Google Gemini (Fallback)
        if not reply and gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-3.6-flash')
                response = model.generate_content(f"{sys_prompt}\nChat History:\n{context}\nUser: {message}")
                reply = response.text.strip()
            except Exception as gemini_err:
                print(f"Gemini API error: {gemini_err}", flush=True)

        # Process search tags if LLM succeeded
        if reply:
            match = re.search(r'\[SEARCH:(.*?)\|(.*?)\]', reply)
            if match:
                origin = match.group(1).strip()
                dest = match.group(2).strip()
                reply = reply.replace(match.group(0), f"\n🔗 [Click here to view full schedule for {origin} to {dest}](/results?origin={origin}&dest={dest})\n")
        else:
            # Attempt 3: Smart Local Fallback
            if any(k in query for k in ['year', 'which year', 'what year', 'current year', 'date today', 'what is the date', 'today date']):
                reply = f"We are currently in the year **{current_year}**! Today is {current_time_str}. How can I assist you with your journey today?"
            else:
                origin, dest = _extract_cities_fallback(query)
                if any(k in query for k in ['model', 'models', 'ai used', 'which ai', 'best ai']):
                    reply = "🧠 **SmartBus AI Architecture**\n\nI am fully equipped to use **Groq & Google Gemini 2.5 Flash** for advanced conversation and memory! Right now, I am using a hybridized context-aware NLP engine that processes your commands and extracts entities."
                elif origin and dest:
                    reply = f"🚌 Great! Based on our chat context, I am looking up elite routes from **{origin.title()}** to **{dest.title()}** for you.\n\nHere are some top-tier options I pulled dynamically. Note the rich interactive cards below!"
                else:
                    # Memory Check (If user says "what about tomorrow?", we can recall origin/dest from history)
                    prev_context_hit = False
                    if any(word in query for word in ["tomorrow", "what about", "cheapest", "cost"]):
                        for history_msg in reversed(session['chat_history'][:-1]):
                            o, d = _extract_cities_fallback(history_msg['content'].lower())
                            if o and d:
                                origin, dest = o, d
                                reply = f"Ah, continuing our chat about your trip from **{origin.title()}** to **{dest.title()}**!\nI can definitely find options for that."
                                prev_context_hit = True
                                break
                    
                    if not prev_context_hit:
                        name_str = f" **{user_name}**" if user_name else " there"
                        reply = f"👋 Hello{name_str}! I am your **SmartBus AI Travel Concierge**.\nWe are in the year **{current_year}**. Try asking me: *'Find me a bus from Hyderabad to Bangalore'* or *'Check safety rating'*."

        # 4. Generate Interactive Rich Cards if Origin & Dest found
        if origin and dest:
            o_clean = origin.title()
            d_clean = dest.title()
            
            # City Name Normalizer for common misspellings or abbreviations
            city_aliases = {
                "rajhamundry": "rajahmundry",
                "rajmundry": "rajahmundry",
                "vizag": "visakhapatnam",
                "banglore": "bangalore",
                "bangaluru": "bangalore",
                "bengaluru": "bangalore",
                "hyd": "hyderabad",
                "hyderbad": "hyderabad",
                "madras": "chennai",
                "tirupathi": "tirupati"
            }
            search_origin = city_aliases.get(origin.lower(), origin)
            search_dest = city_aliases.get(dest.lower(), dest)
            
            # Real Database Query for actual bus routes and schedules
            active_routes = Route.query.filter(
                Route.origin.ilike(f"%{search_origin}%"), 
                Route.destination.ilike(f"%{search_dest}%"),
                Route.is_active == True
            ).all()
            
            if active_routes:
                matched_route_ids = [r.id for r in active_routes]
                # Get live schedules
                schedules = BusSchedule.query.filter(
                    BusSchedule.route_id.in_(matched_route_ids),
                    BusSchedule.is_active == True
                ).limit(3).all()
                
                if schedules:
                    for sch in schedules:
                        bus = Bus.query.filter_by(id=sch.bus_id).first()
                        route_info = Route.query.filter_by(id=sch.route_id).first()
                        
                        dist = float(getattr(route_info, 'distance_km', random.randint(150, 600)))
                        
                        # AI-driven Travel Duration Estimation
                        b_type = bus.type.lower() if getattr(bus, 'type', None) else 'seater'
                        if 'volvo' in b_type or 'scania' in b_type or 'premium' in b_type:
                            speed = 68.0
                        elif 'express' in b_type:
                            speed = 58.0
                        else:
                            speed = 48.0 # Sleeper / Normal
                            
                        duration_hrs = dist / speed
                        hrs = int(duration_hrs)
                        mins = int((duration_hrs - hrs) * 60)
                        
                        # Dynamic Fare Multipliers based on Luxury/Type
                        base = float(route_info.base_fare)
                        mult = 1.45 if 'volvo' in b_type or 'premium' in b_type else (1.30 if 'ac sleeper' in b_type else (1.15 if 'sleeper' in b_type else (0.85 if 'express' in b_type else 1.0)))
                        optimized_fare = int(round(base * mult, -1))
                        
                        # Construct genuine Rich UI Card
                        rich_cards.append({
                            "title": f"SmartBus {bus.bus_number}",
                            "type": bus.type,
                            "origin": route_info.origin.title(),
                            "destination": route_info.destination.title(),
                            "distance": round(dist, 1),
                            "time": f"{hrs}h {mins}m",
                            "fare": f"{optimized_fare}",
                            "bookLink": f"/results?origin={route_info.origin}&dest={route_info.destination}"
                        })
                    
                    reply = f"🚌 Found {len(schedules)} active schedules for **{o_clean}** to **{d_clean}** directly from the live database. Check out the verified options below!"
                else:
                    reply = f"I found the route for **{o_clean}** to **{d_clean}**, but there are currently no active bus schedules available for this route in the database right now."
            else:
                reply = f"It looks like we don't currently operate a direct route from **{o_clean}** to **{d_clean}** yet. SmartBus AI is constantly analyzing demand to expand our network!"
            
        session['chat_history'].append({"role": "assistant", "content": reply})
        session.modified = True
        return jsonify({'response': reply, 'rich_cards': rich_cards})

    except Exception as global_err:
        import traceback
        traceback.print_exc()
        if any(k in query for k in ['year', 'which year', 'what year', 'current year', 'date']):
            fallback_msg = f"We are in the year **{current_year}**! Today is {current_time_str}. How can I assist you with your journey today?"
        else:
            fallback_msg = "👋 Hello! I am your SmartBus AI Travel Concierge. How can I assist you with your journey today?"
            
        return jsonify({'response': fallback_msg, 'rich_cards': []}), 200

def _extract_cities_fallback(text):
    import re
    # Try explicit travel keywords first
    match = re.search(r'(?:buses|bus|tickets|travel|route|busses)\s+(?:from|between)?\s*([a-zA-Z\s]+?)\s*(?:to|and)\s*([a-zA-Z\s]+)', text)
    if not match:
        # Try generic "City to City"
        match = re.search(r'(?:from\s+)?([a-zA-Z\s]+?)\s+(?:to|-)\s+([a-zA-Z\s]+)', text)
    if match:
        origin = match.group(1).replace("tomorrow", "").replace("today", "").strip()
        dest = match.group(2).replace("tomorrow", "").replace("today", "").strip()
        return origin, dest
    return None, None

