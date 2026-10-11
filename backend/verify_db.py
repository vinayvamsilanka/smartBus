from app import create_app
from app.models.bus import Bus, Route
from app.models import User
app = create_app()
app.app_context().push()
print('=== AIVEN CLOUD DATABASE VERIFICATION ===')
print(f'Total Users Found: {User.query.count()}')
print(f'Total Buses Found: {Bus.query.count()}')
first_bus = Bus.query.first()
print(f'Sample Fleet Bus: {first_bus.bus_number} ({first_bus.type})')
print(f'Total Routes Found: {Route.query.count()}')
r = Route.query.first()
print(f'Sample Route: {r.origin.title()} to {r.destination.title()} ({r.distance_km} km)')
