#!/usr/bin/env python3
"""
Test Data Generator
Simulates telemetry data for testing the UI without actual hardware
"""

import csv
import time
import math
import random
from datetime import datetime

CSV_FILE = 'telemetry_data.csv'
CSV_HEADERS = ['timestamp', 'roll', 'pitch', 'yaw', 'latitude', 'longitude', 
               'altitude', 'velocity', 'temperature', 'pressure']

def generate_telemetry(t):
    """Generate realistic simulated telemetry data"""
    # Simulate a balloon ascending
    altitude = 1000 + t * 2.5  # Rising at ~2.5 m/s
    
    # Oscillating orientation
    roll = math.sin(t * 0.1) * 15
    pitch = math.cos(t * 0.15) * 10
    yaw = (t * 0.5) % 360
    
    # Drifting GPS position (starting from LA coordinates)
    base_lat = 34.052235
    base_lon = -118.243683
    lat = base_lat + (t * 0.0001)
    lon = base_lon + (t * 0.00008)
    
    # Environmental data
    velocity = 2.5 + random.uniform(-0.5, 0.5)
    temperature = 25 - (altitude / 150)  # Temperature decreases with altitude
    pressure = 1013.25 * math.exp(-altitude / 8500)  # Barometric formula
    
    return {
        'roll': round(roll, 2),
        'pitch': round(pitch, 2),
        'yaw': round(yaw, 2),
        'latitude': round(lat, 6),
        'longitude': round(lon, 6),
        'altitude': round(altitude, 1),
        'velocity': round(velocity, 2),
        'temperature': round(temperature, 1),
        'pressure': round(pressure, 2)
    }

def main():
    print("Test Data Generator")
    print("=" * 50)
    print(f"Generating simulated telemetry to {CSV_FILE}")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    # Initialize CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
    
    t = 0
    
    try:
        while True:
            # Generate data
            data = generate_telemetry(t)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Write to CSV
            with open(CSV_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    data['roll'],
                    data['pitch'],
                    data['yaw'],
                    data['latitude'],
                    data['longitude'],
                    data['altitude'],
                    data['velocity'],
                    data['temperature'],
                    data['pressure']
                ])
            
            # Display
            print(f"[{timestamp}] Alt: {data['altitude']:.1f}m | "
                  f"GPS: {data['latitude']:.4f}, {data['longitude']:.4f}")
            
            t += 1
            time.sleep(1)  # Update every second
    
    except KeyboardInterrupt:
        print("\n\nStopped data generation")

if __name__ == "__main__":
    main()

