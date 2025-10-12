#!/usr/bin/env python3
"""
UI Display - Ground Station Frontend
Retrofuturist ASCII-style GUI inspired by classic DOD terminal systems
"""

import pygame
import csv
import math
import os
import random
import argparse
from datetime import datetime

# Import visualization modules
from viz_map import draw_simple_map
from viz_cube import draw_3d_cube
from viz_landing import draw_landing_zone

# Import pre-flight and prediction modules
try:
    from preflight_menu import PreFlightMenu
    from cusf_predictor import CUSFPredictor
    from map_tiles import preload_flight_area
    PREFLIGHT_AVAILABLE = True
except ImportError:
    PREFLIGHT_AVAILABLE = False

# Configuration
CSV_FILE = 'telemetry_data.csv'
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MIN_WIDTH = 1024
MIN_HEIGHT = 768
FPS = 30

# Theme definitions
THEMES = {
    'dark': {
        'bg': (0, 0, 0),
        'primary': (255, 255, 255),
        'accent': (200, 200, 200),
        'dim': (100, 100, 100),
        'warning': (180, 180, 180),
        'alert': (150, 150, 150)
    },
    'light': {
        'bg': (240, 240, 240),
        'primary': (0, 0, 0),
        'accent': (40, 40, 40),
        'dim': (120, 120, 120),
        'warning': (60, 60, 60),
        'alert': (80, 80, 80)
    }
}

# Current theme
current_theme = 'dark'

def get_colors():
    """Get current theme colors"""
    return THEMES[current_theme]

# Minimal Banner
BANNER_TEXT = "GROUND STATION CONTROL INTERFACE v2.1"


def read_latest_telemetry():
    """Read the most recent telemetry data from CSV"""
    if not os.path.exists(CSV_FILE):
        return None
    
    try:
        with open(CSV_FILE, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                return rows[-1]
    except Exception:
        pass
    
    return None


def generate_dummy_telemetry(time_offset=0):
    """Generate random dummy telemetry data for testing"""
    # Create realistic-looking random values
    base_lat = 34.052235
    base_lon = -118.243683
    
    # Oscillating orientation values
    roll = math.sin(time_offset * 0.1) * 25 + random.uniform(-5, 5)
    pitch = math.cos(time_offset * 0.15) * 20 + random.uniform(-3, 3)
    yaw = (time_offset * 2) % 360
    
    # Drifting GPS position
    altitude = 1000 + time_offset * 3 + random.uniform(-50, 50)
    lat = base_lat + (time_offset * 0.0001) + random.uniform(-0.0001, 0.0001)
    lon = base_lon + (time_offset * 0.00008) + random.uniform(-0.0001, 0.0001)
    
    # Other telemetry
    velocity = 2.5 + random.uniform(-0.5, 0.5)
    temperature = 25 - (altitude / 150) + random.uniform(-1, 1)
    pressure = 1013.25 * math.exp(-altitude / 8500) + random.uniform(-2, 2)
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'roll': f'{roll:.2f}',
        'pitch': f'{pitch:.2f}',
        'yaw': f'{yaw:.2f}',
        'latitude': f'{lat:.6f}',
        'longitude': f'{lon:.6f}',
        'altitude': f'{altitude:.1f}',
        'velocity': f'{velocity:.2f}',
        'temperature': f'{temperature:.1f}',
        'pressure': f'{pressure:.2f}'
    }


def predict_landing(lat, lon, alt, velocity):
    """Predict balloon landing location"""
    if velocity == 0 or alt <= 0:
        return lat, lon
    
    descent_time = alt / 5.0
    drift_distance = velocity * descent_time / 1000.0
    
    lat_change = drift_distance / 111.0
    lon_change = drift_distance / (111.0 * math.cos(math.radians(lat)))
    
    return lat + lat_change, lon + lon_change


def draw_text(surface, text, pos, font, color=None):
    """Draw text on surface"""
    if color is None:
        color = get_colors()['primary']
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, pos)
    return text_surface.get_rect(topleft=pos)


def draw_section_title(surface, title, x, y, font, colors, sep_width, scale):
    draw_text(surface, title, (x, y), font, colors['accent'])
    line_height = int(20 * scale)
    pygame.draw.line(surface, colors['dim'], (x, y + line_height + int(5 * scale)), (x + sep_width, y + line_height + int(5 * scale)), 1)


