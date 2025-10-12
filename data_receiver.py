#!/usr/bin/env python3
"""
Data Receiver - Ground Station Backend
Receives sensor data from E22900t22s LoRa module and logs to CSV
"""

import serial
import sys
import time
import csv
import os
from datetime import datetime
import argparse

# Configuration (defaults)
SERIAL_PORT = 'COM5'
BAUD_RATE = 9600
TIMEOUT = 1
CSV_FILE = 'telemetry_data.csv'  # legacy default; main() now sets session-specific path
TELEMETRY_DIR = 'Telemetry'


# CSV Headers
CSV_HEADERS = ['timestamp', 'roll', 'pitch', 'yaw', 'latitude', 'longitude', 
               'altitude', 'velocity', 'temperature', 'pressure']


def initialize_csv(csv_path):
    """Initialize CSV file with headers if it doesn't exist"""
    os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"Created new CSV file: {csv_path}")


def validate_data(data_dict):
    """
    Validate sensor data before writing to CSV
    Returns True if data is valid, False otherwise
    """
    try:
        # Check all required fields are present
        required_fields = ['roll', 'pitch', 'yaw', 'latitude', 'longitude', 
                          'altitude', 'velocity', 'temperature', 'pressure']
        
        for field in required_fields:
            if field not in data_dict:
                return False
        
        # Validate numeric ranges
        if not (-180 <= float(data_dict['roll']) <= 180):
            return False
        if not (-90 <= float(data_dict['pitch']) <= 90):
            return False
        if not (-180 <= float(data_dict['yaw']) <= 180):
            return False
        if not (-90 <= float(data_dict['latitude']) <= 90):
            return False
        if not (-180 <= float(data_dict['longitude']) <= 180):
            return False
        if not (-1000 <= float(data_dict['altitude']) <= 50000):
            return False
        
        return True
    
    except (ValueError, TypeError):
        return False


def parse_sensor_data(raw_text):
    """
    Parse HAART GPS payload: "GPGGA,...;GPRMC,..." only.
    Returns a complete dict with missing values defaulted to 0.
    """
    try:
        text = raw_text.strip()
        haart = parse_haart_payload(text)
        return haart
    except Exception as e:
        print(f"Parse error: {e}")
        return None


def nmea_degmin_to_decimal(value_str, deg_len):
    """
    Convert NMEA degrees+minutes (ddmm.mmmm or dddmm.mmmm) to decimal degrees.
    Expects value_str without hemisphere. Returns float or None.
    deg_len: 2 for latitude, 3 for longitude.
    """
    try:
        if value_str is None:
            return None
        s = value_str.strip()
        if s == '':
            return None
        # Remove any non-numeric except dot
        s = ''.join(ch for ch in s if ch.isdigit() or ch == '.')
        if s == '' or '.' not in s or len(s) <= deg_len:
            return None
        degrees = int(s[:deg_len])
        minutes = float(s[deg_len:])
        return degrees + minutes / 60.0
    except Exception:
        return None


def knots_to_mps(knots):
    try:
        return float(knots) * 0.514444
    except Exception:
        return 0.0


def fill_defaults(data_dict):
    """
    Ensure all required fields exist; default missing ones to 0.
    Returns a dict of strings to keep CSV consistent.
    """
    fields = ['roll', 'pitch', 'yaw', 'latitude', 'longitude', 'altitude', 'velocity', 'temperature', 'pressure']
    out = {}
    for f in fields:
        val = data_dict.get(f, 0)
        if val is None or val == '':
            val = 0
        out[f] = str(val)
    return out


