from flask import Blueprint, jsonify
from app.models import AnalyticsLogs
from app.extensions import db
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

# NOTE: In production you would apply @role_required('Admin') decorators to these
# from app.utils.decorators import role_required

@admin_bp.route('/analytics/demand')
# @role_required('Admin')
def demand_heatmap():
    # Fetch origin-dest combos to form a heatmap of user search activity
    demands = db.session.query(
        AnalyticsLogs.search_origin, 
        AnalyticsLogs.search_dest, 
        func.count(AnalyticsLogs.id)
    ).group_by(AnalyticsLogs.search_origin, AnalyticsLogs.search_dest).all()
    
    results = [{"origin": r[0], "destination": r[1], "searches": r[2]} for r in demands]
    return jsonify(results), 200

@admin_bp.route('/analytics/revenue')
def revenue_analysis():
    # Simulated revenue stats for Graph
    return jsonify({
        "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
        "revenue_data": [12000, 19000, 15000, 22000, 30000]
    }), 200

@admin_bp.route('/analytics/operational')
def sys_ops():
    # Simulated average safety
    return jsonify({
        "average_bus_safety": 94,
        "critical_delay_incidents": 2
    }), 200
