from app import create_app
from app.extensions import db
from app.models.graph import City

app = create_app()

NEW_CITIES = [
    'Bangalore', 'Chennai', 'Mumbai', 'Pune', 'Mysore', 'Vellore', 
    'Chittoor', 'Eluru', 'Hyderabad', 'Vijayawada', 'Guntur', 
    'Tirupati', 'Visakhapatnam', 'Vizianagaram', 'Nellore', 
    'Kurnool', 'Rajahmundry', 'Ongole', 'Warangal', 'Anantapur', 
    'Kadapa', 'Kakinada'
]

with app.app_context():
    for city_name in NEW_CITIES:
        city = City.query.filter_by(name=city_name.lower()).first()
        if not city:
            city = City(name=city_name.lower(), is_active=True)
            db.session.add(city)
            print(f"Added city: {city_name}")
        else:
            city.is_active = True
            print(f"City already exists: {city_name}")
    
    db.session.commit()
    print("Database seeding completed.")