def parse_haart_payload(text):
    """
    Parse HAART sender payload embedded in arbitrary bytes/text.
    Looks for "GPGGA,...;GPRMC,..." and extracts lat/lon/alt/speed.
    Returns a full data dict with defaults, or None if pattern absent.
    """
    try:
        if 'GPGGA,' not in text or 'GPRMC,' not in text:
            return None

        # Narrow to the GPGGA..GPRMC region
        gga_idx = text.find('GPGGA,')
        sub = text[gga_idx:]
        # Split gga and rmc on the first ';'
        if ';' in sub:
            gga_part, rest = sub.split(';', 1)
        else:
            # If no separator, try to find GPRMC start directly
            rmc_start = sub.find('GPRMC,')
            if rmc_start == -1:
                return None
            gga_part = sub[:rmc_start]
            rest = sub[rmc_start:]

        # Ensure RMC part begins correctly
        rmc_idx = rest.find('GPRMC,')
        if rmc_idx == -1:
            return None
        rmc_part = rest[rmc_idx:]

        # Clean trailing control chars
        gga_part = ''.join(ch for ch in gga_part if ch >= ' ')
        rmc_part = ''.join(ch for ch in rmc_part if ch >= ' ')

        # Remove headers
        if gga_part.startswith('GPGGA,'):
            gga_fields = gga_part[len('GPGGA,'):].split(',')
        else:
            gga_fields = []
        if rmc_part.startswith('GPRMC,'):
            rmc_fields = rmc_part[len('GPRMC,'):].split(',')
        else:
            rmc_fields = []

        # Expected minimal lengths per sender's __str__
        # GGA: time, lat, long, pos_fix, msl
        # RMC: time, status, lat, long, gnd_spd, gnd_course
        gga_lat = gga_fields[1] if len(gga_fields) >= 2 else ''
        gga_lon = gga_fields[2] if len(gga_fields) >= 3 else ''
        gga_msl = gga_fields[4] if len(gga_fields) >= 5 else ''

        rmc_lat = rmc_fields[2] if len(rmc_fields) >= 3 else ''
        rmc_lon = rmc_fields[3] if len(rmc_fields) >= 4 else ''
        rmc_spd = rmc_fields[4] if len(rmc_fields) >= 5 else ''

        # Prefer RMC lat/lon if present, else GGA
        lat_src = rmc_lat if rmc_lat not in (None, '') else gga_lat
        lon_src = rmc_lon if rmc_lon not in (None, '') else gga_lon

        lat_dd = nmea_degmin_to_decimal(lat_src, 2)
        lon_dd = nmea_degmin_to_decimal(lon_src, 3)
        alt_m = None
        try:
            alt_m = float(gga_msl) if gga_msl not in (None, '') else None
        except Exception:
            alt_m = None

        vel_ms = knots_to_mps(rmc_spd) if rmc_spd not in (None, '') else 0.0

        data = {
            'roll': 0,
            'pitch': 0,
            'yaw': 0,
            'latitude': lat_dd if lat_dd is not None else 0,
            'longitude': lon_dd if lon_dd is not None else 0,
            'altitude': alt_m if alt_m is not None else 0,
            'velocity': vel_ms,
            'temperature': 0,
            'pressure': 0
        }

        return fill_defaults(data)
    except Exception:
        return None


class StreamAssembler:
    """Assembles fragmented HAART frames from a byte stream.

    A frame is defined as: GPGGA,<...> ; GPRMC,<...>
    We extract a frame between a 'GPGGA,' start and the next 'GPGGA,' start.
    If the next start is not yet present but we have at least a full RMC header
    and fields, we may emit the current buffer tail as a frame (best effort).
    """

    def __init__(self, max_buffer=65536):
        self.buffer = bytearray()
        self.max_buffer = max_buffer

    def append(self, data: bytes):
        if not data:
            return
        self.buffer += data
        # Hard cap to avoid runaway growth; keep the last window
        if len(self.buffer) > self.max_buffer:
            # Try to keep from last GPGGA if present, else trim tail window
            marker = self.buffer.rfind(b'GPGGA,')
            if marker != -1:
                self.buffer = self.buffer[marker:]
            else:
                self.buffer = self.buffer[-self.max_buffer:]

    def extract_frames(self):
        frames = []
        while True:
            start = self.buffer.find(b'GPGGA,')
            if start == -1:
                # discard noise at front if buffer too big
                if len(self.buffer) > 2048:
                    self.buffer = self.buffer[-1024:]
                break

            # Drop leading noise
            if start > 0:
                del self.buffer[:start]

            # Find the separator and RMC header
            semi = self.buffer.find(b';', 6)  # after 'GPGGA,'
            if semi == -1:
                # wait for more data
                break

            rmc_idx = self.buffer.find(b'GPRMC,', semi + 1)
            if rmc_idx == -1:
                # wait for more data
                break

            # Heuristic: frame ends at next GPGGA start (next frame) if present
            next_start = self.buffer.find(b'GPGGA,', rmc_idx + 6)
            if next_start != -1:
                frame_bytes = bytes(self.buffer[:next_start])
                del self.buffer[:next_start]
                frames.append(self._clean_text(frame_bytes))
                continue

            # If no next start yet, check if we likely have complete RMC fields
            rmc_body = self.buffer[rmc_idx + len(b'GPRMC,'):]
            comma_count = rmc_body.count(b',')
            if comma_count >= 5:
                # emit everything we have as one frame
                frame_bytes = bytes(self.buffer)
                self.buffer.clear()
                frames.append(self._clean_text(frame_bytes))
                break

            # Not enough yet
            break

        return frames

    @staticmethod
    def _clean_text(b: bytes) -> str:
        # Keep printable ASCII and punctuation; drop controls
        text = b.decode('utf-8', errors='ignore')
        return ''.join(ch for ch in text if ch >= ' ')


