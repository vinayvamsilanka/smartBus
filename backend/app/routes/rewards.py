from flask import Blueprint, request, jsonify, session
from app.extensions import db
from app.models import User
from app.models.reward import RewardProduct, Redemption
import uuid
import random

rewards_bp = Blueprint('rewards', __name__)

def auto_seed_rewards():
    """Seed default rewards catalog if empty."""
    default_products = [
        {
            "name": "Eco-Friendly Travel Kit",
            "description": "Bamboo travel toothbrush, sustainable utensils, and reusable steel straw in a canvas bag.",
            "points_cost": 120,
            "category": "Merchandise",
            "stock": 15,
            "image_url": "fa-kit-medical"
        },
        {
            "name": "50% SmartBus Ride Discount Voucher",
            "description": "Get a 50% discount on any booking up to ₹500. Valid for 6 months.",
            "points_cost": 200,
            "category": "Voucher",
            "stock": 50,
            "image_url": "fa-ticket"
        },
        {
            "name": "100kg Carbon Offset Certificate",
            "description": "Invest in certified solar and reforestation programs. Offsets 100kg of CO₂ emissions.",
            "points_cost": 80,
            "category": "Carbon Offset",
            "stock": 999,
            "image_url": "fa-leaf"
        },
        {
            "name": "SmartBus Premium Glass Thermos",
            "description": "Vacuum-insulated double-wall glass bottle with sustainable wood lid. 500ml.",
            "points_cost": 150,
            "category": "Merchandise",
            "stock": 10,
            "image_url": "fa-bottle-water"
        },
        {
            "name": "Priority Boarding & Lounge Access Upgrade",
            "description": "Skip queues at boarding and get free premium lounge access at the SmartBus terminal.",
            "points_cost": 50,
            "category": "Voucher",
            "stock": 100,
            "image_url": "fa-crown"
        }
    ]
    
    for dp in default_products:
        product = RewardProduct(
            name=dp["name"],
            description=dp["description"],
            points_cost=dp["points_cost"],
            category=dp["category"],
            stock=dp["stock"],
            image_url=dp["image_url"]
        )
        db.session.add(product)
    
    db.session.commit()

@rewards_bp.route('/products', methods=['GET'])
def get_products():
    # If no products exist, seed the catalog dynamically
    if RewardProduct.query.count() == 0:
        auto_seed_rewards()
        
    products = RewardProduct.query.filter(RewardProduct.stock > 0).all()
    product_list = [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "points_cost": p.points_cost,
        "category": p.category,
        "stock": p.stock,
        "image_url": p.image_url
    } for p in products]
    
    return jsonify({"success": True, "products": product_list}), 200

@rewards_bp.route('/redeem', methods=['POST'])
def redeem_reward():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "msg": "User authentication required"}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "msg": "User authentication required"}), 401
        
    data = request.get_json() or {}
    product_id = data.get('product_id')
    if not product_id:
        return jsonify({"success": False, "msg": "Product selection required"}), 400
        
    product = RewardProduct.query.get(product_id)
    if not product:
        return jsonify({"success": False, "msg": "Product not found"}), 404
        
    if product.stock <= 0:
        return jsonify({"success": False, "msg": "Product is out of stock"}), 400
        
    user_pts = user.eco_points or 0
    if user_pts < product.points_cost:
        return jsonify({
            "success": False, 
            "msg": f"Insufficient Green Miles. You need {product.points_cost} points, but only have {user_pts}."
        }), 400
        
    # Deduct points and stock
    user.eco_points = user_pts - product.points_cost
    product.stock -= 1
    
    # Generate unique coupon code for redemptions
    code_prefix = product.name[:3].upper().replace(" ", "").replace("-", "")
    coupon_code = f"ECO-{code_prefix}-{uuid.uuid4().hex[:6].upper()}"
    
    new_redemption = Redemption(
        user_id=user.id,
        product_id=product.id,
        points_spent=product.points_cost,
        coupon_code=coupon_code,
        status='Active'
    )
    
    try:
        db.session.add(new_redemption)
        db.session.commit()
        return jsonify({
            "success": True,
            "msg": f"Successfully redeemed '{product.name}'!",
            "coupon_code": coupon_code,
            "points_spent": product.points_cost,
            "remaining_points": user.eco_points
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": "Failed to complete redemption", "error": str(e)}), 500

@rewards_bp.route('/user-redemptions', methods=['GET'])
def get_user_redemptions():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "msg": "User authentication required"}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "msg": "User authentication required"}), 401
        
    redemptions = Redemption.query.filter_by(user_id=user.id).order_by(Redemption.redemption_date.desc()).all()
    redemption_list = [{
        "id": r.id,
        "product_name": r.product.name,
        "product_category": r.product.category,
        "points_spent": r.points_spent,
        "coupon_code": r.coupon_code,
        "redemption_date": r.redemption_date.strftime("%Y-%m-%d %H:%M"),
        "status": r.status
    } for r in redemptions]
    
    return jsonify({"success": True, "redemptions": redemption_list}), 200

@rewards_bp.route('/validate-coupon', methods=['POST'])
def validate_coupon():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "msg": "User authentication required"}), 401
        
    data = request.get_json() or {}
    code = data.get('coupon_code', '').strip()
    
    if not code:
        return jsonify({"success": False, "msg": "No coupon code provided"}), 400
        
    redemption = Redemption.query.filter_by(coupon_code=code, user_id=user_id).first()
    
    if not redemption:
        return jsonify({"success": False, "msg": "Invalid coupon code"}), 404
        
    if redemption.status != 'Active':
        return jsonify({"success": False, "msg": f"Coupon is already {redemption.status}"}), 400
        
    # Hardcoded discount logic for demo. "50%" gives 50% off. Others give a flat 10% off for eco products.
    discount_pct = 0.10
    if "50%" in redemption.product.name:
        discount_pct = 0.50
        
    return jsonify({
        "success": True, 
        "discount_pct": discount_pct,
        "product_name": redemption.product.name
    }), 200
