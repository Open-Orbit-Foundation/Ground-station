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

# Import prediction module (keep separate for clarity and caching)
from cusf_predictor import CUSFPredictor
from map_tiles import MapRenderer, tiles_exist_for_area

# Configuration
CSV_FILE = 'telemetry_data.csv'
TELEMETRY_DIR = 'Telemetry'
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MIN_WIDTH = 1024
MIN_HEIGHT = 768
FPS = 20

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
# ===== Merged: viz_map.draw_simple_map =====

# Tiles are rendered only if present in cache; otherwise we draw a grid


def draw_simple_map(surface, lat, lon, pos, size, font, colors, scale=1.0, use_tiles=True, zoom=11):
    """
    Draw map with current position marker
    """
    x, y = pos
    width, height = size
    
    # Render tiles only if the full area is cached; otherwise show grid
    if use_tiles and tiles_exist_for_area(lat, lon, zoom, (x, y, width, height)):
        renderer = MapRenderer()
        renderer.render_map(surface, lat, lon, zoom, (x, y, width, height), colors)
        # Draw coordinates below map
        coord_y = y + height + int(10 * scale)
        coord_text = f"{lat:.6f}°, {lon:.6f}°"
        text_surface = font.render(coord_text, True, colors['accent'])
        surface.blit(text_surface, (x + int(10*scale), coord_y))
        return

    _draw_grid_map(surface, lat, lon, x, y, width, height, font, colors, scale)


def _draw_grid_map(surface, lat, lon, x, y, width, height, font, colors, scale):
    """Draw simple grid-based map (fallback)"""
    # Draw border
    pygame.draw.rect(surface, colors['accent'], (x, y, width, height), max(1, int(2*scale)))
    
    # Draw grid lines
    grid_spacing_x = width // 5
    grid_spacing_y = height // 5
    
    for i in range(1, 5):
        # Vertical lines
        pygame.draw.line(surface, colors['dim'], 
                        (x + i * grid_spacing_x, y), 
                        (x + i * grid_spacing_x, y + height), 1)
        # Horizontal lines
        pygame.draw.line(surface, colors['dim'], 
                        (x, y + i * grid_spacing_y), 
                        (x + width, y + i * grid_spacing_y), 1)
    
    # Draw center marker (current position)
    center_x = x + width // 2
    center_y = y + height // 2
    marker_size = int(10 * scale)
    
    # Cross marker
    pygame.draw.line(surface, colors['primary'], 
                    (center_x - marker_size, center_y), 
                    (center_x + marker_size, center_y), max(2, int(3*scale)))
    pygame.draw.line(surface, colors['primary'], 
                    (center_x, center_y - marker_size), 
                    (center_x, center_y + marker_size), max(2, int(3*scale)))
    pygame.draw.circle(surface, colors['primary'], (center_x, center_y), 
                      int(5 * scale), max(1, int(2*scale)))
    
    # Draw coordinates below map
    coord_y = y + height + int(10 * scale)
    coord_text = f"{lat:.6f}°, {lon:.6f}°"
    text_surface = font.render(coord_text, True, colors['accent'])
    surface.blit(text_surface, (x + int(10*scale), coord_y))




# ===== Merged: viz_landing.draw_landing_zone =====

