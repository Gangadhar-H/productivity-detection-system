# src/zone_tracking/zone_manager.py
import json
import os
import cv2
import numpy as np

class ZoneManager:
    """Class to define and manage workspace zones"""
    
    def __init__(self, zones_file=None):
        """Initialize with optional zones file"""
        self.zones = {}  # Format: {zone_id: {"name": name, "type": type, "points": [points]}}
        self.zone_types = ["desk", "meeting_room", "break_area", "hallway"]
        
        if zones_file and os.path.exists(zones_file):
            self.load_zones(zones_file)
            
    def create_zone(self, zone_id, name, zone_type, points):
        """Create a new zone with specified parameters"""
        if zone_type not in self.zone_types:
            raise ValueError(f"Zone type must be one of: {self.zone_types}")
            
        self.zones[zone_id] = {
            "name": name,
            "type": zone_type,
            "points": points
        }
        
    def delete_zone(self, zone_id):
        """Delete a zone by ID"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            
    def save_zones(self, filename):
        """Save zones to a file"""
        with open(filename, 'w') as f:
            json.dump(self.zones, f)
            
    def load_zones(self, filename):
        """Load zones from a file"""
        with open(filename, 'r') as f:
            self.zones = json.load(f)
            
    def point_in_zone(self, point, zone_id):
        """Check if a point is inside a specific zone"""
        if zone_id not in self.zones:
            return False
            
        zone = self.zones[zone_id]
        points = np.array(zone["points"], np.int32)
        points = points.reshape((-1, 1, 2))
        
        return cv2.pointPolygonTest(points, point, False) >= 0
        
    def get_zone_for_point(self, point):
        """Get the zone containing a point"""
        for zone_id, zone in self.zones.items():
            if self.point_in_zone(point, zone_id):
                return zone_id, zone
                
        return None, None
        
    def is_productive_zone(self, zone_id):
        """Check if a zone is considered productive"""
        if zone_id not in self.zones:
            return False
            
        # Desks and meeting rooms are productive
        productive_types = ["desk", "meeting_room"]
        return self.zones[zone_id]["type"] in productive_types
        
    def draw_zones(self, frame):
        """Draw zones on a frame"""
        frame_copy = frame.copy()
        
        # Define colors for different zone types
        colors = {
            "desk": (0, 255, 0),       # Green
            "meeting_room": (0, 0, 255),  # Blue
            "break_area": (0, 255, 255),  # Yellow
            "hallway": (128, 128, 128)   # Gray
        }
        
        # Draw each zone
        for zone_id, zone in self.zones.items():
            color = colors.get(zone["type"], (255, 255, 255))
            points = np.array(zone["points"], np.int32)
            points = points.reshape((-1, 1, 2))
            
            # Draw filled polygon with transparency
            overlay = frame_copy.copy()
            cv2.fillPoly(overlay, [points], color)
            alpha = 0.4  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame_copy, 1 - alpha, 0, frame_copy)
            
            # Draw outline
            cv2.polylines(frame_copy, [points], True, color, 2)
            
            # Add zone name
            centroid = np.mean(points, axis=0).astype(int)
            cv2.putText(frame_copy, zone["name"], 
                      (centroid[0][0], centroid[0][1]), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        return frame_copy