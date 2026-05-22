import random
import math

class GPSSimulator:
    def __init__(self, start_lat=37.7749, start_lon=-122.4194):
        # Default start: San Francisco
        self.current_lat = start_lat
        self.current_lon = start_lon

    def get_coordinates(self):
        # Simulate moving along a road by adding small random noise
        # This creates a "random walk" style movement
        lat_change = random.uniform(-0.0005, 0.0005)
        lon_change = random.uniform(-0.0005, 0.0005)
        
        self.current_lat += lat_change
        self.current_lon += lon_change
        
        return self.current_lat, self.current_lon
