#!/usr/bin/env python3
"""
3D Cube Visualization Module
Displays payload orientation with rotating 3D cube
"""

import pygame
import math


def draw_3d_cube(surface, roll, pitch, yaw, pos, size, colors, current_theme, scale=1.0):
    """Draw a 3D wireframe cube representing payload orientation"""
    x, y = pos
    width, height = size
    
    # Draw border
    pygame.draw.rect(surface, colors['accent'], (x, y, width, height), max(1, int(2*scale)))
    
    # Cube center
    center_x = x + width // 2
    center_y = y + height // 2
    
    # Make cube 50% smaller as requested
    cube_size = int(min(width, height) // 6)  # Changed from // 3 to // 6 (50% smaller)
    
    # Convert angles to radians
    roll_rad = math.radians(roll)
    pitch_rad = math.radians(pitch)
    yaw_rad = math.radians(yaw)
    
    # Define cube vertices (8 corners of a cube)
    vertices = [
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],  # Back face
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]       # Front face
    ]
    
    # Scale vertices
    vertices = [[v[0] * cube_size, v[1] * cube_size, v[2] * cube_size] for v in vertices]
    
    # Rotation matrices
    def rotate_x(point, angle):
        y = point[1] * math.cos(angle) - point[2] * math.sin(angle)
        z = point[1] * math.sin(angle) + point[2] * math.cos(angle)
        return [point[0], y, z]
    
    def rotate_y(point, angle):
        x = point[0] * math.cos(angle) + point[2] * math.sin(angle)
        z = -point[0] * math.sin(angle) + point[2] * math.cos(angle)
        return [x, point[1], z]
    
    def rotate_z(point, angle):
        x = point[0] * math.cos(angle) - point[1] * math.sin(angle)
        y = point[0] * math.sin(angle) + point[1] * math.cos(angle)
        return [x, y, point[2]]
    
    # Apply rotations to all vertices (roll -> pitch -> yaw)
    rotated = []
    for vertex in vertices:
        v = rotate_x(vertex, roll_rad)
        v = rotate_y(v, pitch_rad)
        v = rotate_z(v, yaw_rad)
        rotated.append(v)
    
    # Project 3D to 2D (simple perspective projection)
    projected = []
    distance = 4 * cube_size  # Camera distance
    for vertex in rotated:
        factor = distance / (distance + vertex[2])
        px = int(center_x + vertex[0] * factor)
        py = int(center_y - vertex[1] * factor)  # Negative because y increases downward
        projected.append((px, py))
    
    # Define edges (which vertices connect to which)
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Back face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Front face
        (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting edges
    ]
    
    # Draw edges
    line_thickness = max(1, int(2 * scale))
    for edge in edges:
        start = projected[edge[0]]
        end = projected[edge[1]]
        pygame.draw.line(surface, colors['primary'], start, end, line_thickness)
    
    # Draw vertices as small circles
    vertex_radius = max(2, int(3 * scale))
    for point in projected:
        pygame.draw.circle(surface, colors['accent'], point, vertex_radius)
    
    # Draw orientation axes
    axis_length = cube_size * 1.5
    
    # X-axis (red) - right
    x_axis = rotate_x([axis_length, 0, 0], roll_rad)
    x_axis = rotate_y(x_axis, pitch_rad)
    x_axis = rotate_z(x_axis, yaw_rad)
    factor = distance / (distance + x_axis[2])
    x_end = (int(center_x + x_axis[0] * factor), int(center_y - x_axis[1] * factor))
    pygame.draw.line(surface, (200, 100, 100) if current_theme == 'dark' else (150, 50, 50), 
                    (center_x, center_y), x_end, max(2, int(3 * scale)))
    
    # Y-axis (green) - up
    y_axis = rotate_x([0, axis_length, 0], roll_rad)
    y_axis = rotate_y(y_axis, pitch_rad)
    y_axis = rotate_z(y_axis, yaw_rad)
    factor = distance / (distance + y_axis[2])
    y_end = (int(center_x + y_axis[0] * factor), int(center_y - y_axis[1] * factor))
    pygame.draw.line(surface, (100, 200, 100) if current_theme == 'dark' else (50, 150, 50), 
                    (center_x, center_y), y_end, max(2, int(3 * scale)))
    
    # Z-axis (blue) - forward
    z_axis = rotate_x([0, 0, axis_length], roll_rad)
    z_axis = rotate_y(z_axis, pitch_rad)
    z_axis = rotate_z(z_axis, yaw_rad)
    factor = distance / (distance + z_axis[2])
    z_end = (int(center_x + z_axis[0] * factor), int(center_y - z_axis[1] * factor))
    pygame.draw.line(surface, (100, 100, 200) if current_theme == 'dark' else (50, 50, 150), 
                    (center_x, center_y), z_end, max(2, int(3 * scale)))