def write_to_csv(data_dict, csv_path):
    """Write validated data to CSV file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            data_dict['roll'],
            data_dict['pitch'],
            data_dict['yaw'],
            data_dict['latitude'],
            data_dict['longitude'],
            data_dict['altitude'],
            data_dict['velocity'],
            data_dict['temperature'],
            data_dict['pressure']
        ])


def main():
    print("=" * 60)
    print("  GROUND STATION DATA RECEIVER")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--serial-port', default=SERIAL_PORT, help='Serial port (default COM5)')
    parser.add_argument('--baud', type=int, default=BAUD_RATE, help='Serial baud rate (default 9600)')
    args, _ = parser.parse_known_args()

    # Initialize CSV path for this run
    session_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_path = os.path.join(TELEMETRY_DIR, f"{session_ts}.csv")
    initialize_csv(csv_path)
    
    try:
        packet_count = 0
        error_count = 0

        assembler = StreamAssembler()

        # Serial receive path (E22/SX126x UART bridge)
        print(f"Connecting to E22900t22s module on {args.serial_port}...")
        ser = serial.Serial(
            port=args.serial_port,
            baudrate=args.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=TIMEOUT
        )

        print(f"Connected! Listening at {args.baud} baud...")
        print(f"Logging to: {csv_path}")
        print("-" * 60)

        while True:
            if ser.in_waiting > 0:
                raw_chunk = ser.read(ser.in_waiting)
                assembler.append(raw_chunk)
                frames = assembler.extract_frames()
                for frame in frames:
                    data_dict = parse_sensor_data(frame)
                    if data_dict is None:
                        error_count += 1
                        print(f"[ERROR] Failed to parse data: {frame[:80]}...")
                        continue

                    if not validate_data(data_dict):
                        error_count += 1
                        print(f"[ERROR] Invalid data values: {data_dict}")
                        continue

                    write_to_csv(data_dict, csv_path)
                    packet_count += 1

                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] Packet #{packet_count} - LOGGED")
                    print(f"  Orientation: R={data_dict['roll']}° P={data_dict['pitch']}° Y={data_dict['yaw']}°")
                    print(f"  GPS: {data_dict['latitude']}, {data_dict['longitude']} @ {data_dict['altitude']}m")
                    print(f"  Velocity: {data_dict['velocity']} m/s | Temp: {data_dict['temperature']}°C | Press: {data_dict['pressure']} hPa")
                    print(f"  Stats: {packet_count} logged, {error_count} errors")
                    print("-" * 60)

            time.sleep(0.05)
    
    except serial.SerialException as e:
        print(f"\n[ERROR] Could not open serial port {args.serial_port}")
        print(f"Details: {e}")
        print("Tip: Check Device Manager for the correct COM port")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nShutting down data receiver...")
        print(f"Final stats: {packet_count} packets logged, {error_count} errors")
        ser.close()
        sys.exit(0)
    
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

