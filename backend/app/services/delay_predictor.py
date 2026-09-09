import numpy as np
from sklearn.linear_model import LinearRegression
import random

class DelayPredictor:
    def __init__(self):
        # Time-series regression mock trained on synthetic traffic congestion levels
        # Features: [Hour of Day, Route Distance, Driver Safety Score]
        # target: Delay minutes
        X_train = np.array([
            [8, 100, 95],   # morning rush hour
            [12, 100, 95],  # afternoon off-peak
            [18, 150, 90],  # evening rush hour
            [22, 200, 98],  # night long distance
            [10, 50, 85],   # mid morning, cautious driver
            [15, 300, 92],  # mid afternoon
            [9, 400, 88],   # long distance morning rush hour
            [3, 100, 96]    # late night empty road
        ])
        y_train = np.array([15, 5, 25, 8, 10, 12, 35, 2])
        
        self.model = LinearRegression()
        self.model.fit(X_train, y_train)

    def predict_delay(self, hour: int, distance_km: float, driver_score: float) -> dict:
        # Base ML prediction
        predicted = self.model.predict([[hour, distance_km, driver_score]])[0]
        predicted = max(0, predicted) # Ensure no negative delays
        
        # Determine congestion level based on hour
        if hour in [8, 9, 10, 17, 18, 19]:
            congestion = "High Congestion"
            multiplier = 1.3
        elif hour in [11, 12, 13, 14, 15, 16, 20, 21]:
            congestion = "Moderate Traffic"
            multiplier = 1.0
        else:
            congestion = "Light / Free Flowing"
            multiplier = 0.6
            
        final_delay = int(round(predicted * multiplier))
        
        # Categorize delay factor explanation
        reasons = []
        if congestion == "High Congestion":
            reasons.append("Peak commute traffic at key toll points")
        if driver_score < 90:
            reasons.append("Precautionary driving speeds by safety policy")
        if distance_km > 300:
            reasons.append("Long-distance transit buffer adjustment")
            
        if not reasons:
            reasons.append("Standard buffer for optimal route safety")
            
        return {
            "delay_minutes": final_delay,
            "congestion": congestion,
            "reasons": reasons,
            "ai_confidence_score": min(98, max(75, 100 - abs(final_delay - 10)))
        }

delay_service = DelayPredictor()
