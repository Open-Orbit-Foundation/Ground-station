#!/usr/bin/env python3
"""
GPS Map Visualization Module
Displays current position on a grid map or OSM tiles
"""

import pygame


# Try to import map tiles, fall back to simple grid if not available
try:
    from map_tiles import MapRenderer
    MAP_TILES_AVAILABLE = True
except ImportError:
    MAP_TILES_AVAILABLE = False


def draw_simple_map(surface, lat, lon, pos, size, font, colors, scale=1.0, use_tiles=True, zoom=11):
    """
    Draw map with current position marker
    
    Args:
        use_tiles: If True and tiles are available, use OSM tiles. Otherwise use grid.
        zoom: Zoom level for map tiles (10-15 recommended)
    """
    x, y = pos
    width, height = size
    
    # Try to use map tiles if available and enabled
    if use_tiles and MAP_TILES_AVAILABLE:
        try:
            renderer = MapRenderer()
            renderer.render_map(surface, lat, lon, zoom, (x, y, width, height), colors)
            
            # Draw coordinates below map
            coord_y = y + height + int(10 * scale)
            coord_text = f"{lat:.6f}°, {lon:.6f}°"
            text_surface = font.render(coord_text, True, colors['accent'])
            surface.blit(text_surface, (x + int(10*scale), coord_y))
            return
        except Exception as e:
            print(f"Error rendering tiles: {e}, falling back to grid")
    
    # Fall back to simple grid visualization
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

