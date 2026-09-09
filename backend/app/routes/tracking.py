from flask import Blueprint, jsonify
from app.models import BusSchedule
import time
import math

tracking_bp = Blueprint('tracking', __name__)

CITY_COORDINATES = {
    'hyderabad': [17.3850, 78.4867],
    'vijayawada': [16.5062, 80.6480],
    'guntur': [16.3067, 80.4365],
    'tirupati': [13.6285, 79.4192],
    'visakhapatnam': [17.6868, 83.2185],
    'vizianagaram': [18.1067, 83.3950],
    'nellore': [14.4426, 79.9865],
    'kurnool': [15.8281, 78.0373],
    'rajahmundry': [17.0005, 81.7835],
    'ongole': [15.5057, 80.0499],
    'warangal': [17.9689, 79.5941],
    'anantapur': [14.6819, 77.6006],
    'kadapa': [14.4673, 78.8242],
    'kakinada': [16.9891, 82.2475],
    'bangalore': [12.9716, 77.5946],
    'chennai': [13.0827, 80.2707],
    'mumbai': [19.0760, 72.8777],
    'pune': [18.5204, 73.8567],
    'mysore': [12.2958, 76.6394],
    'vellore': [12.9165, 79.1325],
    'chittoor': [13.2048, 79.1003],
    'eluru': [16.7107, 81.1030]
}

@tracking_bp.route('/live/<int:bus_id>', methods=['GET'])
def get_live_tracking(bus_id):
    """
    Simulates a live moving bus along the schedule route path.
    Returns current lat/lng based on the current timestamp.
    """
    origin_name = "bangalore"
    dest_name = "chennai"
    
    try:
        schedule = BusSchedule.query.filter_by(bus_id=bus_id, is_active=True).first()
        if not schedule:
            schedule = BusSchedule.query.filter_by(bus_id=bus_id).first()
            
        if schedule and schedule.route:
            origin_name = schedule.route.origin.lower()
            dest_name = schedule.route.destination.lower()
    except Exception as e:
        # Silently fall back to Bangalore-Chennai if DB query fails
        pass

    origin_coords = CITY_COORDINATES.get(origin_name, [12.9716, 77.5946])
    dest_coords = CITY_COORDINATES.get(dest_name, [13.0827, 80.2707])

    # 5 minute cycle
    cycle_time = 300 
    current_time = time.time()
    
    # Calculate progress (0.0 to 1.0)
    progress = (current_time % cycle_time) / cycle_time
    
    # Interpolate coordinates
    current_lat = origin_coords[0] + (dest_coords[0] - origin_coords[0]) * progress
    current_lng = origin_coords[1] + (dest_coords[1] - origin_coords[1]) * progress
    
    return jsonify({
        "bus_id": bus_id,
        "location": [current_lat, current_lng],
        "origin_coords": origin_coords,
        "dest_coords": dest_coords,
        "origin": origin_name.title(),
        "destination": dest_name.title(),
        "progress_percent": progress * 100,
        "speed_kmh": 65 + (math.sin(current_time) * 10), # Simulated speed variance
        "status": "On Route"
    }), 200

@tracking_bp.route('/predict-delay/<int:schedule_id>', methods=['GET'])
def predict_schedule_delay(schedule_id):
    try:
        from datetime import timedelta
        from app.models import BusSchedule, SafetyMetrics
        schedule = BusSchedule.query.get(schedule_id)
        if not schedule or not schedule.route:
            return jsonify({"error": "Schedule not found"}), 404
            
        distance = schedule.route.distance_km
        driver_score = 90
        safety = SafetyMetrics.query.filter_by(bus_id=schedule.bus_id).first()
        if safety:
            driver_score = safety.driver_score
            
        dep_hour = schedule.departure_time.hour
        
        from app.services.delay_predictor import delay_service
        result = delay_service.predict_delay(dep_hour, distance, driver_score)
        
        # Calculate dynamic arrival based on departure + delay
        scheduled_arrival = schedule.arrival_time
        ai_adjusted_arrival = scheduled_arrival + timedelta(minutes=result["delay_minutes"])
        
        return jsonify({
            "schedule_id": schedule_id,
            "distance_km": distance,
            "driver_score": driver_score,
            "congestion": result["congestion"],
            "reasons": result["reasons"],
            "delay_minutes": result["delay_minutes"],
            "ai_confidence_score": result["ai_confidence_score"],
            "scheduled_departure": schedule.departure_time.strftime('%I:%M %p'),
            "scheduled_arrival": scheduled_arrival.strftime('%I:%M %p'),
            "adjusted_arrival": ai_adjusted_arrival.strftime('%I:%M %p')
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