def draw_landing_zone(surface, current_lat, current_lon, pred_lat, pred_lon, pos, size, font, colors, scale=1.0, prediction_error=None):
    """
    Draw landing prediction visualization
    """
    x, y = pos
    width, height = size
    
    # Draw border
    pygame.draw.rect(surface, colors['warning'], (x, y, width, height), max(1, int(2*scale)))
    
    # Draw grid
    grid_spacing_x = width // 5
    grid_spacing_y = height // 5
    
    for i in range(1, 5):
        pygame.draw.line(surface, colors['dim'], 
                        (x + i * grid_spacing_x, y), 
                        (x + i * grid_spacing_x, y + height), 1)
        pygame.draw.line(surface, colors['dim'], 
                        (x, y + i * grid_spacing_y), 
                        (x + width, y + i * grid_spacing_y), 1)
    
    # Calculate relative positions for visualization
    center_x = x + width // 2
    center_y = y + height // 2
    
    # Draw current position
    pygame.draw.circle(surface, colors['primary'], (center_x, center_y), 
                      int(5 * scale), 0)
    
    # Calculate predicted position offset (scaled for visualization)
    lat_diff = pred_lat - current_lat
    lon_diff = pred_lon - current_lon
    
    # Scale factor for visualization
    vis_scale = 5000
    offset_x = int(lon_diff * vis_scale)
    offset_y = int(-lat_diff * vis_scale)
    
    # Clamp to box
    pred_x = max(x + 10, min(x + width - 10, center_x + offset_x))
    pred_y = max(y + 10, min(y + height - 10, center_y + offset_y))
    
    # Draw trajectory line
    pygame.draw.line(surface, colors['warning'], 
                    (center_x, center_y), (pred_x, pred_y), 
                    max(1, int(2*scale)))
    
    # Draw landing marker
    marker_size = int(8 * scale)
    pygame.draw.line(surface, colors['warning'], 
                    (pred_x - marker_size, pred_y - marker_size), 
                    (pred_x + marker_size, pred_y + marker_size), max(2, int(3*scale)))
    pygame.draw.line(surface, colors['warning'], 
                    (pred_x - marker_size, pred_y + marker_size), 
                    (pred_x + marker_size, pred_y - marker_size), max(2, int(3*scale)))
    
    # Draw coordinates below map
    coord_y = y + height + int(10 * scale)
    coord_text = f"{pred_lat:.6f}°, {pred_lon:.6f}°"
    text_surface = font.render(coord_text, True, colors['warning'])
    surface.blit(text_surface, (x + int(10*scale), coord_y))
    
    # Draw prediction error if available
    if prediction_error:
        error_y = coord_y + int(25 * scale)
        horiz_error = prediction_error['horizontal_error_km']
        error_color = colors['warning'] if horiz_error < 5 else colors['alert']
        error_text = f"ERROR: {horiz_error:.2f} km"
        error_surf = font.render(error_text, True, error_color)
        surface.blit(error_surf, (x + int(10*scale), error_y))
        alt_error = prediction_error['altitude_error_m']
        alt_text = f"ALT Δ: {alt_error:+.0f} m"
        alt_surf = font.render(alt_text, True, colors['dim'])
        surface.blit(alt_surf, (x + int(10*scale), error_y + int(20*scale)))


# ===== Merged: preflight_menu.PreFlightMenu =====

