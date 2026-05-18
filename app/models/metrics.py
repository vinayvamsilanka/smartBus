from app.extensions import db
from datetime import datetime

class SafetyMetrics(db.Model):
    __tablename__ = 'safety_metrics'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), unique=True, nullable=False)
    driver_score = db.Column(db.Integer, default=90)
    maintenance_score = db.Column(db.Integer, default=90)
    night_safety = db.Column(db.Integer, default=90)
    women_safety = db.Column(db.Integer, default=90)
    overall_score = db.Column(db.Integer, default=90)

class AnalyticsLogs(db.Model):
    __tablename__ = 'analytics_logs'
    id = db.Column(db.Integer, primary_key=True)
    endpoint_accessed = db.Column(db.String(200))
    user_id = db.Column(db.Integer, nullable=True) # Anonymous if None
    search_origin = db.Column(db.String(100), nullable=True)
    search_dest = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class EcoMetrics(db.Model):
    __tablename__ = 'eco_metrics'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), unique=True, nullable=False)
    co2_emissions_per_km = db.Column(db.Float, default=0.04) # kg/km
    eco_rating = db.Column(db.String(20), default='Medium')
    waste_management_score = db.Column(db.Integer, default=50) # out of 100
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DelayRecords(db.Model):
    __tablename__ = 'delay_records'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('bus_schedules.id'), nullable=True)
    delay_minutes = db.Column(db.Integer, default=0)
    reason = db.Column(db.String(200), nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
