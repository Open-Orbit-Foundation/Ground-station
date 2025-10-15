#!/usr/bin/env python3
"""
OpenStreetMap Tile Cache Manager
Downloads and caches map tiles for offline use
"""

import os
import math
import urllib.request
import urllib.error
import time


class MapTileCache:
    """Manages downloading and caching of OpenStreetMap tiles"""
    
    def __init__(self, cache_dir='map_cache', tile_server='https://tile.openstreetmap.org'):
        self.cache_dir = cache_dir
        self.tile_server = tile_server
        self.tile_size = 256
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
    
    def lat_lon_to_tile(self, lat, lon, zoom):
        """Convert lat/lon to tile coordinates"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y
    
    def get_tile_path(self, zoom, x, y):
        """Get local file path for a tile"""
        tile_dir = os.path.join(self.cache_dir, str(zoom), str(x))
        os.makedirs(tile_dir, exist_ok=True)
        return os.path.join(tile_dir, f"{y}.png")
    
    def download_tile(self, zoom, x, y):
        """Download a single tile from OSM (no retries; fail on error)."""
        url = f"{self.tile_server}/{zoom}/{x}/{y}.png"
        tile_path = self.get_tile_path(zoom, x, y)
        
        # Check if already cached
        if os.path.exists(tile_path):
            return tile_path
        
        # Polite throttling
        time.sleep(0.25)
        # Download with user agent (required by OSM)
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'GroundStationControl/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(tile_path, 'wb') as f:
                f.write(response.read())
        print(f"Downloaded tile: {zoom}/{x}/{y}")
        return tile_path
    
    
    
    def preload_area(self, center_lat, center_lon, zoom, radius_tiles=2):
        """Pre-download tiles around a center point"""
        center_x, center_y = self.lat_lon_to_tile(center_lat, center_lon, zoom)
        
        tiles_downloaded = 0
        tiles_cached = 0
        
        print(f"Preloading tiles around ({center_lat:.4f}, {center_lon:.4f}) at zoom {zoom}")
        print(f"Radius: {radius_tiles} tiles")
        
        for x in range(center_x - radius_tiles, center_x + radius_tiles + 1):
            for y in range(center_y - radius_tiles, center_y + radius_tiles + 1):
                tile_path = self.get_tile_path(zoom, x, y)
                
                if os.path.exists(tile_path):
                    tiles_cached += 1
                else:
                    if self.download_tile(zoom, x, y):
                        tiles_downloaded += 1
        
        total = (radius_tiles * 2 + 1) ** 2
        print(f"Complete! Downloaded: {tiles_downloaded}, Cached: {tiles_cached}, Total: {total}")
        
        return tiles_downloaded, tiles_cached


class MapRenderer:
    """Renders cached map tiles in pygame"""
    
    def __init__(self, cache_dir='map_cache'):
        self.cache = MapTileCache(cache_dir)
        self.tile_size = 256
        self._image_cache = {}
        self._image_cache_max = 512  # simple bound to avoid runaway memory
    
    def render_map(self, surface, center_lat, center_lon, zoom, display_rect, colors):
        """Render map tiles centered on lat/lon"""
        # Lazy import to avoid requiring pygame for CLI preloaders
        import pygame
        x, y, width, height = display_rect
        
        # Calculate which tiles we need
        center_tile_x, center_tile_y = self.cache.lat_lon_to_tile(center_lat, center_lon, zoom)
        
        # How many tiles to display
        tiles_x = math.ceil(width / self.tile_size) + 1
        tiles_y = math.ceil(height / self.tile_size) + 1
        
        # Starting tile
        start_tile_x = center_tile_x - tiles_x // 2
        start_tile_y = center_tile_y - tiles_y // 2
        
        # Draw border
        pygame.draw.rect(surface, colors['accent'], (x, y, width, height), 2)
        
        # Render tiles
        for tile_x_offset in range(tiles_x):
            for tile_y_offset in range(tiles_y):
                tile_x = start_tile_x + tile_x_offset
                tile_y = start_tile_y + tile_y_offset
                
                tile_path = self.cache.get_tile_path(zoom, tile_x, tile_y)
                
                if os.path.exists(tile_path):
                    # Load and display tile (with simple in-memory cache)
                    tile_img = self._get_tile_image(tile_path)
                    
                    # Calculate screen position
                    screen_x = x + tile_x_offset * self.tile_size
                    screen_y = y + tile_y_offset * self.tile_size
                    
                    # Clip to display area
                    if screen_x < x + width and screen_y < y + height:
                        surface.blit(tile_img, (screen_x, screen_y))
        
        # Draw center marker (current position)
        center_x = x + width // 2
        center_y = y + height // 2
        marker_size = 10
        
        # Cross marker
        pygame.draw.line(surface, colors['primary'], 
                        (center_x - marker_size, center_y), 
                        (center_x + marker_size, center_y), 3)
        pygame.draw.line(surface, colors['primary'], 
                        (center_x, center_y - marker_size), 
                        (center_x, center_y + marker_size), 3)
        pygame.draw.circle(surface, colors['primary'], (center_x, center_y), 5, 2)

    def _get_tile_image(self, path):
        """Get tile image surface from cache; load if missing or stale."""
        # Lazy import inside method
        import pygame
        mtime = os.path.getmtime(path)

        cached = self._image_cache.get(path)
        if cached and cached.get('mtime') == mtime:
            return cached['surf']

        # Load fresh
        surf = pygame.image.load(path)
        # Update cache (simple dict with bound size)
        if len(self._image_cache) >= self._image_cache_max:
            # Drop an arbitrary item (simple pop of first key)
            self._image_cache.pop(next(iter(self._image_cache)))
        self._image_cache[path] = {'surf': surf, 'mtime': mtime}
        return surf


def tiles_exist_for_area(center_lat, center_lon, zoom, display_rect, cache_dir='map_cache'):
    """Return True if all tiles required to render display_rect are cached locally."""
    x, y, width, height = display_rect
    cache = MapTileCache(cache_dir)
    tile_size = 256
    center_tx, center_ty = cache.lat_lon_to_tile(center_lat, center_lon, zoom)
    tiles_x = math.ceil(width / tile_size) + 1
    tiles_y = math.ceil(height / tile_size) + 1
    start_tx = center_tx - tiles_x // 2
    start_ty = center_ty - tiles_y // 2
    for dx in range(tiles_x):
        for dy in range(tiles_y):
            tx = start_tx + dx
            ty = start_ty + dy
            tile_path = cache.get_tile_path(zoom, tx, ty)
            if not os.path.exists(tile_path):
                return False
    return True


def preload_flight_area(center_lat, center_lon, max_radius_km=50, zoom_levels=[10, 11, 12]):
    """
    Preload map tiles for an entire flight area
    
    Args:
        center_lat: Center latitude of flight area
        center_lon: Center longitude of flight area
        max_radius_km: Maximum radius in kilometers
        zoom_levels: List of zoom levels to download
    """
    cache = MapTileCache()
    
    print("=" * 60)
    print("MAP TILE PRELOADER")
    print("=" * 60)
    print(f"Center: {center_lat:.4f}, {center_lon:.4f}")
    print(f"Radius: {max_radius_km} km")
    print(f"Zoom levels: {zoom_levels}")
    print()
    
    for zoom in zoom_levels:
        # Calculate tile radius based on km radius
        # At zoom level, 1 tile ≈ (40075 km / (2^zoom * 256 pixels)) * 256 pixels
        km_per_tile = 40075 * math.cos(math.radians(center_lat)) / (2 ** zoom)
        tile_radius = math.ceil(max_radius_km / km_per_tile)
        
        print(f"\nZoom level {zoom} (tile radius: {tile_radius}):")
        cache.preload_area(center_lat, center_lon, zoom, tile_radius)
    
    print("\n" + "=" * 60)
    print("Preloading complete!")
    print("=" * 60)


def preload_tiles_along_path(path_points, buffer_km=25, zoom_levels=[10, 11, 12], cache_dir='map_cache'):
    """
    Preload map tiles along a flight path with a buffer distance.
    
    Args:
        path_points: Iterable of (lat, lon) tuples along the path
        buffer_km: Buffer distance from the path to cover (in km)
        zoom_levels: List of zoom levels to download
        cache_dir: Tile cache directory
    """
    cache = MapTileCache(cache_dir)
    print("=" * 60)
    print("MAP TILE PRELOADER (PATH-BASED)")
    print("=" * 60)
    print(f"Points: {len(path_points)} | Buffer: {buffer_km} km | Zooms: {zoom_levels}")
    print()

    # Collect unique tiles to download
    tiles_to_download = set()

    for zoom in zoom_levels:
        for (lat, lon) in path_points:
            # Compute tile at this point
            center_x, center_y = cache.lat_lon_to_tile(lat, lon, zoom)
            # Approximate km per tile (east-west) at latitude
            km_per_tile = 40075 * math.cos(math.radians(lat)) / (2 ** zoom)
            tile_radius = max(0, int(math.ceil(buffer_km / max(km_per_tile, 1e-6))))

            # Gather all tiles in square around center within radius
            max_index = (2 ** zoom) - 1
            for dx in range(-tile_radius, tile_radius + 1):
                for dy in range(-tile_radius, tile_radius + 1):
                    tx = min(max(center_x + dx, 0), max_index)
                    ty = min(max(center_y + dy, 0), max_index)
                    tiles_to_download.add((zoom, tx, ty))

    # Download unique tiles
    downloaded = 0
    cached = 0
    total = len(tiles_to_download)
    print(f"Preparing to fetch {total} unique tiles...")
    for (zoom, x, y) in sorted(tiles_to_download):
        tile_path = cache.get_tile_path(zoom, x, y)
        if os.path.exists(tile_path):
            cached += 1
        else:
            if cache.download_tile(zoom, x, y):
                downloaded += 1

    print("\n" + "=" * 60)
    print(f"Path-based preloading complete: Downloaded: {downloaded}, Cached: {cached}, Total: {total}")
    print("=" * 60)


if __name__ == "__main__":
    # Example: Preload tiles for Los Angeles area
    print("Map Tile Cache - Preload Utility")
    print()
    
    # Example coordinates (adjust for your launch site)
    launch_lat = 34.052235
    launch_lon = -118.243683
    
    print(f"Launch site: {launch_lat}, {launch_lon}")
    print()
    
    response = input("Preload tiles for this area? (y/n): ")
    
    if response.lower() == 'y':
        preload_flight_area(launch_lat, launch_lon, max_radius_km=50, zoom_levels=[10, 11, 12])
    else:
        print("Aborted.")

