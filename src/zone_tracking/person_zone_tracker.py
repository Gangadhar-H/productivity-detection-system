# src/zone_tracking/person_zone_tracker.py
import time
import json
from collections import defaultdict

class PersonZoneTracker:
    """Class to track people in zones and calculate time spent"""
    
    def __init__(self, zone_manager):
        """Initialize with ZoneManager instance"""
        self.zone_manager = zone_manager
        self.person_zones = {}  # {person_id: current_zone_id}
        self.zone_entry_times = {}  # {person_id: {zone_id: entry_timestamp}}
        self.time_in_zones = defaultdict(lambda: defaultdict(float))  # {person_id: {zone_id: time_spent}}
        self.daily_productive_time = defaultdict(float)  # {person_id: productive_time}
        self.last_update_time = None
        
    def update(self, detections):
        """Update zone tracking with new detections"""
        current_time = time.time()
        
        if self.last_update_time is None:
            self.last_update_time = current_time
            
        time_diff = current_time - self.last_update_time
        
        # Process each detection
        for detection in detections:
            person_id, x, y, _, _, _ = detection
            
            # Skip untracked persons
            if person_id < 0:
                continue
                
            # Find zone for this person
            current_zone_id, zone = self.zone_manager.get_zone_for_point((x, y))
            
            # If person already being tracked
            if person_id in self.person_zones:
                prev_zone_id = self.person_zones[person_id]
                
                # If person changed zones
                if current_zone_id != prev_zone_id:
                    # Update time spent in previous zone
                    if prev_zone_id is not None:
                        entry_time = self.zone_entry_times.get(person_id, {}).get(prev_zone_id)
                        if entry_time:
                            time_spent = current_time - entry_time
                            self.time_in_zones[person_id][prev_zone_id] += time_spent
                            
                            # Update productive time if applicable
                            if self.zone_manager.is_productive_zone(prev_zone_id):
                                self.daily_productive_time[person_id] += time_spent
                    
                    # Record entry time for new zone
                    if current_zone_id is not None:
                        if person_id not in self.zone_entry_times:
                            self.zone_entry_times[person_id] = {}
                        self.zone_entry_times[person_id][current_zone_id] = current_time
                
                # If person stayed in same zone, update cumulative time
                elif current_zone_id is not None:
                    # Add the time diff to productive time if applicable
                    if self.zone_manager.is_productive_zone(current_zone_id):
                        self.daily_productive_time[person_id] += time_diff
            
            # If new person
            else:
                if current_zone_id is not None:
                    if person_id not in self.zone_entry_times:
                        self.zone_entry_times[person_id] = {}
                    self.zone_entry_times[person_id][current_zone_id] = current_time
            
            # Update current zone
            self.person_zones[person_id] = current_zone_id
        
        self.last_update_time = current_time
        
    def get_person_zone(self, person_id):
        """Get the current zone for a person"""
        return self.person_zones.get(person_id)
        
    def get_zone_occupancy(self):
        """Get number of people in each zone"""
        occupancy = defaultdict(int)
        
        for person_id, zone_id in self.person_zones.items():
            if zone_id is not None:
                occupancy[zone_id] += 1
                
        return occupancy
        
    def get_time_in_zone(self, person_id, zone_id):
        """Get time spent by a person in a specific zone"""
        return self.time_in_zones.get(person_id, {}).get(zone_id, 0)
        
    def get_productive_time(self, person_id):
        """Get total productive time for a person"""
        return self.daily_productive_time.get(person_id, 0)
        
    def save_data(self, filename):
        """Save tracking data to file"""
        data = {
            "time_in_zones": {
                str(person_id): {str(zone_id): time for zone_id, time in zones.items()}
                for person_id, zones in self.time_in_zones.items()
            },
            "daily_productive_time": {str(person_id): time for person_id, time in self.daily_productive_time.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)