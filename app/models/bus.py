from app.extensions import db

class Bus(db.Model):
    __tablename__ = 'buses'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Operator
    bus_number = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), default='AC Sleeper')
    capacity = db.Column(db.Integer, default=40)
    eco_rating = db.Column(db.String(20), default='Medium')
    base_carbon_emission_per_km = db.Column(db.Float, default=0.04)

class Route(db.Model):
    __tablename__ = 'routes'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    origin = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    distance_km = db.Column(db.Float, nullable=False)
    base_fare = db.Column(db.Float, nullable=False)

class BusSchedule(db.Model):
    __tablename__ = 'bus_schedules'
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    projected_delay_mins = db.Column(db.Integer, default=0)

    # Relationships
    bus = db.relationship('Bus', backref='schedules')
    route = db.relationship('Route', backref='schedules')
    bookings = db.relationship('Booking', backref='schedule')

class SeatMap(db.Model):
    __tablename__ = 'seat_maps'
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(20), default='Aisle') # Window / Aisle
    zone = db.Column(db.String(20), default='Middle') # Front / Mid / Back
    noise_level_db = db.Column(db.Integer, default=45)
    vibration_level = db.Column(db.String(20), default='Low')
