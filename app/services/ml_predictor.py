import numpy as np
import random
import math
from sklearn.linear_model import LinearRegression

# Geography-aware fare prediction (Coordinates shared with split_optimizer)
CITY_COORDINATES = {
    'hyderabad': (17.3850, 78.4867),
    'vijayawada': (16.5062, 80.6480),
    'guntur': (16.3067, 80.4365),
    'tirupati': (13.6285, 79.4192),
    'visakhapatnam': (17.6868, 83.2185),
    'vizianagaram': (18.1067, 83.3950),
    'nellore': (14.4426, 79.9865),
    'kurnool': (15.8281, 78.0373),
    'rajahmundry': (17.0005, 81.7835),
    'ongole': (15.5057, 80.0499),
    'warangal': (17.9689, 79.5941),
    'anantapur': (14.6819, 77.6006),
    'kadapa': (14.4673, 78.8242),
    'kakinada': (16.9891, 82.2475),
    'bangalore': (12.9716, 77.5946),
    'chennai': (13.0827, 80.2707),
    'mumbai': (19.0760, 72.8777),
    'pune': (18.5204, 73.8567),
    'mysore': (12.2958, 76.6394),
    'vellore': (12.9165, 79.1325),
    'chittoor': (13.2048, 79.1003),
    'eluru': (16.7107, 81.1030)
}

class FarePredictor:
    def __init__(self):
        # Time-series regression mock trained on 30 days of synthetic flight pricing
        X_train = np.array([[i] for i in range(1, 31)]) # days to travel
        y_train = np.array([500 + (30 - i)*15 + random.randint(-50, 50) for i in range(1, 31)])
        self.model = LinearRegression()
        self.model.fit(X_train, y_train)

    def _get_distance(self, origin, dest):
        c1 = CITY_COORDINATES.get(origin.lower())
        c2 = CITY_COORDINATES.get(dest.lower())
        
        if c1 and c2:
            lat1, lon1 = map(math.radians, c1)
            lat2, lon2 = map(math.radians, c2)
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return max(50, c * 6371) # KM
        
        # Fallback to hash-based for unknown cities
        return (hash(origin + dest) % 600) + 150

    def predict_fare(self, days_out, origin, dest):
        # Base price calculation based on ACTUAL geographic distance
        distance = self._get_distance(origin, dest)
        
        # Base rate per km (fluctuates based on days remaining)
        # Closer to travel date = higher price (1.5 to 3.0 INR per km)
        rate_per_km = 1.3 + (max(0, 30 - days_out) * 0.06)
        
        # Real-world 'noise' factors
        weekend_surge = 1.15 if random.random() > 0.7 else 1.0
        fuel_surcharge = random.uniform(20, 80)
        
        predicted = (distance * rate_per_km * weekend_surge) + fuel_surcharge
        
        # Machine learning regression refinement (coefficient derived from trained model)
        ml_refinement = self.model.predict([[days_out]])[0] / 500
        
        final_fare = round(predicted * ml_refinement, 2)
        # Minimum fare threshold based on distance
        return max(distance * 1.5, final_fare)
        
ml_service = FarePredictor()

