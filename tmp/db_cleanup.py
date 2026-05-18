from app import create_app
from app.extensions import db
from app.models.graph import City, GraphRoute
from app.models.bus import Route
import sys

app = create_app()

def cleanup_cities():
    with app.app_context():
        # 1. List all cities to find duplicates
        cities = City.query.all()
        print(f"Checking {len(cities)} cities...")
        
        # Mapping bad names to good names
        corrections = {
            'banglore': 'bangalore',
            'bglr': 'bangalore',
            'benagluru': 'bangalore',
            'mumbai ': 'mumbai',
            'chennai ': 'chennai',
            'hyd': 'hyderabad'
        }
        
        # Let's also do a case-insensitive unique check
        city_names_map = {} # normalized_name: [list of city objects]
        for city in cities:
            norm = city.name.lower().strip()
            # Check corrections
            if norm in corrections:
                norm = corrections[norm]
            
            if norm not in city_names_map:
                city_names_map[norm] = []
            city_names_map[norm].append(city)
            
        for norm_name, city_objs in city_names_map.items():
            if len(city_objs) > 1:
                print(f"Found duplicates for '{norm_name}': {[c.name for c in city_objs]}")
                # Target city is the one with the correct spelling (norm_name) or the first one
                target_city = None
                for c in city_objs:
                    if c.name.lower().strip() == norm_name:
                        target_city = c
                        break
                if not target_city: target_city = city_objs[0]
                
                # Others are duplicates to be merged
                duplicates = [c for c in city_objs if c.id != target_city.id]
                
                for dup in duplicates:
                    print(f"  Merging '{dup.name}' (ID {dup.id}) into '{target_city.name}' (ID {target_city.id})")
                    
                    # A. Update GraphRoutes
                    GraphRoute.query.filter_by(source_city_id=dup.id).update({GraphRoute.source_city_id: target_city.id})
                    GraphRoute.query.filter_by(destination_city_id=dup.id).update({GraphRoute.destination_city_id: target_city.id})
                    
                    # B. Update Route (standard model) - uses strings
                    Route.query.filter_by(origin=dup.name).update({Route.origin: target_city.name})
                    Route.query.filter_by(destination=dup.name).update({Route.destination: target_city.name})
                    Route.query.filter_by(origin=dup.name.lower()).update({Route.origin: target_city.name})
                    Route.query.filter_by(destination=dup.name.lower()).update({Route.destination: target_city.name})
                    
                    # C. Delete dup city
                    db.session.delete(dup)
                
                # Finally, ensure target_city name is normalized
                target_city.name = norm_name
                db.session.add(target_city)
                db.session.commit()
                print(f"  Merged successfully.")
            else:
                # Just normalize the name if it's the only one
                city_obj = city_objs[0]
                if city_obj.name != norm_name:
                    print(f"Normalizing '{city_obj.name}' to '{norm_name}'")
                    city_obj.name = norm_name
                    db.session.add(city_obj)
                    db.session.commit()

if __name__ == "__main__":
    cleanup_cities()
    print("Database cleanup complete.")
