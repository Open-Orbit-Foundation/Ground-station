#!/usr/bin/env python3
"""
CUSF Landing Predictor API Integration
Downloads and caches balloon trajectory predictions
"""

import requests
import json
import os
import math
from datetime import datetime, timedelta


class CUSFPredictor:
    """Interface to CUSF Landing Predictor API"""
    
    def __init__(self, cache_file='flight_prediction.json'):
        self.api_url = 'https://predict.cusf.co.uk/api/v1/'
        self.cache_file = cache_file
        self.cached_prediction = None
        self.cache_loaded_at = None
        
        # Load cached prediction if exists
        if os.path.exists(cache_file):
            self.load_cache()

    def _cache_is_fresh(self, ttl_hours: float = 3.0) -> bool:
        """Return True if a cached prediction exists and is within TTL."""
        if not self.cached_prediction:
            return False
        ts = self.cached_prediction.get('download_time')
        if not ts:
            return False
        t = datetime.fromisoformat(ts.replace('Z', '+00:00')) if 'T' in ts else datetime.fromisoformat(ts)
        age = datetime.now(t.tzinfo) - t if t.tzinfo else datetime.now() - t
        return age <= timedelta(hours=max(ttl_hours, 0))
    
    def download_prediction(self, config, use_cache_on_fail: bool = True, ttl_hours: float = 3.0):
        """
        Download trajectory prediction from CUSF API
        
        Args:
            config: Dictionary with prediction parameters:
                - launch_latitude
                - launch_longitude
                - launch_altitude (meters)
                - launch_datetime (ISO format or datetime object)
                - ascent_rate (m/s)
                - burst_altitude (meters)
                - descent_rate (m/s)
        
        Returns:
            Prediction data dictionary or None if failed
        """
        # Convert datetime to ISO string if needed
        launch_time = config.get('launch_datetime')
        if isinstance(launch_time, datetime):
            launch_time = launch_time.isoformat() + 'Z'
        
        params = {
            'launch_latitude': config['launch_latitude'],
            'launch_longitude': config['launch_longitude'],
            'launch_altitude': config.get('launch_altitude', 0),
            'launch_datetime': launch_time,
            'ascent_rate': config['ascent_rate'],
            'burst_altitude': config['burst_altitude'],
            'descent_rate': config['descent_rate']
        }
        
        print(f"Downloading prediction from CUSF API...")
        print(f"Launch: {params['launch_latitude']:.4f}, {params['launch_longitude']:.4f}")
        print(f"Time: {params['launch_datetime']}")
        
        response = requests.get(self.api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Add metadata
        data['config'] = config
        data['download_time'] = datetime.now().isoformat()
        # Cache the prediction
        self.cached_prediction = data
        self.save_cache()
        print(f"✓ Prediction downloaded successfully")
        print(f"✓ Landing: {data['landing_location']['latitude']:.4f}, {data['landing_location']['longitude']:.4f}")
        return data
    
    def save_cache(self):
        """Save prediction to cache file"""
        if self.cached_prediction:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cached_prediction, f, indent=2)
            print(f"✓ Prediction cached to {self.cache_file}")
    
    def load_cache(self):
        """Load prediction from cache file"""
        with open(self.cache_file, 'r') as f:
            self.cached_prediction = json.load(f)
        self.cache_loaded_at = datetime.now().isoformat()
        print(f"✓ Loaded cached prediction from {self.cache_file}")
        return True
    
    def get_trajectory(self):
        """
        Get trajectory points from cached prediction
        
        Returns:
            List of (lat, lon, altitude, time_offset) tuples
        """
        if not self.cached_prediction:
            return []
        
        trajectory = []
        
        # Parse prediction path
        for stage in ['ascent', 'descent']:
            if stage in self.cached_prediction['prediction']:
                for point in self.cached_prediction['prediction'][stage]:
                    trajectory.append((
                        point['latitude'],
                        point['longitude'],
                        point['altitude'],
                        point.get('time', 0)
                    ))
        return trajectory
    
    def get_landing_location(self):
        """Get predicted landing location"""
        if not self.cached_prediction:
            return None
        
        landing = self.cached_prediction['landing_location']
        return (
            landing['latitude'],
            landing['longitude'],
            0  # Landing altitude
        )
    
    def get_position_at_time(self, elapsed_seconds):
        """
        Get predicted position at a given time after launch
        
        Args:
            elapsed_seconds: Seconds since launch
        
        Returns:
            (lat, lon, altitude) or None
        """
        trajectory = self.get_trajectory()
        
        if not trajectory:
            return None
        
        # Find closest trajectory point
        closest = min(trajectory, key=lambda p: abs(p[3] - elapsed_seconds))
        
        return (closest[0], closest[1], closest[2])
    
    def calculate_prediction_error(self, actual_lat, actual_lon, actual_alt, elapsed_seconds):
        """
        Calculate error between predicted and actual position
        
        Args:
            actual_lat, actual_lon, actual_alt: Current actual position
            elapsed_seconds: Time since launch
        
        Returns:
            Dictionary with error metrics or None
        """
        predicted = self.get_position_at_time(elapsed_seconds)
        
        if not predicted:
            return None
        
        pred_lat, pred_lon, pred_alt = predicted
        
        # Calculate horizontal distance error (Haversine formula)
        lat1, lon1 = math.radians(actual_lat), math.radians(actual_lon)
        lat2, lon2 = math.radians(pred_lat), math.radians(pred_lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        horizontal_error_km = 6371 * c  # Earth radius = 6371 km
        
        # Altitude error
        altitude_error_m = actual_alt - pred_alt
        
        # Direction of error
        bearing = math.degrees(math.atan2(
            math.sin(dlon) * math.cos(lat2),
            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        ))
        
        return {
            'horizontal_error_km': horizontal_error_km,
            'horizontal_error_m': horizontal_error_km * 1000,
            'altitude_error_m': altitude_error_m,
            'bearing_degrees': bearing % 360,
            'predicted_lat': pred_lat,
            'predicted_lon': pred_lon,
            'predicted_alt': pred_alt
        }


if __name__ == "__main__":
    # Test CUSF predictor
    print("CUSF Landing Predictor - Test")
    print("=" * 60)
    
    predictor = CUSFPredictor()
    
    # Example configuration
    config = {
        'launch_latitude': 34.052235,
        'launch_longitude': -118.243683,
        'launch_altitude': 0,
        'launch_datetime': datetime.now() + timedelta(hours=1),
        'ascent_rate': 5.0,
        'burst_altitude': 30000,
        'descent_rate': 5.0
    }
    
    print("\nDownloading prediction...")
    result = predictor.download_prediction(config)
    
    if result:
        print("\n✓ Success!")
        landing = predictor.get_landing_location()
        if landing:
            print(f"\nPredicted landing: {landing[0]:.6f}, {landing[1]:.6f}")
        
        print(f"\nTrajectory points: {len(predictor.get_trajectory())}")
    else:
        print("\n✗ Failed to download prediction")
        print("Note: Requires internet connection")

