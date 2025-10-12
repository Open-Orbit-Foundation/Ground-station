# Ground Station Control Interface

High-altitude balloon telemetry system with cyberpunk-style UI for the E22900t22s LoRa module.

## Components

### 1. Data Receiver (`data_receiver.py`)
Backend that receives sensor data from the LoRa module and logs to CSV with validation.

### 2. UI Display (`ui_display.py`)
Main UI application - retrofuturist ASCII-style GUI window inspired by classic DOD terminal systems with CRT effects.

### 3. Visualization Modules
- `viz_map.py` - GPS position map visualization
- `viz_cube.py` - 3D payload orientation cube
- `viz_landing.py` - Landing prediction trajectory visualization

### 4. Test Data Generator (`test_data_generator.py`)
Generates simulated telemetry data for testing without hardware.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the serial port in `data_receiver.py`:
   - Windows: `COM3`, `COM4`, `COM5`, etc.
   - Linux/Raspberry Pi: `/dev/ttyUSB0`, `/dev/serial0`, `/dev/ttyAMA0`, etc.

3. Ensure the E22900t22s module is properly connected and powered.

## Usage

### Running the Data Receiver

Start the backend to receive and log data:
```bash
python data_receiver.py
```

The receiver expects sensor data in CSV format:
```
roll,pitch,yaw,latitude,longitude,altitude,velocity,temperature,pressure
```

Example: `45.2,12.5,180.0,34.052235,-118.243683,15000.0,5.5,25.3,1013.25`

Data is logged to `telemetry_data.csv` with automatic validation.

### Receiving with RTL-SDR (Windows)

You can replace the proprietary SX126x/UART module by using an RTL-SDR and an external LoRa demodulator that outputs decoded payloads over UDP.

1. Install an RTL-SDR driver and a LoRa demodulator tool that can output ASCII payloads via UDP. Example stacks include SDRSharp/SDR++ feeding gr-lora or a standalone Windows demodulator that emits UDP lines.
2. Start your demodulator to send decoded lines like `roll,pitch,yaw,lat,lon,alt,vel,temp,pressure` to a UDP port, e.g., 16886.
3. Run the receiver in UDP mode:
```bash
python data_receiver.py --udp --udp-host 0.0.0.0 --udp-port 16886
```

Quick print-only monitor without CSV logging:
```bash
python CLI_Test.py --udp --udp-host 0.0.0.0 --udp-port 16886
```

Notes:
- Ensure the demodulator outputs one payload per UDP datagram as a UTF-8 string.
- The expected format is identical to the serial path: `roll,pitch,yaw,lat,lon,alt,vel,temp,pressure`.

### Running the UI

#### Normal Mode (with Pre-Flight Configuration)
Launch with pre-flight menu to configure and download offline data:
```bash
python ui_display.py
```

**Pre-flight menu allows you to:**
1. Configure launch parameters (lat/lon, ascent rate, burst altitude, etc.)
2. Download CUSF trajectory prediction
3. Download offline map tiles
4. Click "DOWNLOAD & LOCK" to prepare for flight
5. Click "START FLIGHT" when ready to launch

See [PREFLIGHT_GUIDE.md](PREFLIGHT_GUIDE.md) for detailed instructions.

#### Skip Pre-Flight (Quick Start)
Skip configuration and go straight to flight mode:
```bash
python ui_display.py --skip-preflight
```

#### Dummy Mode (for testing)
Run the UI with simulated telemetry data:
```bash
python ui_display.py --dummy
```

This generates random but realistic telemetry data so you can test the UI without hardware or the data receiver.

#### Optional Arguments
```bash
python ui_display.py --dummy                # Test mode with fake data
python ui_display.py --skip-preflight       # Skip pre-flight menu
python ui_display.py --theme light          # Start with light theme
python ui_display.py -h                     # Show help
```

The UI displays:

**Pre-Flight Mode:**
- Configuration menu for launch parameters
- "DOWNLOAD & LOCK" button (downloads CUSF prediction + map tiles)
- "START FLIGHT" button (begins real-time tracking)

**Flight Mode:**
- Minimal single-line banner
- **Grid Layout (4 sections):**
  - **Top Left:** Raw telemetry data (all sensor readings)
  - **Top Middle:** Current GPS position with offline OSM map tiles
  - **Top Right:** CUSF landing prediction with real-time error tracking
  - **Bottom Left:** 3D payload orientation cube (rotates with roll/pitch/yaw)
- **Real-time Prediction Error:** Shows horizontal distance and altitude difference from CUSF predicted path
- CRT monitor aesthetic with scanlines
- B/W color scheme with dark mode (white on black) and light mode (black on white)
- **Fullscreen by default** - uses 100% of screen resolution

**Controls:**
- `F1` - Toggle between dark mode and light mode
- `F11` - Toggle fullscreen on/off
- `ESC` - Exit (pre-flight only, disabled during flight)

### Testing Without Hardware

**Option 1: Dummy Mode (Easiest)**
Test the UI immediately without any setup:
```bash
python ui_display.py --dummy
```

**Option 2: Simulate Full System**
Test the complete data pipeline (receiver + UI):
```bash
# Terminal 1: Generate simulated telemetry data
python test_data_generator.py

# Terminal 2: Run the UI
python ui_display.py
```

## Data Format

CSV columns logged:
- `timestamp` - Local time of data reception
- `roll` - Roll angle in degrees (-180 to 180)
- `pitch` - Pitch angle in degrees (-90 to 90)
- `yaw` - Yaw/heading in degrees (-180 to 180)
- `latitude` - GPS latitude (-90 to 90)
- `longitude` - GPS longitude (-180 to 180)
- `altitude` - Altitude in meters
- `velocity` - Velocity in m/s
- `temperature` - Temperature in Celsius
- `pressure` - Atmospheric pressure in hPa

## Configuration

Default settings in `data_receiver.py`:
- Baud Rate: 9600 (standard for E22 modules)
- Data Bits: 8
- Parity: None
- Stop Bits: 1

Adjust these settings if your module is configured differently.