class PreFlightMenu:
    """Pre-flight configuration menu"""
    
    def __init__(self, screen_width, screen_height, colors, theme):
        self.width = screen_width
        self.height = screen_height
        self.colors = colors
        self.theme = theme
        
        # Configuration state
        from datetime import timedelta
        self.config = {
            'launch_latitude': 34.052235,
            'launch_longitude': -118.243683,
            'launch_altitude': 0,
            'launch_datetime': datetime.now() + timedelta(hours=1),
            'ascent_rate': 5.0,
            'burst_altitude': 30000,
            'descent_rate': 5.0,
            'map_zoom_levels': [10, 11, 12],
            'map_radius_km': 50
        }
        
        # UI state
        self.active_field = None
        self.download_status = ""
        self.download_complete = False
        self.locked = False
        
        # Input buffer for active field
        self.input_buffer = ""
    
    def handle_keydown(self, event):
        """Handle keyboard input"""
        if self.locked:
            return
        
        if self.active_field is None:
            return
        
        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            # Commit the input
            self._commit_input()
            self.active_field = None
            self.input_buffer = ""
        
        elif event.key == pygame.K_ESCAPE:
            # Cancel input
            self.active_field = None
            self.input_buffer = ""
        
        elif event.key == pygame.K_BACKSPACE:
            self.input_buffer = self.input_buffer[:-1]
        
        elif event.unicode.isprintable():
            self.input_buffer += event.unicode
    
    def handle_click(self, pos):
        """Handle mouse click"""
        if self.locked:
            return None
        
        x, y = pos
        
        # Check field clicks
        field_y = int(self.height * 0.2)
        line_height = 30
        
        fields = [
            'launch_latitude', 'launch_longitude', 'launch_altitude',
            'ascent_rate', 'burst_altitude', 'descent_rate'
        ]
        
        for i, field in enumerate(fields):
            field_rect = pygame.Rect(int(self.width * 0.3), field_y + i * line_height, 
                                    int(self.width * 0.4), 25)
            if field_rect.collidepoint(pos):
                self.active_field = field
                self.input_buffer = str(self.config[field])
                return None
        
        # Check button clicks
        button_y = int(self.height * 0.65)
        
        # Download button
        download_button = pygame.Rect(int(self.width * 0.25), button_y, 
                                     int(self.width * 0.2), 50)
        if download_button.collidepoint(pos) and not self.locked:
            return 'download'
        
        # Start flight button (only if downloaded)
        if self.download_complete:
            start_button = pygame.Rect(int(self.width * 0.55), button_y, 
                                      int(self.width * 0.2), 50)
            if start_button.collidepoint(pos):
                return 'start_flight'
        
        return None
    
    def _commit_input(self):
        """Commit the input buffer to config"""
        if self.active_field is None:
            return
        
        # Parse based on field type
        if self.active_field in ['launch_latitude', 'launch_longitude']:
            self.config[self.active_field] = float(self.input_buffer)
        elif self.active_field in ['launch_altitude', 'burst_altitude']:
            self.config[self.active_field] = int(self.input_buffer)
        elif self.active_field in ['ascent_rate', 'descent_rate']:
            self.config[self.active_field] = float(self.input_buffer)
    
    def set_download_status(self, status):
        """Update download status message"""
        self.download_status = status
    
    def set_download_complete(self):
        """Mark download as complete"""
        self.download_complete = True
        self.locked = True
    
    def draw(self, surface, font, font_large):
        """Draw the pre-flight menu"""
        colors = self.colors
        
        # Background
        surface.fill(colors['bg'])
        
        # Title
        title = "PRE-FLIGHT CONFIGURATION"
        title_surf = font_large.render(title, True, colors['primary'])
        title_rect = title_surf.get_rect(center=(self.width // 2, int(self.height * 0.1)))
        surface.blit(title_surf, title_rect)
        
        # Draw horizontal line
        pygame.draw.line(surface, colors['accent'], 
                        (int(self.width * 0.2), int(self.height * 0.15)),
                        (int(self.width * 0.8), int(self.height * 0.15)), 2)
        
        # Configuration fields
        field_y = int(self.height * 0.2)
        line_height = 30
        label_x = int(self.width * 0.15)
        value_x = int(self.width * 0.3)
        
        fields = [
            ('Launch Latitude:', 'launch_latitude', '°'),
            ('Launch Longitude:', 'launch_longitude', '°'),
            ('Launch Altitude:', 'launch_altitude', 'm'),
            ('Ascent Rate:', 'ascent_rate', 'm/s'),
            ('Burst Altitude:', 'burst_altitude', 'm'),
            ('Descent Rate:', 'descent_rate', 'm/s'),
        ]
        
        for i, (label, field_name, unit) in enumerate(fields):
            y = field_y + i * line_height
            
            # Label
            label_surf = font.render(label, True, colors['primary'])
            surface.blit(label_surf, (label_x, y))
            
            # Value box
            is_active = (self.active_field == field_name)
            box_color = colors['accent'] if is_active else colors['dim']
            
            value_rect = pygame.Rect(value_x, y, int(self.width * 0.4), 25)
            pygame.draw.rect(surface, box_color, value_rect, 2)
            
            # Value text
            if is_active and not self.locked:
                display_value = self.input_buffer + "_"
            else:
                display_value = f"{self.config[field_name]}"
            
            value_surf = font.render(f"{display_value} {unit}", True, colors['primary'])
            surface.blit(value_surf, (value_x + 10, y + 3))
        
        # Additional info
        info_y = field_y + len(fields) * line_height + 20
        info_lines = [
            f"Map Radius: {self.config['map_radius_km']} km",
            f"Zoom Levels: {', '.join(map(str, self.config['map_zoom_levels']))}"
        ]
        
        for i, line in enumerate(info_lines):
            info_surf = font.render(line, True, colors['dim'])
            surface.blit(info_surf, (label_x, info_y + i * 20))
        
        # Buttons
        button_y = int(self.height * 0.65)
        
        # Download & Lock button
        download_button = pygame.Rect(int(self.width * 0.25), button_y, 
                                     int(self.width * 0.2), 50)
        download_color = colors['dim'] if self.locked else colors['accent']
        pygame.draw.rect(surface, download_color, download_button, 3 if not self.locked else 1)
        
        download_text = "LOCKED" if self.locked else "DOWNLOAD & LOCK"
        download_surf = font.render(download_text, True, colors['primary'] if not self.locked else colors['dim'])
        download_rect = download_surf.get_rect(center=download_button.center)
        surface.blit(download_surf, download_rect)
        
        # Start Flight button (only if download complete)
        if self.download_complete:
            start_button = pygame.Rect(int(self.width * 0.55), button_y, 
                                      int(self.width * 0.2), 50)
            pygame.draw.rect(surface, colors['warning'], start_button, 3)
            
            start_surf = font.render("START FLIGHT", True, colors['warning'])
            start_rect = start_surf.get_rect(center=start_button.center)
            surface.blit(start_surf, start_rect)
        
        # Status message
        if self.download_status:
            status_y = button_y + 80
            status_surf = font.render(self.download_status, True, colors['accent'])
            status_rect = status_surf.get_rect(center=(self.width // 2, status_y))
            surface.blit(status_surf, status_rect)
        
        # Instructions
        if not self.locked:
            inst_y = int(self.height * 0.85)
            instructions = [
                "Click field to edit | ENTER to confirm | ESC to cancel",
                "Download will fetch CUSF prediction and map tiles"
            ]
            
            for i, inst in enumerate(instructions):
                inst_surf = font.render(inst, True, colors['dim'])
                inst_rect = inst_surf.get_rect(center=(self.width // 2, inst_y + i * 20))
                surface.blit(inst_surf, inst_rect)


_telemetry_cache = {
    'last_row': None,
    'last_check_ts': 0.0,
    'last_mtime': 0.0,
    'last_size': 0,
    'csv_path': None,
    'dir_check_ts': 0.0
}

def _get_current_csv_path():
    """Return path to most recent Telemetry CSV, else fallback to CSV_FILE.

    Caches discovery for ~2 seconds to avoid frequent directory scans.
    """
    now = datetime.now().timestamp()
    cached_path = _telemetry_cache.get('csv_path')
    if cached_path and (now - _telemetry_cache.get('dir_check_ts', 0.0) < 2.0) and os.path.exists(cached_path):
        return cached_path

    latest = None
    latest_mtime = -1
    try:
        if os.path.isdir(TELEMETRY_DIR):
            for name in os.listdir(TELEMETRY_DIR):
                if not name.lower().endswith('.csv'):
                    continue
                path = os.path.join(TELEMETRY_DIR, name)
                try:
                    mtime = os.path.getmtime(path)
                except Exception:
                    continue
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest = path
    except Exception:
        latest = None

    chosen = latest if latest else CSV_FILE
    _telemetry_cache['csv_path'] = chosen
    _telemetry_cache['dir_check_ts'] = now
    return chosen

def read_latest_telemetry():
    """Read the most recent telemetry row efficiently (tail the CSV)."""
    path = _get_current_csv_path()
    if not os.path.exists(path):
        return None
    
    try:
        stat = os.stat(path)
        now = datetime.now().timestamp()

        # Rate limit checks (~2 Hz) if file unchanged
        if (
            _telemetry_cache['last_row'] is not None and
            stat.st_mtime == _telemetry_cache['last_mtime'] and
            stat.st_size == _telemetry_cache['last_size'] and
            (now - _telemetry_cache['last_check_ts']) < 0.5
        ):
            return _telemetry_cache['last_row']

        # Read only the tail of the file to get the last CSV line
        with open(path, 'rb') as f:
            size = stat.st_size
            read_from = max(0, size - 8192)
            if read_from > 0:
                f.seek(read_from)
            chunk = f.read().decode('utf-8', errors='ignore')
            lines = [ln for ln in chunk.splitlines() if ln.strip()]
            if not lines:
                return _telemetry_cache['last_row']
            # Ensure we skip header if our window started before it
            # Find last non-header line
            for line in reversed(lines):
                if not line.lower().startswith('timestamp,'):
                    last_line = line
                    break
            else:
                last_line = None

        if last_line is None:
            return _telemetry_cache['last_row']

        # Parse last CSV line against known headers
        headers = ['timestamp','roll','pitch','yaw','latitude','longitude','altitude','velocity','temperature','pressure']
        parts = []
        try:
            # Simple CSV split; our generator/receiver do not include commas in fields
            parts = [p.strip() for p in last_line.split(',')]
            if len(parts) != len(headers):
                # Fallback to DictReader if line malformed
                with open(path, 'r') as fr:
                    reader = csv.DictReader(fr)
                    rows = list(reader)
                    row = rows[-1] if rows else None
            else:
                row = dict(zip(headers, parts))
        except Exception:
            row = None

        _telemetry_cache['last_row'] = row
        _telemetry_cache['last_check_ts'] = now
        _telemetry_cache['last_mtime'] = stat.st_mtime
        _telemetry_cache['last_size'] = stat.st_size
        return row
    except Exception:
        return _telemetry_cache['last_row']


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
# - viz_landing.py: Landing prediction visualization


def _make_scanlines_surface(width, height):
    """Pre-render scanlines into a surface for cheap blits each frame."""
    colors = get_colors()
    scanline_color = (5, 5, 5) if current_theme == 'dark' else (230, 230, 230)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 3):
        pygame.draw.line(surf, scanline_color, (0, y), (width, y), 1)
    return surf


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
    
    # Determine start mode
    mode = 'flight' if skip_preflight else 'preflight'
    preflight_menu = None
    cusf_predictor = None
    flight_start_time = None
    
    # Initialize pre-flight menu if starting in pre-flight
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
                    # Toggle pre-flight menu (create menu inline; predictor reused if available)
                    if mode == 'flight':
                        colors = get_colors()
                        preflight_menu = PreFlightMenu(current_width, current_height, colors, current_theme)
                        cusf_predictor = cusf_predictor or CUSFPredictor()
                        mode = 'preflight'
                    else:
                        # Switch to flight, keep cusf_predictor cached for in-flight error calc
                        mode = 'flight'
                        preflight_menu = None
                        # Reset flight start time when returning from preflight
                        flight_start_time = datetime.now()
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
                        
                        preflight_menu.set_download_status("Downloading map tiles...")
                        pygame.display.flip()
                        
                        # Prefer path-based preloading if CUSF prediction exists
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
                        preflight_menu.set_download_status("✓ Download complete! Ready to start flight.")
                        preflight_menu.set_download_complete()
                    
                    elif action == 'start_flight':
                        # Switch to flight mode and reset everything
                        mode = 'flight'
                        flight_start_time = datetime.now()
                        preflight_menu = None
                        # Clear any cached telemetry data to force fresh read
                        _telemetry_cache['last_row'] = None
                        _telemetry_cache['last_check_ts'] = 0.0
                        _telemetry_cache['last_mtime'] = 0.0
                        _telemetry_cache['last_size'] = 0
                        print(f"Flight started at {flight_start_time} - Interface reset")
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
        
        # Load fonts based on scale (fail-fast)
        font_size = max(12, int(16 * scale))
        font_large_size = max(14, int(20 * scale))
        font = pygame.font.SysFont('consolas', font_size)
        font_large = pygame.font.SysFont('consolas', font_large_size)
        
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
        # Pre-rendered scanlines surface (recreate if size or theme changed)
        if ('_scanlines' not in globals()) or (globals().get('_scan_w') != current_width) or (globals().get('_scan_h') != current_height) or (globals().get('_scan_theme') != current_theme):
            globals()['_scanlines'] = _make_scanlines_surface(current_width, current_height)
            globals()['_scan_w'] = current_width
            globals()['_scan_h'] = current_height
            globals()['_scan_theme'] = current_theme
        screen.blit(globals()['_scanlines'], (0, 0))
        
        # Draw status bar
        status_bar_height = int(40 * scale)
        draw_status_bar(screen, telemetry, font, current_width, current_height, scale)
        
        # Draw minimal banner
        banner_start_y = status_bar_height + int(10 * scale)
        banner_width = font.size(BANNER_TEXT)[0]
        banner_x = max(10, (current_width - banner_width) // 2)
        draw_text(screen, BANNER_TEXT, (banner_x, banner_start_y), font, colors['primary'])
        
        if telemetry:
                # Parse telemetry data (GPS-only display)
                lat = float(telemetry['latitude'])
                lon = float(telemetry['longitude'])
                alt = float(telemetry['altitude']) if 'altitude' in telemetry and telemetry['altitude'] != '' else None
                vel = float(telemetry['velocity']) if 'velocity' in telemetry and telemetry['velocity'] != '' else None
                
                # Calculate grid layout with proper margins
                content_start_y = banner_start_y + int(40 * scale)
                margin = int(20 * scale)
                
                # Calculate available space
                available_width = current_width - (4 * margin)
                available_height = current_height - content_start_y - int(50 * scale)  # Reserve space at bottom
                
                # Calculate column widths (3 columns) - make GPS windows larger
                col_width = max(350, available_width // 3)  # Increased minimum width per column
                
                # Left column: RAW DATA
                left_x = margin
                raw_data = [
                    "GPS TELEMETRY",
                    "══════════════════════════",
                    f"LATITUDE:    {lat:>12.6f}°",
                    f"LONGITUDE:   {lon:>12.6f}°",
                ]
                if alt is not None:
                    raw_data.append(f"ALTITUDE:    {alt:>10.1f} m")
                if vel is not None:
                    raw_data.append(f"SPEED:       {vel:>10.2f} m/s")
                raw_data.extend([
                    "",
                    f"TIMESTAMP:   {telemetry.get('timestamp', 'N/A')}"
                ])
                
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
                # Scale map to fit available space - make GPS windows larger
                max_map_size = min(col_width - int(40*scale), available_height - int(200*scale))
                map_size = max(250, min(max_map_size, int(400 * scale)))  # Increased minimum and maximum sizes
                draw_simple_map(screen, lat, lon, (middle_x, map_y), 
                              (map_size, map_size), font, colors, scale)
                
                # Additional GPS info below map
                info_y = map_y + map_size + int(30 * scale)
                gps_info = []
                if alt is not None:
                    gps_info.append(f"ALT: {alt:.1f} m")
                if vel is not None:
                    gps_info.append(f"SPD: {vel*3.6:.1f} km/h")
                for line in gps_info:
                    draw_text(screen, line, (middle_x, info_y), font, colors['primary'])
                    info_y += line_height

                # Right column: LANDING PREDICTION
                right_x = margin + 2 * (col_width + margin)

                # Ensure right column doesn't overflow
                if right_x + col_width > current_width - margin:
                    right_x = current_width - col_width - margin

                # Calculate prediction using CUSF if available; fallback to simple drift
                prediction_error = None
                alt_val = float(alt) if alt is not None else 0.0
                vel_val = float(vel) if vel is not None else 0.0

                if cusf_predictor and flight_start_time:
                    elapsed_seconds = (datetime.now() - flight_start_time).total_seconds()
                    prediction_error = cusf_predictor.calculate_prediction_error(
                        lat, lon, alt_val, elapsed_seconds
                    )
                    cusf_landing = cusf_predictor.get_landing_location()
                    if cusf_landing:
                        pred_lat, pred_lon = cusf_landing[0], cusf_landing[1]
                    else:
                        pred_lat, pred_lon = predict_landing(lat, lon, alt_val, vel_val)
                else:
                    pred_lat, pred_lon = predict_landing(lat, lon, alt_val, vel_val)

                pred_title_y = content_start_y
                sep_width = min(int(200 * scale), col_width - int(20 * scale))
                draw_section_title(screen, "LANDING PREDICTION", right_x, pred_title_y, font, colors, sep_width, scale)

                pred_map_y = pred_title_y + int(50 * scale)
                # Use the same larger map size for landing prediction
                draw_landing_zone(
                    screen, lat, lon, pred_lat, pred_lon,
                    (right_x, pred_map_y), (map_size, map_size), font, colors, scale,
                    prediction_error=prediction_error
                )

                # Landing info below map
                land_info_y = pred_map_y + map_size + int(30 * scale)
                landing_info = [
                    f"EST. LAT: {pred_lat:.6f}°",
                    f"EST. LON: {pred_lon:.6f}°",
                ]
                if alt is not None and alt_val > 0:
                    descent_time_min = (alt_val / 5.0) / 60
                    landing_info.append(f"TIME:     {descent_time_min:.1f} min")
                for line in landing_info:
                    draw_text(screen, line, (right_x, land_info_y), font, colors['warning'])
                    land_info_y += line_height
                
                # Bottom info bar
                info_text = f"DATA: {CSV_FILE} │ FPS: {FPS} │ [F1] THEME │ [F2] PREFLIGHT │ [ESC] EXIT │ [F11] TOGGLE FULLSCREEN"
                draw_text(screen, info_text, (margin, int(current_height - 30*scale)), font, colors['dim'])
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
    
    
    main(dummy_mode=args.dummy, skip_preflight=args.skip_preflight)
    
    print("\n[SYSTEM] Ground Station Interface Terminated.")
