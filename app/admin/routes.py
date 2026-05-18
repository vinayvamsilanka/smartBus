from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from functools import wraps
from app.extensions import db, bcrypt
from app.models import User, City, Bus, GraphRoute, FareHistory, SafetyMetrics, EcoMetrics, Booking
from app.admin.services import admin_service
from . import admin_ui_bp
import time
from sqlalchemy import func

# Simple Rate Limiter Dictionary
LOGIN_ATTEMPTS = {}

def check_rate_limit(ip):
    now = time.time()
    attempts = LOGIN_ATTEMPTS.get(ip, [])
    # Remove attempts older than 5 mins
    attempts = [t for t in attempts if now - t < 300]
    LOGIN_ATTEMPTS[ip] = attempts
    if len(attempts) >= 5:
        return False
    return True

def add_rate_limit(ip):
    now = time.time()
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = []
    LOGIN_ATTEMPTS[ip].append(now)

# Middleware Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_ui.login', next=request.url))
        if not admin_service.is_authorized(session['admin_id']):
            flash('Unauthorized access.', 'error')
            return redirect(url_for('admin_ui.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session or not admin_service.is_authorized(session['admin_id'], roles):
                flash('Insufficient permissions to access this module.', 'error')
                return redirect(url_for('admin_ui.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Inject User Context to Templates
@admin_ui_bp.context_processor
def inject_user():
    user = None
    if 'admin_id' in session:
        user = User.query.get(session['admin_id'])
    return dict(current_admin=user)

# ----------------- UTILITIES / API -----------------
@admin_ui_bp.route('/api/suggest-route', methods=['GET'])
@admin_required
def suggest_route_data():
    origin = request.args.get('origin', '').lower()
    dest = request.args.get('dest', '').lower()
    
    if not origin or not dest:
        return jsonify({"error": "Select cities"}), 400
        
    from app.services.split_optimizer import split_optimizer_service
    dist = split_optimizer_service._calculate_geodesic_distance(origin, dest)
    
    if dist:
        # Suggest a fare based on distance (₹1.8 per km + small noise)
        suggested_fare = round((dist * 1.55) + 50, -1) # Round to nearest 10
        return jsonify({
            "distance_km": round(dist, 1),
            "suggested_fare": max(250, suggested_fare)
        })
    
    return jsonify({"distance_km": 0, "suggested_fare": 0})

# ----------------- AUTHENTICATION -----------------

@admin_ui_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_id' in session:
        return redirect(url_for('admin_ui.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        client_ip = request.remote_addr
        
        if not check_rate_limit(client_ip):
            flash('Too many login attempts. Try again in 5 minutes.', 'error')
            return render_template('admin/login.html')

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if user.role and user.role.name in ['Super Admin', 'Operator', 'Analyst']:
                session['admin_id'] = user.id
                admin_service.log_action(user.id, "Logged in to Admin Panel", ip_address=client_ip)
                flash('Login successful', 'success')
                return redirect(url_for('admin_ui.dashboard'))
        
        add_rate_limit(client_ip)
        flash('Invalid credentials or insufficient privileges.', 'error')
        admin_service.log_action(user.id if user else None, "Failed Login Attempt", ip_address=client_ip)

    return render_template('admin/login.html')

@admin_ui_bp.route('/logout')
def logout():
    if 'admin_id' in session:
        admin_service.log_action(session['admin_id'], "Logged out", ip_address=request.remote_addr)
        session.pop('admin_id', None)
    flash('Successfully logged out.', 'success')
    return redirect(url_for('admin_ui.login'))

# ----------------- DASHBOARD -----------------
@admin_ui_bp.route('/')
@admin_ui_bp.route('/dashboard')
@admin_required
def dashboard():
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(func.sum(Booking.fare_paid)).filter(Booking.status=='Confirmed').scalar() or 0
    total_buses = Bus.query.count()
    from app.models.bus import Route, BusSchedule
    total_cities = City.query.count()
    total_routes = Route.query.count()
    active_schedules = BusSchedule.query.filter_by(is_active=True).count()
    
    return render_template('admin/dashboard.html', 
                            t_users=total_users, 
                            t_bookings=total_bookings, 
                            t_revenue=round(total_revenue, 2),
                            t_buses=total_buses,
                            t_cities=total_cities,
                            t_routes=total_routes,
                            t_schedules=active_schedules)

# ----------------- CITIES MODULE -----------------
@admin_ui_bp.route('/cities', methods=['GET'])
@admin_required
@role_required('Super Admin', 'Operator')
def manage_cities():
    cities = City.query.order_by(City.id.desc()).all()
    return render_template('admin/cities.html', cities=cities)

@admin_ui_bp.route('/cities/add', methods=['POST'])
@admin_required
@role_required('Super Admin')
def add_city():
    name = request.form.get('name').strip()
    if City.query.filter_by(name=name.lower()).first():
        flash('City already exists.', 'error')
    else:
        city = City(name=name.lower())
        db.session.add(city)
        db.session.commit()
        admin_service.log_action(session['admin_id'], f"Added City: {name}", "cities", city.id)
        flash(f'City {name} added successfully.', 'success')
    return redirect(url_for('admin_ui.manage_cities'))

@admin_ui_bp.route('/cities/delete/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin')
def delete_city(id):
    city = City.query.get_or_404(id)
    name = city.name
    # Soft Delete
    city.is_active = False
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Soft Deleted City: {name}", "cities", id)
    flash(f'{name.title()} deactivated and soft-deleted.', 'success')
    return redirect(url_for('admin_ui.manage_cities'))

@admin_ui_bp.route('/cities/toggle/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def toggle_city(id):
    city = City.query.get_or_404(id)
    city.is_active = not city.is_active
    db.session.commit()
    status = "Activated" if city.is_active else "Deactivated"
    admin_service.log_action(session['admin_id'], f"{status} City: {city.name}", "cities", id)
    flash(f'City {city.name.title()} {status.lower()} successfully.', 'success')
    return redirect(url_for('admin_ui.manage_cities'))

# ----------------- ROUTE ENGINE MODULE -----------------
@admin_ui_bp.route('/routes', methods=['GET'])
@admin_required
@role_required('Super Admin', 'Operator')
def manage_routes():
    from app.models.bus import Route
    routes = Route.query.order_by(Route.id.desc()).all()
    cities = City.query.filter_by(is_active=True).all()
    return render_template('admin/routes.html', routes=routes, cities=cities)

@admin_ui_bp.route('/routes/add', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def add_route():
    from app.models.bus import Route
    origin = request.form.get('origin')
    dest = request.form.get('destination')
    dist = request.form.get('distance', type=float)
    fare = request.form.get('base_fare', type=float)
    
    if origin.lower() == dest.lower():
        flash('Origin and Destination cannot be identical.', 'error')
        return redirect(url_for('admin_ui.manage_routes'))
        
    route = Route(origin=origin.lower(), destination=dest.lower(), distance_km=dist, base_fare=fare)
    db.session.add(route)
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Added Route: {origin} to {dest}", "routes", route.id)
    flash(f'Route {origin.title()} → {dest.title()} created.', 'success')
    return redirect(url_for('admin_ui.manage_routes'))

@admin_ui_bp.route('/routes/toggle/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def toggle_route(id):
    from app.models.bus import Route
    route = Route.query.get_or_404(id)
    route.is_active = not route.is_active
    db.session.commit()
    status = "Live" if route.is_active else "Suspended"
    admin_service.log_action(session['admin_id'], f"{status} Route: {route.origin} to {route.destination}", "routes", id)
    flash(f'Route status set to {status}.', 'success')
    return redirect(url_for('admin_ui.manage_routes'))

@admin_ui_bp.route('/routes/edit/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def edit_route(id):
    from app.models.bus import Route
    route = Route.query.get_or_404(id)
    
    dist = request.form.get('distance', type=float)
    fare = request.form.get('base_fare', type=float)
    
    if dist is not None:
        route.distance_km = dist
    if fare is not None:
        route.base_fare = fare
        
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Updated Route {id}: {dist}km, ₹{fare}", "routes", id)
    flash('Route updated successfully.', 'success')
    return redirect(url_for('admin_ui.manage_routes'))

@admin_ui_bp.route('/routes/delete/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin')
def delete_route(id):
    from app.models.bus import Route
    route = Route.query.get_or_404(id)
    route.is_active = False # Soft delete
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Soft Deleted Route ID: {id}", "routes", id)
    flash(f'Route archived (Soft Delete).', 'success')
    return redirect(url_for('admin_ui.manage_routes'))

# ----------------- BUSES MODULE -----------------
@admin_ui_bp.route('/buses', methods=['GET'])
@admin_required
@role_required('Super Admin', 'Operator')
def manage_buses():
    buses = Bus.query.order_by(Bus.id.desc()).all()
    return render_template('admin/buses.html', buses=buses)

@admin_ui_bp.route('/buses/add', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def add_bus():
    bus_num = request.form.get('bus_number')
    b_type = request.form.get('type')
    cap = request.form.get('capacity', 40, type=int)
    
    bus = Bus(bus_number=bus_num, type=b_type, capacity=cap)
    db.session.add(bus)
    db.session.flush() # get id
    
    # Initialize basic metrics
    sm = SafetyMetrics(bus_id=bus.id, driver_score=90, maintenance_score=90, night_safety=90, women_safety=90, overall_score=90)
    em = EcoMetrics(bus_id=bus.id, co2_emissions_per_km=0.04)
    db.session.add(sm)
    db.session.add(em)
    
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Added Bus: {bus_num}", "buses", bus.id)
    flash(f'Bus {bus_num} tracked.', 'success')
    return redirect(url_for('admin_ui.manage_buses'))

@admin_ui_bp.route('/buses/edit/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def edit_bus(id):
    bus = Bus.query.get_or_404(id)
    bus.bus_number = request.form.get('bus_number')
    bus.type = request.form.get('type')
    bus.capacity = request.form.get('capacity', type=int)
    
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Updated Bus ID {id}: {bus.bus_number}", "buses", id)
    flash(f'Bus {bus.bus_number} updated.', 'success')
    return redirect(url_for('admin_ui.manage_buses'))

@admin_ui_bp.route('/buses/delete/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin')
def delete_bus(id):
    bus = Bus.query.get_or_404(id)
    # Soft Delete
    bus.is_active = False
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Soft Deleted Bus: {bus.bus_number}", "buses", id)
    flash(f'Bus decommissioned (Soft Delete).', 'success')
    return redirect(url_for('admin_ui.manage_buses'))

@admin_ui_bp.route('/buses/toggle/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def toggle_bus(id):
    bus = Bus.query.get_or_404(id)
    bus.is_active = not bus.is_active
    db.session.commit()
    status = "Active" if bus.is_active else "Inactive"
    admin_service.log_action(session['admin_id'], f"Set Bus {bus.bus_number} to {status}", "buses", id)
    flash(f'Bus {bus.bus_number} status updated to {status}.', 'success')
    return redirect(url_for('admin_ui.manage_buses'))

@admin_ui_bp.route('/buses/telemetry/<int:id>', methods=['GET', 'POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def bus_telemetry(id):
    bus = Bus.query.get_or_404(id)
    sm = SafetyMetrics.query.filter_by(bus_id=id).first()
    em = EcoMetrics.query.filter_by(bus_id=id).first()
    
    if request.method == 'POST':
        driver = request.form.get('driver_score', 90, type=int)
        maint = request.form.get('maintenance_score', 90, type=int)
        night = request.form.get('night_safety', 90, type=int)
        women = request.form.get('women_safety', 90, type=int)
        co2 = request.form.get('co2_emissions', 0.04, type=float)
        
        if not sm:
            sm = SafetyMetrics(bus_id=id)
            db.session.add(sm)
        sm.driver_score = driver
        sm.maintenance_score = maint
        sm.night_safety = night
        sm.women_safety = women
        sm.overall_score = round((driver + maint + night + women) / 4)
        
        if not em:
            em = EcoMetrics(bus_id=id)
            db.session.add(em)
        em.co2_emissions_per_km = co2
        em.eco_rating = 'High' if co2 < 0.03 else ('Medium' if co2 <= 0.06 else 'Low')
        
        db.session.commit()
        admin_service.log_action(session['admin_id'], f"Updated Telemetry metrics for Bus {bus.bus_number}", "buses", id)
        flash(f'Telemetry metrics updated for {bus.bus_number}.', 'success')
        return redirect(url_for('admin_ui.manage_buses'))
        
    return jsonify({
        "bus_number": bus.bus_number,
        "driver_score": sm.driver_score if sm else 90,
        "maintenance_score": sm.maintenance_score if sm else 90,
        "night_safety": sm.night_safety if sm else 90,
        "women_safety": sm.women_safety if sm else 90,
        "co2_emissions": em.co2_emissions_per_km if em else 0.04
    }), 200

# ----------------- SCHEDULES MODULE -----------------
@admin_ui_bp.route('/schedules', methods=['GET'])
@admin_required
@role_required('Super Admin', 'Operator')
def manage_schedules():
    from app.models.bus import BusSchedule, Bus, Route
    from datetime import datetime
    schedules = BusSchedule.query.order_by(BusSchedule.departure_time.desc()).all()
    buses = Bus.query.filter_by(is_active=True).all()
    routes = Route.query.filter_by(is_active=True).all()
    return render_template('admin/schedules.html', 
                            schedules=schedules, 
                            buses=buses, 
                            routes=routes,
                            now=datetime.utcnow())

@admin_ui_bp.route('/schedules/add', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def add_schedule():
    from app.models.bus import BusSchedule
    from datetime import datetime
    bus_id = request.form.get('bus_id', type=int)
    route_id = request.form.get('route_id', type=int)
    dep_str = request.form.get('departure')
    arr_str = request.form.get('arrival')
    
    try:
        departure = datetime.fromisoformat(dep_str)
        arrival = datetime.fromisoformat(arr_str)
    except ValueError:
        flash('Invalid date/time format.', 'error')
        return redirect(url_for('admin_ui.manage_schedules'))
        
    if arrival <= departure:
        flash('Arrival must be after departure.', 'error')
        return redirect(url_for('admin_ui.manage_schedules'))
        
    sch = BusSchedule(bus_id=bus_id, route_id=route_id, departure_time=departure, arrival_time=arrival)
    db.session.add(sch)
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Scheduled Dispatch ID: {sch.id}", "schedules", sch.id)
    flash(f'Dispatch scheduled successfully.', 'success')
    return redirect(url_for('admin_ui.manage_schedules'))

@admin_ui_bp.route('/schedules/toggle/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin', 'Operator')
def toggle_schedule(id):
    from app.models.bus import BusSchedule
    sch = BusSchedule.query.get_or_404(id)
    sch.is_active = not sch.is_active
    db.session.commit()
    status = "Active" if sch.is_active else "Cancelled"
    admin_service.log_action(session['admin_id'], f"Toggled Schedule {id} to {status}", "schedules", id)
    flash(f'Schedule status set to {status}.', 'success')
    return redirect(url_for('admin_ui.manage_schedules'))

@admin_ui_bp.route('/schedules/delete/<int:id>', methods=['POST'])
@admin_required
@role_required('Super Admin')
def delete_schedule(id):
    from app.models.bus import BusSchedule
    sch = BusSchedule.query.get_or_404(id)
    sch.is_active = False # Soft delete
    db.session.commit()
    admin_service.log_action(session['admin_id'], f"Soft Deleted Schedule ID: {id}", "schedules", id)
    flash(f'Dispatch archived (Soft Delete).', 'success')
    return redirect(url_for('admin_ui.manage_schedules'))
