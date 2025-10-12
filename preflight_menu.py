#!/usr/bin/env python3
"""
Pre-flight Configuration Menu
UI for configuring launch parameters and downloading offline data
"""

import pygame
from datetime import datetime, timedelta


class PreFlightMenu:
    """Pre-flight configuration menu"""
    
    def __init__(self, screen_width, screen_height, colors, theme):
        self.width = screen_width
        self.height = screen_height
        self.colors = colors
        self.theme = theme
        
        # Configuration state
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
        
        try:
            # Parse based on field type
            if self.active_field in ['launch_latitude', 'launch_longitude']:
                self.config[self.active_field] = float(self.input_buffer)
            elif self.active_field in ['launch_altitude', 'burst_altitude']:
                self.config[self.active_field] = int(self.input_buffer)
            elif self.active_field in ['ascent_rate', 'descent_rate']:
                self.config[self.active_field] = float(self.input_buffer)
        except ValueError:
            pass  # Ignore invalid input
    
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

