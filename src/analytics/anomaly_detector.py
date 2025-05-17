import time
import numpy as np
from collections import defaultdict, deque

class AnomalyDetector:
    """Class to detect anomalies in workspace activity"""
    
    def __init__(self, zone_manager):
        """Initialize with reference to zone manager"""
        self.zone_manager = zone_manager
        
        # Define thresholds for anomaly detection
        self.thresholds = {
            "idle_time": 30 * 60,  # 30 minutes
            "zone_capacity": {},   # Will be populated from zone data
            "unauthorized_access": {},  # Will be populated from zone data
            "suspicious_movement": 5,  # Number of zone transitions in short period
            "movement_window": 10 * 60  # 10 minute window for movement tracking
        }
        
        # Set default capacity for each zone type
        self.default_capacities = {
            "desk": 1,
            "meeting_room": 6,
            "break_area": 4,
            "hallway": 10
        }
        
        # Movement history for each person
        self.movement_history = defaultdict(lambda: deque(maxlen=20))
        
        # Time of last update
        self.last_update = time.time()
        
        # Initialize zone capacities from zone data
        self._initialize_zone_thresholds()
    
    def _initialize_zone_thresholds(self):
        """Initialize thresholds based on zone configuration"""
        # Set capacity for each zone based on type
        for zone_id, zone in self.zone_manager.zones.items():
            zone_type = zone["type"]
            # Use default capacity for zone type
            self.thresholds["zone_capacity"][zone_id] = self.default_capacities.get(zone_type, 4)
            
            # Set unauthorized access flags (only desks are person-specific)
            if zone_type == "desk":
                # Extract person ID from desk name if available (assuming format "desk_1", "desk_2", etc.)
                if "_" in zone["name"]:
                    try:
                        person_id = int(zone["name"].split("_")[1])
                        self.thresholds["unauthorized_access"][zone_id] = [person_id]
                    except (ValueError, IndexError):
                        # If parsing fails, no restrictions
                        self.thresholds["unauthorized_access"][zone_id] = []
                else:
                    self.thresholds["unauthorized_access"][zone_id] = []
            else:
                # Other zone types have no restrictions
                self.thresholds["unauthorized_access"][zone_id] = []
    
    def update_movement_history(self, person_id, zone_id, timestamp=None):
        """Update movement history for a person"""
        if timestamp is None:
            timestamp = time.time()
            
        self.movement_history[person_id].append((zone_id, timestamp))
    
    def detect_idle_time(self, person_zone_tracker):
        """Detect people who have been idle for too long"""
        anomalies = []
        current_time = time.time()
        
        for person_id, zone_id in person_zone_tracker.person_zones.items():
            if zone_id is None:
                continue
                
            # Get zone entry time
            entry_time = person_zone_tracker.zone_entry_times.get(person_id, {}).get(zone_id)
            if entry_time is None:
                continue
                
            # Calculate time in current zone
            time_in_zone = current_time - entry_time
            
            # Check if exceeds threshold
            if time_in_zone > self.thresholds["idle_time"]:
                zone_name = self.zone_manager.zones.get(zone_id, {}).get("name", "Unknown")
                anomalies.append({
                    "type": "idle_person",
                    "person_id": person_id,
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "idle_time": time_in_zone,
                    "timestamp": current_time,
                    "severity": "high" if time_in_zone > 2 * self.thresholds["idle_time"] else "medium"
                })
                
        return anomalies
    
    def detect_overcrowded_zones(self, person_zone_tracker):
        """Detect zones that are over capacity"""
        anomalies = []
        current_time = time.time()
        
        # Count people in each zone
        zone_counts = defaultdict(int)
        for person_id, zone_id in person_zone_tracker.person_zones.items():
            if zone_id is not None:
                zone_counts[zone_id] += 1
        
        # Check against thresholds
        for zone_id, count in zone_counts.items():
            if zone_id not in self.zone_manager.zones:
                continue
                
            capacity = self.thresholds["zone_capacity"].get(zone_id)
            if capacity and count > capacity:
                zone_name = self.zone_manager.zones[zone_id]["name"]
                anomalies.append({
                    "type": "overcrowded_zone",
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "current_count": count,
                    "capacity": capacity,
                    "timestamp": current_time,
                    "severity": "high" if count > capacity + 2 else "medium" 
                })
                
        return anomalies
    
    def detect_unauthorized_access(self, person_zone_tracker):
        """Detect unauthorized access to restricted zones"""
        anomalies = []
        current_time = time.time()
        
        for person_id, zone_id in person_zone_tracker.person_zones.items():
            if zone_id is None:
                continue
                
            # Check if zone has access restrictions
            allowed_people = self.thresholds["unauthorized_access"].get(zone_id, [])
            if allowed_people and person_id not in allowed_people:
                zone_name = self.zone_manager.zones.get(zone_id, {}).get("name", "Unknown")
                anomalies.append({
                    "type": "unauthorized_access",
                    "person_id": person_id,
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "timestamp": current_time,
                    "severity": "high"
                })
                
        return anomalies
    
    def detect_suspicious_movement(self):
        """Detect suspicious movement patterns (frequent zone changes)"""
        anomalies = []
        current_time = time.time()
        
        for person_id, movements in self.movement_history.items():
            if len(movements) < 2:
                continue
                
            # Get movements in the recent window
            recent_movements = [(z, t) for z, t in movements 
                               if current_time - t < self.thresholds["movement_window"]]
            
            if len(recent_movements) < 2:
                continue
                
            # Count unique zones visited recently
            unique_zones = set(zone for zone, _ in recent_movements)
            
            # Calculate zone transitions
            transitions = len(recent_movements) - 1
            
            # Check if suspicious
            if transitions >= self.thresholds["suspicious_movement"]:
                anomalies.append({
                    "type": "suspicious_movement",
                    "person_id": person_id,
                    "transitions": transitions,
                    "unique_zones": len(unique_zones),
                    "timestamp": current_time,
                    "severity": "medium" if transitions < 2 * self.thresholds["suspicious_movement"] else "high"
                })
                
        return anomalies
    
    def detect_all_anomalies(self, person_zone_tracker):
        """Detect all types of anomalies"""
        # Update internal state if needed
        time_since_update = time.time() - self.last_update
        if time_since_update > 60:  # Update state if more than a minute has passed
            self._initialize_zone_thresholds()
            self.last_update = time.time()
        
        # Detect each type of anomaly
        idle_anomalies = self.detect_idle_time(person_zone_tracker)
        overcrowded_anomalies = self.detect_overcrowded_zones(person_zone_tracker)
        unauthorized_anomalies = self.detect_unauthorized_access(person_zone_tracker)
        movement_anomalies = self.detect_suspicious_movement()
        
        # Combine all anomalies
        all_anomalies = idle_anomalies + overcrowded_anomalies + unauthorized_anomalies + movement_anomalies
        
        return all_anomalies