# Visualization functions moved to separate files:
# - viz_map.py: GPS map visualization
# - viz_cube.py: 3D cube orientation visualization
# - viz_landing.py: Landing prediction visualization


def draw_scanlines(surface, width, height):
    """Draw CRT scanline effect"""
    colors = get_colors()
    scanline_color = colors['bg']
    # Subtle scanline effect
    if current_theme == 'dark':
        scanline_color = (5, 5, 5)
    else:
        scanline_color = (230, 230, 230)
    
    for y in range(0, height, 3):
        pygame.draw.line(surface, scanline_color, (0, y), (width, y), 1)


def draw_status_bar(surface, telemetry, font, width, height, scale=1.0):
    """Draw top status bar"""
    colors = get_colors()
    bar_height = int(30 * scale)
    
    # Background
    bar_bg = colors['bg']
    if current_theme == 'dark':
        bar_bg = (10, 10, 10)
    else:
        bar_bg = (220, 220, 220)
    pygame.draw.rect(surface, bar_bg, (0, 0, width, bar_height))
    
    # Timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    timestamp_text = f"[{timestamp}]"
    draw_text(surface, timestamp_text, (int(10 * scale), int(5 * scale)), font, colors['accent'])
    
    # Status indicator (center)
    if telemetry:
        status = "■ ACTIVE"
        color = colors['primary']
    else:
        status = "□ NO SIGNAL"
        color = colors['alert']
    
    status_width = font.size(status)[0]
    status_x = (width - status_width) // 2
    draw_text(surface, status, (status_x, int(5 * scale)), font, color)
    
    # Theme indicator (right)
    theme_text = f"[F1] THEME: {current_theme.upper()}"
    theme_width = font.size(theme_text)[0]
    draw_text(surface, theme_text, (width - theme_width - int(10 * scale), int(5 * scale)), font, colors['dim'])
    
    # Separator line
    pygame.draw.line(surface, colors['primary'], (0, bar_height), (width, bar_height), max(1, int(2 * scale)))


