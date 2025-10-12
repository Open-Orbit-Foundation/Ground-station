#!/usr/bin/env python3
"""
Landing Prediction Visualization Module
Displays predicted landing location with trajectory
"""

import pygame
import math


def draw_landing_zone(surface, current_lat, current_lon, pred_lat, pred_lon, pos, size, font, colors, scale=1.0, prediction_error=None):
    """
    Draw landing prediction visualization
    
    Args:
        prediction_error: Dictionary with error metrics (from CUSF predictor)
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
    
    # Scale factor for visualization (arbitrary - makes it visible)
    vis_scale = 5000
    offset_x = int(lon_diff * vis_scale)
    offset_y = int(-lat_diff * vis_scale)  # Negative because y increases downward
    
    # Clamp to box
    pred_x = max(x + 10, min(x + width - 10, center_x + offset_x))
    pred_y = max(y + 10, min(y + height - 10, center_y + offset_y))
    
    # Draw trajectory line
    pygame.draw.line(surface, colors['warning'], 
                    (center_x, center_y), (pred_x, pred_y), 
                    max(1, int(2*scale)))
    
    # Draw landing marker
    marker_size = int(8 * scale)
    # X marker
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
        
        # Horizontal error
        horiz_error = prediction_error['horizontal_error_km']
        error_color = colors['warning'] if horiz_error < 5 else colors['alert']
        
        error_text = f"ERROR: {horiz_error:.2f} km"
        error_surf = font.render(error_text, True, error_color)
        surface.blit(error_surf, (x + int(10*scale), error_y))
        
        # Altitude error
        alt_error = prediction_error['altitude_error_m']
        alt_text = f"ALT Δ: {alt_error:+.0f} m"
        alt_surf = font.render(alt_text, True, colors['dim'])
        surface.blit(alt_surf, (x + int(10*scale), error_y + int(20*scale)))

