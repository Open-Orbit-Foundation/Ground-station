#!/usr/bin/env python3
"""
Offline Weather Balloon Trajectory Prediction
Uses simplified wind model or cached wind data
"""

import math
import json
import os
from datetime import datetime


class BalloonPredictor:
    """Predicts balloon trajectory using offline wind data or models"""
    
    def __init__(self, wind_data_file='wind_cache.json'):
        self.wind_data_file = wind_data_file
        self.wind_data = self.load_wind_data()
        
        # Default ascent/descent rates (m/s)
        self.ascent_rate = 5.0
        self.descent_rate = 5.0
        
        # Burst altitude (meters)
        self.burst_altitude = 30000
    
    def load_wind_data(self):
        """Load cached wind data from file"""
        if os.path.exists(self.wind_data_file):
            try:
                with open(self.wind_data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading wind data: {e}")
        
        return None
    
    def get_wind_at_altitude(self, altitude, lat, lon, timestamp=None):
        """
        Get wind speed and direction at a given altitude
        
        Returns: (wind_speed_mps, wind_direction_degrees)
        """
        # If we have cached wind data, use it
        if self.wind_data:
            return self._interpolate_wind_from_cache(altitude, lat, lon, timestamp)
        
        # Otherwise use simplified model
        return self._simple_wind_model(altitude)
    
    def _interpolate_wind_from_cache(self, altitude, lat, lon, timestamp):
        """Interpolate wind from cached data"""
        # This would use actual cached wind data
        # For now, return a placeholder
        
        # Find closest altitude layer
        altitudes = sorted([float(a) for a in self.wind_data.get('altitudes', [])])
        
        if not altitudes:
            return self._simple_wind_model(altitude)
        
        # Find bounding altitudes
        lower_alt = max([a for a in altitudes if a <= altitude], default=altitudes[0])
        upper_alt = min([a for a in altitudes if a >= altitude], default=altitudes[-1])
        
        # Get wind at those altitudes
        lower_wind = self.wind_data['data'].get(str(int(lower_alt)), {'speed': 5, 'direction': 90})
        upper_wind = self.wind_data['data'].get(str(int(upper_alt)), {'speed': 10, 'direction': 90})
        
        # Linear interpolation
        if upper_alt == lower_alt:
            return lower_wind['speed'], lower_wind['direction']
        
        ratio = (altitude - lower_alt) / (upper_alt - lower_alt)
        speed = lower_wind['speed'] + ratio * (upper_wind['speed'] - lower_wind['speed'])
        direction = lower_wind['direction'] + ratio * (upper_wind['direction'] - lower_wind['direction'])
        
        return speed, direction
    
    def _simple_wind_model(self, altitude):
        """
        Simplified wind model for when no real data is available
        Based on typical atmospheric patterns
        """
        # Wind generally increases with altitude
        # This is a very simplified model!
        
        if altitude < 1000:
            # Surface winds
            speed = 5 + (altitude / 1000) * 5
            direction = 90  # East
        
        elif altitude < 10000:
            # Lower atmosphere - typical jet stream approach
            speed = 10 + (altitude / 10000) * 20
            direction = 90 + (altitude / 10000) * 45
        
        else:
            # Upper atmosphere - near jet stream
            speed = 30 + math.sin(altitude / 5000) * 20
            direction = 135  # Southeast typical
        
        return speed, direction % 360
    
    def predict_trajectory(self, start_lat, start_lon, start_alt, num_steps=100):
        """
        Predict balloon trajectory
        
        Returns: list of (lat, lon, altitude, time_offset) tuples
        """
        trajectory = []
        
        current_lat = start_lat
        current_lon = start_lon
        current_alt = start_alt
        time_offset = 0  # seconds
        
        # Time step (seconds)
        dt = 30
        
        # Ascent phase
        while current_alt < self.burst_altitude and len(trajectory) < num_steps:
            # Get wind at current altitude
            wind_speed, wind_direction = self.get_wind_at_altitude(current_alt, current_lat, current_lon)
            
            # Convert wind direction to radians (meteorological: direction FROM which wind blows)
            wind_rad = math.radians(wind_direction + 180)  # +180 to get direction TO
            
            # Calculate displacement
            wind_x = wind_speed * math.sin(wind_rad) * dt  # meters east
            wind_y = wind_speed * math.cos(wind_rad) * dt  # meters north
            
            # Convert to lat/lon change
            # 1 degree latitude ≈ 111,000 meters
            # 1 degree longitude ≈ 111,000 * cos(latitude) meters
            dlat = wind_y / 111000
            dlon = wind_x / (111000 * math.cos(math.radians(current_lat)))
            
            # Update position
            current_lat += dlat
            current_lon += dlon
            current_alt += self.ascent_rate * dt
            time_offset += dt
            
            trajectory.append((current_lat, current_lon, current_alt, time_offset))
        
        # Descent phase
        while current_alt > 0 and len(trajectory) < num_steps * 2:
            # Get wind at current altitude
            wind_speed, wind_direction = self.get_wind_at_altitude(current_alt, current_lat, current_lon)
            
            wind_rad = math.radians(wind_direction + 180)
            
            # Calculate displacement
            wind_x = wind_speed * math.sin(wind_rad) * dt
            wind_y = wind_speed * math.cos(wind_rad) * dt
            
            # Convert to lat/lon change
            dlat = wind_y / 111000
            dlon = wind_x / (111000 * math.cos(math.radians(current_lat)))
            
            # Update position
            current_lat += dlat
            current_lon += dlon
            current_alt -= self.descent_rate * dt
            time_offset += dt
            
            trajectory.append((current_lat, current_lon, max(0, current_alt), time_offset))
        
        return trajectory
    
    def get_landing_prediction(self, start_lat, start_lon, start_alt):
        """
        Get predicted landing location
        
        Returns: (landing_lat, landing_lon, flight_time_seconds)
        """
        trajectory = self.predict_trajectory(start_lat, start_lon, start_alt)
        
        if trajectory:
            landing = trajectory[-1]
            return landing[0], landing[1], landing[3]
        
        # Fallback to simple calculation if trajectory fails
        return self._simple_landing_prediction(start_lat, start_lon, start_alt)
    
    def _simple_landing_prediction(self, start_lat, start_lon, start_alt):
        """Ultra-simple landing prediction (fallback)"""
        # Time to burst
        time_to_burst = (self.burst_altitude - start_alt) / self.ascent_rate
        
        # Time to descend
        time_to_land = self.burst_altitude / self.descent_rate
        
        total_time = time_to_burst + time_to_land
        
        # Assume constant average wind (simplified!)
        avg_wind_speed = 15  # m/s
        avg_wind_direction = 90  # degrees (eastward)
        
        wind_rad = math.radians(avg_wind_direction + 180)
        
        total_displacement_x = avg_wind_speed * math.sin(wind_rad) * total_time
        total_displacement_y = avg_wind_speed * math.cos(wind_rad) * total_time
        
        landing_lat = start_lat + (total_displacement_y / 111000)
        landing_lon = start_lon + (total_displacement_x / (111000 * math.cos(math.radians(start_lat))))
        
        return landing_lat, landing_lon, total_time


def download_wind_data(lat, lon, output_file='wind_cache.json'):
    """
    Download wind data for offline use
    
    This is a placeholder - in practice you'd use:
    - NOAA GFS data
    - RUC soundings
    - ECMWF data
    - Wyoming upper air soundings
    """
    print("=" * 60)
    print("WIND DATA DOWNLOADER")
    print("=" * 60)
    print()
    print("To download real wind data, you would typically use:")
    print("1. NOAA GFS: ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/")
    print("2. Wyoming Soundings: http://weather.uwyo.edu/upperair/sounding.html")
    print("3. RUC/RAP data from NOAA")
    print()
    print("For this demo, creating sample wind data...")
    
    # Create sample wind data structure
    wind_data = {
        'location': {'lat': lat, 'lon': lon},
        'timestamp': datetime.now().isoformat(),
        'altitudes': [0, 1000, 3000, 5000, 10000, 15000, 20000, 25000, 30000],
        'data': {
            '0': {'speed': 5, 'direction': 90},
            '1000': {'speed': 8, 'direction': 95},
            '3000': {'speed': 12, 'direction': 100},
            '5000': {'speed': 18, 'direction': 110},
            '10000': {'speed': 30, 'direction': 120},
            '15000': {'speed': 40, 'direction': 130},
            '20000': {'speed': 45, 'direction': 135},
            '25000': {'speed': 40, 'direction': 140},
            '30000': {'speed': 35, 'direction': 145}
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(wind_data, f, indent=2)
    
    print(f"Sample wind data saved to {output_file}")
    print()
    print("In production, replace this with actual wind data downloads")
    print("scheduled before your flight.")


if __name__ == "__main__":
    print("Balloon Trajectory Prediction - Test")
    print()
    
    # Create sample wind data
    download_wind_data(34.052235, -118.243683)
    
    # Test prediction
    predictor = BalloonPredictor()
    
    start_lat = 34.052235
    start_lon = -118.243683
    start_alt = 1000  # meters
    
    print(f"Predicting from: {start_lat}, {start_lon}, {start_alt}m")
    
    landing_lat, landing_lon, flight_time = predictor.get_landing_prediction(
        start_lat, start_lon, start_alt
    )
    
    print(f"Predicted landing: {landing_lat:.6f}, {landing_lon:.6f}")
    print(f"Flight time: {flight_time/60:.1f} minutes")
    
    # Show full trajectory
    print("\nFull trajectory:")
    trajectory = predictor.predict_trajectory(start_lat, start_lon, start_alt, num_steps=50)
    
    print(f"{'Time (min)':<12} {'Lat':<12} {'Lon':<12} {'Alt (m)':<10}")
    print("-" * 50)
    for lat, lon, alt, t in trajectory[::5]:  # Every 5th point
        print(f"{t/60:<12.1f} {lat:<12.6f} {lon:<12.6f} {alt:<10.0f}")

