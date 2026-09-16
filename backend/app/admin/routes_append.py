@admin_ui_bp.route('/safety-metrics', methods=['GET'])
@admin_required
@role_required('Super Admin', 'Operator', 'Analyst')
def safety_metrics():
    from app.models.bus import Bus
    from app.models.metrics import SafetyMetrics, EcoMetrics
    
    buses = Bus.query.filter_by(is_active=True).all()
    # Eager load could be better but list comprehension is fine for this demo
    metrics_data = []
    
    total_driver = 0
    total_maint = 0
    total_co2 = 0.0
    count = 0

    for bus in buses:
        sm = SafetyMetrics.query.filter_by(bus_id=bus.id).first()
        em = EcoMetrics.query.filter_by(bus_id=bus.id).first()
        metrics_data.append({
            'bus': bus,
            'safety': sm or SafetyMetrics(driver_score=0, maintenance_score=0, overall_score=0, bus_id=bus.id),
            'eco': em or EcoMetrics(co2_emissions_per_km=0.0, eco_rating='Unknown', bus_id=bus.id)
        })
        if sm and em:
            total_driver += sm.driver_score
            total_maint += sm.maintenance_score
            total_co2 += em.co2_emissions_per_km
            count += 1
            
    avg_driver = round(total_driver / count, 1) if count > 0 else 0
    avg_maint = round(total_maint / count, 1) if count > 0 else 0
    avg_co2 = round(total_co2 / count, 3) if count > 0 else 0.0

    return render_template('admin/safety_metrics.html', 
                            metrics_data=metrics_data,
                            avg_driver=avg_driver,
                            avg_maint=avg_maint,
                            avg_co2=avg_co2,
                            total_tracked=len(buses))

@admin_ui_bp.route('/system-access', methods=['GET'])
@admin_required
@role_required('Super Admin')
def system_access():
    from app.models.user import User
    from app.models.admin_models import Role, AdminLogs
    
    roles = Role.query.all()
    # Users who have a role assigned
    admins = User.query.filter(User.role_id != None).all()
    recent_logs = AdminLogs.query.order_by(AdminLogs.timestamp.desc()).limit(50).all()
    
    return render_template('admin/system_access.html', 
                            admins=admins,
                            roles=roles,
                            logs=recent_logs)
