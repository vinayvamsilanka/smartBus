from app.extensions import db
from datetime import datetime

class RewardProduct(db.Model):
    __tablename__ = 'reward_products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False) # e.g., Voucher, Merchandise, Carbon Offset
    stock = db.Column(db.Integer, default=100)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Redemption(db.Model):
    __tablename__ = 'redemptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('reward_products.id'), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    coupon_code = db.Column(db.String(50), unique=True, nullable=True)
    redemption_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Active') # Active, Used, Cancelled

    # Relationships
    user = db.relationship('User', backref=db.backref('redemptions', lazy=True))
    product = db.relationship('RewardProduct', backref=db.backref('redemptions', lazy=True))
