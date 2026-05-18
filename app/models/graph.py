from app.extensions import db
from datetime import datetime

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)

class GraphRoute(db.Model):
    __tablename__ = 'graph_routes'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    source_city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False, index=True)
    destination_city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False, index=True)
    distance = db.Column(db.Float, nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    estimated_time = db.Column(db.Float, nullable=False) # in hours
    route_date = db.Column(db.Date, nullable=False, index=True)

    # Relationships
    source = db.relationship('City', foreign_keys=[source_city_id])
    destination = db.relationship('City', foreign_keys=[destination_city_id])

class FareHistory(db.Model):
    __tablename__ = 'fare_history'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('graph_routes.id'), nullable=False)
    recorded_date = db.Column(db.DateTime, default=datetime.utcnow)
    historical_price = db.Column(db.Float, nullable=False)
