from app import create_app
from app.extensions import db
from app.models.graph import City, GraphRoute
from app.models.bus import Route
import sys

app = create_app()

with app.app_context():
    print("Checking database integrity...")
    
    # 1. Cities
    cities = City.query.all()
    print(f"Cities: {len(cities)}")
    for c in cities:
        print(f"  {c.id}: {c.name}")
        
    # 2. GraphRoutes (check if cities exist)
    bad_routes = 0
    routes = GraphRoute.query.all()
    for r in routes:
        src = City.query.get(r.source_city_id)
        dst = City.query.get(r.destination_city_id)
        if not src or not dst:
            print(f"  Bad GraphRoute {r.id}: {r.source_city_id} -> {r.destination_city_id}")
            bad_routes += 1
            # Optionally delete these orphaned routes
            db.session.delete(r)
            
    if bad_routes > 0:
        db.session.commit()
        print(f"Deleted {bad_routes} orphaned graph routes.")
    else:
        print("All GraphRoutes have valid cities.")
        
    # 3. Routes (check strings)
    standard_routes = Route.query.all()
    print(f"Standard Routes: {len(standard_routes)}")
    
    # Check "Eluru" and "Hyderabad"
    eluru = City.query.filter_by(name='eluru').first()
    hyd = City.query.filter_by(name='hyderabad').first()
    print(f"Eluru: {eluru.id if eluru else 'MISSSING'}")
    print(f"Hyderabad: {hyd.id if hyd else 'MISSING'}")