def main(dummy_mode=False, skip_preflight=False):
    global current_theme
    
    pygame.init()
    
    # Get display info to find screen resolution
    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    
    # Use 100% of screen size (fullscreen windowed mode)
    window_width = screen_width
    window_height = screen_height
    
    # Create fullscreen window (borderless fullscreen)
    screen = pygame.display.set_mode((window_width, window_height), pygame.NOFRAME | pygame.RESIZABLE)
    
    # Set window title based on mode
    title = "Ground Station Control Interface"
    if dummy_mode:
        title += " [DUMMY MODE]"
    pygame.display.set_caption(title)
    
    clock = pygame.time.Clock()
    
    # Current window dimensions
    current_width = window_width
    current_height = window_height
    
    # Dummy mode counter
    dummy_time = 0
    
    # Flight mode state: start in flight; access pre-flight via F2
    mode = 'flight'
    preflight_menu = None
    cusf_predictor = None
    flight_start_time = None
    
    # Initialize pre-flight menu if available
    if mode == 'preflight':
        colors = get_colors()
        preflight_menu = PreFlightMenu(current_width, current_height, colors, current_theme)
        cusf_predictor = CUSFPredictor()
    
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False  # Exit in any mode
                elif event.key == pygame.K_F1:
                    # Toggle theme
                    current_theme = 'light' if current_theme == 'dark' else 'dark'
                    if preflight_menu:
                        preflight_menu.colors = get_colors()
                        preflight_menu.theme = current_theme
                elif event.key == pygame.K_F2:
                    # Toggle pre-flight menu (lazy import to avoid hard dependency at startup)
                    if mode == 'flight':
                        try:
                            # Ensure dependencies are available when toggled
                            from preflight_menu import PreFlightMenu as _PFM
                            from cusf_predictor import CUSFPredictor as _CUSF
                            # Initialize
                            colors = get_colors()
                            preflight_menu = _PFM(current_width, current_height, colors, current_theme)
                            cusf_predictor = _CUSF()
                            mode = 'preflight'
                        except Exception as _e:
                            print(f"Pre-flight unavailable: {_e}")
                    else:
                        mode = 'flight'
                        preflight_menu = None
                elif event.key == pygame.K_F11:
                    # Toggle fullscreen
                    pygame.display.toggle_fullscreen()
                elif mode == 'preflight' and preflight_menu:
                    # Pass keydown to preflight menu
                    preflight_menu.handle_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if mode == 'preflight' and preflight_menu:
                    action = preflight_menu.handle_click(event.pos)
                    
                    if action == 'download':
                        # Download prediction and map tiles
                        preflight_menu.set_download_status("Downloading CUSF prediction...")
                        pygame.display.flip()
                        
                        # Download CUSF prediction
                        result = cusf_predictor.download_prediction(preflight_menu.config)
                        
                        if result:
                            preflight_menu.set_download_status("Downloading map tiles...")
                            pygame.display.flip()
                            
                            # Download map tiles
                            try:
                                # Prefer path-based preloading if CUSF prediction exists
                                try:
                                    traj = cusf_predictor.get_trajectory() if cusf_predictor else []
                                    if traj:
                                        # Reduce to (lat, lon) pairs
                                        path_points = [(p[0], p[1]) for p in traj]
                                        from map_tiles import preload_tiles_along_path
                                        preload_tiles_along_path(
                                            path_points,
                                            buffer_km=preflight_menu.config['map_radius_km'],
                                            zoom_levels=preflight_menu.config['map_zoom_levels']
                                        )
                                    else:
                                        from map_tiles import preload_flight_area
                                        preload_flight_area(
                                            preflight_menu.config['launch_latitude'],
                                            preflight_menu.config['launch_longitude'],
                                            max_radius_km=preflight_menu.config['map_radius_km'],
                                            zoom_levels=preflight_menu.config['map_zoom_levels']
                                        )
                                except Exception as _e:
                                    from map_tiles import preload_flight_area
                                    preload_flight_area(
                                        preflight_menu.config['launch_latitude'],
                                        preflight_menu.config['launch_longitude'],
                                        max_radius_km=preflight_menu.config['map_radius_km'],
                                        zoom_levels=preflight_menu.config['map_zoom_levels']
                                    )
                                preflight_menu.set_download_status("✓ Download complete! Ready to start flight.")
                                preflight_menu.set_download_complete()
                            except Exception as e:
                                preflight_menu.set_download_status(f"✗ Map download error: {e}")
                        else:
                            preflight_menu.set_download_status("✗ CUSF prediction download failed")
                    
                    elif action == 'start_flight':
                        # Switch to flight mode
                        mode = 'flight'
                        flight_start_time = datetime.now()
                        preflight_menu = None
                        print(f"Flight started at {flight_start_time}")
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                current_width = max(event.w, MIN_WIDTH)
                current_height = max(event.h, MIN_HEIGHT)
                screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)
                
                if preflight_menu:
                    preflight_menu.width = current_width
                    preflight_menu.height = current_height
        
        # Calculate scale factor based on window size
        scale_x = current_width / WINDOW_WIDTH
        scale_y = current_height / WINDOW_HEIGHT
        scale = min(scale_x, scale_y)
        
        # Load fonts based on scale
        try:
            font_size = max(12, int(16 * scale))
            font_large_size = max(14, int(20 * scale))
            font = pygame.font.SysFont('consolas', font_size)
            font_large = pygame.font.SysFont('consolas', font_large_size)
        except:
            font_size = max(14, int(18 * scale))
            font_large_size = max(16, int(22 * scale))
            font = pygame.font.Font(None, font_size)
            font_large = pygame.font.Font(None, font_large_size)
        
        # Read latest telemetry or generate dummy data
        if dummy_mode:
            telemetry = generate_dummy_telemetry(dummy_time)
            dummy_time += 0.1  # Increment time for animation
        else:
            telemetry = read_latest_telemetry()
        
        # Clear screen
        colors = get_colors()
        screen.fill(colors['bg'])
        
        # Pre-flight menu mode
        if mode == 'preflight' and preflight_menu:
            preflight_menu.draw(screen, font, font_large)
            pygame.display.flip()
            clock.tick(FPS)
            continue
        
        # Flight mode - normal telemetry display
        # Draw CRT scanlines
        draw_scanlines(screen, current_width, current_height)
        
        # Draw status bar
        status_bar_height = int(40 * scale)
        draw_status_bar(screen, telemetry, font, current_width, current_height, scale)
        
        # Draw minimal banner
        banner_start_y = status_bar_height + int(10 * scale)
        banner_width = font.size(BANNER_TEXT)[0]
        banner_x = max(10, (current_width - banner_width) // 2)
        draw_text(screen, BANNER_TEXT, (banner_x, banner_start_y), font, colors['primary'])
        
        if telemetry:
            try:
                # Parse telemetry data
                roll = float(telemetry['roll'])
                pitch = float(telemetry['pitch'])
                yaw = float(telemetry['yaw'])
                lat = float(telemetry['latitude'])
                lon = float(telemetry['longitude'])
                alt = float(telemetry['altitude'])
                vel = float(telemetry['velocity'])
                temp = float(telemetry['temperature'])
                pressure = float(telemetry['pressure'])
                
                # Calculate grid layout with proper margins
                content_start_y = banner_start_y + int(40 * scale)
                margin = int(20 * scale)
                
                # Calculate available space
                available_width = current_width - (4 * margin)
                available_height = current_height - content_start_y - int(50 * scale)  # Reserve space at bottom
                
                # Calculate column widths (3 columns)
                col_width = max(250, available_width // 3)  # Minimum width per column
                
                # Left column: RAW DATA
                left_x = margin
                raw_data = [
                    "RAW TELEMETRY DATA",
                    "══════════════════════════",
                    f"ROLL:        {roll:>8.2f}°",
                    f"PITCH:       {pitch:>8.2f}°",
                    f"YAW:         {yaw:>8.2f}°",
                    "",
                    f"LATITUDE:    {lat:>12.6f}°",
                    f"LONGITUDE:   {lon:>12.6f}°",
                    f"ALTITUDE:    {alt:>10.1f} m",
                    "",
                    f"VELOCITY:    {vel:>10.2f} m/s",
                    f"TEMPERATURE: {temp:>10.1f} °C",
                    f"PRESSURE:    {pressure:>10.2f} hPa",
                    "",
                    f"GPS FIX:     {'3D LOCK':>10}",
                    f"SATELLITES:  {12:>10}",
                    "",
                    f"TIMESTAMP:   {telemetry.get('timestamp', 'N/A')}"
                ]
                
                y_pos = content_start_y
                line_height = int(20 * scale)
                for i, line in enumerate(raw_data):
                    if i == 0:
                        draw_text(screen, line, (left_x, y_pos), font, colors['accent'])
                    elif i == 1:
                        draw_text(screen, line, (left_x, y_pos), font, colors['dim'])
                    else:
                        draw_text(screen, line, (left_x, y_pos), font, colors['primary'])
                    y_pos += line_height
                
                # Middle column: CURRENT GPS POSITION MAP
                middle_x = margin + col_width + margin
                map_title_y = content_start_y
                
                # Ensure middle column doesn't overflow
                if middle_x + col_width > current_width - margin:
                    middle_x = margin + (available_width // 3)
                
                sep_width = min(int(200 * scale), col_width - int(20 * scale))
                draw_section_title(screen, "CURRENT POSITION", middle_x, map_title_y, font, colors, sep_width, scale)
                
                map_y = map_title_y + int(50 * scale)
                # Scale map to fit available space
                max_map_size = min(col_width - int(40*scale), available_height - int(200*scale))
                map_size = max(150, min(max_map_size, int(300 * scale)))
                draw_simple_map(screen, lat, lon, (middle_x, map_y), 
                              (map_size, map_size), font, colors, scale)
                
                # Additional GPS info below map
                info_y = map_y + map_size + int(30 * scale)
                gps_info = [
                    f"ALT: {alt:.1f} m",
                    f"VEL: {vel:.2f} m/s",
                    f"SPD: {vel*3.6:.1f} km/h"
                ]
                for line in gps_info:
                    draw_text(screen, line, (middle_x, info_y), font, colors['primary'])
                    info_y += line_height
                
                # Right column: LANDING PREDICTION
                right_x = margin + 2 * (col_width + margin)
                
                # Ensure right column doesn't overflow
                if right_x + col_width > current_width - margin:
                    right_x = current_width - col_width - margin
                
                # Calculate prediction error if we have CUSF data and flight has started
                prediction_error = None
                if cusf_predictor and flight_start_time:
                    elapsed_seconds = (datetime.now() - flight_start_time).total_seconds()
                    prediction_error = cusf_predictor.calculate_prediction_error(
                        lat, lon, alt, elapsed_seconds
                    )
                    
                    # Use CUSF landing prediction if available
                    cusf_landing = cusf_predictor.get_landing_location()
                    if cusf_landing:
                        pred_lat, pred_lon = cusf_landing[0], cusf_landing[1]
                    else:
                        pred_lat, pred_lon = predict_landing(lat, lon, alt, vel)
                else:
                    pred_lat, pred_lon = predict_landing(lat, lon, alt, vel)
                
                descent_time = (alt / 5.0) / 60
                
                pred_title_y = content_start_y
                sep_width = min(int(200 * scale), col_width - int(20 * scale))
                draw_section_title(screen, "LANDING PREDICTION", right_x, pred_title_y, font, colors, sep_width, scale)
                
                pred_map_y = pred_title_y + int(50 * scale)
                draw_landing_zone(screen, lat, lon, pred_lat, pred_lon, 
                                (right_x, pred_map_y), 
                                (map_size, map_size), font, colors, scale,
                                prediction_error=prediction_error)
                
                # Landing info below map
                land_info_y = pred_map_y + map_size + int(30 * scale)
                landing_info = [
                    f"EST. LAT: {pred_lat:.6f}°",
                    f"EST. LON: {pred_lon:.6f}°",
                    f"TIME:     {descent_time:.1f} min",
                    f"CONF:     HIGH"
                ]
                for line in landing_info:
                    draw_text(screen, line, (right_x, land_info_y), font, colors['warning'])
                    land_info_y += line_height
                
                # Bottom row: 3D Orientation Cube (below raw data)
                cube_section_y = y_pos + int(40 * scale)
                
                # Only draw if there's enough space
                if cube_section_y < current_height - int(200 * scale):
                    cube_title = "PAYLOAD ORIENTATION"
                    sep_width = min(int(200 * scale), col_width - int(20 * scale))
                    draw_section_title(screen, cube_title, left_x, cube_section_y, font, colors, sep_width, scale)
                    
                    cube_y = cube_section_y + int(50 * scale)
                    cube_display_size = min(col_width - int(40*scale), int(250 * scale))
                    
                    # Ensure cube fits on screen
                    if cube_y + cube_display_size < current_height - int(50 * scale):
                        draw_3d_cube(screen, roll, pitch, yaw, (left_x, cube_y), 
                                   (cube_display_size, cube_display_size), colors, current_theme, scale)
                
                # Bottom info bar
                info_text = f"DATA: {CSV_FILE} │ FPS: {FPS} │ [F1] THEME │ [ESC] EXIT │ [F11] TOGGLE FULLSCREEN"
                draw_text(screen, info_text, (margin, int(current_height - 30*scale)), font, colors['dim'])
                
            except (ValueError, KeyError) as e:
                # Data error
                error_msg = f">>> DATA ERROR: {str(e)} <<<"
                draw_text(screen, error_msg, (current_width // 2 - int(200*scale), current_height // 2), 
                         font_large, colors['alert'])
        else:
            # No data message
            msg = ">>> WAITING FOR TELEMETRY DATA <<<"
            submsg = f"MONITORING: {CSV_FILE}"
            draw_text(screen, msg, (current_width // 2 - int(250*scale), current_height // 2 - int(20*scale)), 
                     font_large, colors['warning'])
            draw_text(screen, submsg, (current_width // 2 - int(200*scale), current_height // 2 + int(20*scale)), 
                     font, colors['dim'])
        
        # Add glow effect by drawing slightly offset
        # (Simple CRT glow simulation)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ground Station Control Interface')
    parser.add_argument('--dummy', action='store_true', 
                       help='Run in dummy mode with simulated telemetry data')
    parser.add_argument('--skip-preflight', action='store_true',
                       help='Skip pre-flight menu and go straight to flight mode')
    parser.add_argument('--theme', choices=['dark', 'light'], default='dark',
                       help='Initial color theme (default: dark)')
    args = parser.parse_args()
    
    # Set initial theme
    current_theme = args.theme
    
    # Print mode information
    if args.dummy:
        print("=" * 60)
        print("  GROUND STATION CONTROL INTERFACE - DUMMY MODE")
        print("=" * 60)
        print("Running with simulated telemetry data")
        print("Press [F1] to toggle theme")
        print("-" * 60)
    
    
    try:
        main(dummy_mode=args.dummy, skip_preflight=args.skip_preflight)
    except KeyboardInterrupt:
        pass
    
    print("\n[SYSTEM] Ground Station Interface Terminated.")
