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

@tracking_bp.route('/notify-email', methods=['POST'])
def notify_email():
    from flask import request, session, current_app
    from app.models import User
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        data = request.json
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        
        # Determine recipient
        to_email = user.email if user else 'traveler@smartbus.ai'
        
        # Get SMTP config
        sender_email = current_app.config.get('MAIL_USERNAME')
        sender_password = current_app.config.get('MAIL_PASSWORD')
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = current_app.config.get('MAIL_PORT')

        if not sender_email or not sender_password:
            return jsonify({"success": False, "error": "SMTP config missing"}), 500

        # Construct email content
        subject = f"SmartBus AI - Dispatch Insights & Delay Alert for Bus #{data.get('bus_id', 'N/A')}"
        
        reasons_html = "".join([f"<li>{r}</li>" for r in data.get('reasons', [])])
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #6366f1; border-bottom: 2px solid #eee; padding-bottom: 10px;">SmartBus AI - Dispatch Insights</h2>
                
                <p>Hello,</p>
                <p>Here is your requested telemetry and delay forecast for your tracked journey.</p>
                
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #475569;">Forecast Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Scheduled Arrival:</strong></td><td style="text-align: right; border-bottom: 1px solid #eee;">{data.get('scheduled_arrival', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>AI-Adjusted ETA:</strong></td><td style="text-align: right; border-bottom: 1px solid #eee; font-weight: bold; color: #ef4444;">{data.get('adjusted_arrival', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Predicted Delay:</strong></td><td style="text-align: right; border-bottom: 1px solid #eee; color: #ef4444;">{data.get('delay_minutes', 0)} mins</td></tr>
                        <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Traffic Congestion:</strong></td><td style="text-align: right; border-bottom: 1px solid #eee;">{data.get('congestion', 'N/A')}</td></tr>
                        <tr><td style="padding: 8px 0;"><strong>AI Confidence:</strong></td><td style="text-align: right;">{data.get('ai_confidence_score', 'N/A')}%</td></tr>
                    </table>
                </div>

                <h3 style="color: #475569;">Congestion Factors</h3>
                <ul style="color: #64748b;">
                    {reasons_html}
                </ul>
                
                <p style="margin-top: 30px; font-size: 0.9em; color: #94a3b8; text-align: center;">
                    <em>Thank you for traveling with SmartBus AI. Travel Safe!</em>
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SmartBus AI <{sender_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return jsonify({"success": True, "email": to_email})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
