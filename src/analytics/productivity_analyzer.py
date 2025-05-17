import pandas as pd
import numpy as np
from collections import defaultdict
import json
import os
import datetime
import time

class ProductivityAnalyzer:
    """Class to analyze productivity data from tracking information"""
    
    def __init__(self, zone_manager):
        """Initialize with zone manager for zone information"""
        self.zone_manager = zone_manager
        self.daily_stats = {}  # Store daily statistics
        self.hourly_stats = {}  # Store hourly statistics
        self.zone_utilization = defaultdict(float)  # Total time spent in each zone
        
    def load_tracking_data(self, tracking_file):
        """Load tracking data from a JSON file"""
        if not os.path.exists(tracking_file):
            return False
            
        try:
            with open(tracking_file, 'r') as f:
                data = json.load(f)
                
            return data
        except Exception as e:
            print(f"Error loading tracking data: {e}")
            return False
    
    def process_tracking_data(self, data):
        """Process tracking data to calculate productivity metrics"""
        time_in_zones = data.get('time_in_zones', {})
        productive_time = data.get('daily_productive_time', {})
        
        # Calculate zone utilization
        for person_id, zones in time_in_zones.items():
            for zone_id, time_spent in zones.items():
                self.zone_utilization[zone_id] += time_spent
        
        # Calculate daily stats
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")
        if date_today not in self.daily_stats:
            self.daily_stats[date_today] = {
                'total_productive_time': 0,
                'total_break_time': 0,
                'avg_productive_time': 0,
                'people_count': 0
            }
            
        # Update daily stats
        total_productive = sum(float(time) for time in productive_time.values())
        people_count = len(productive_time)
        
        if people_count > 0:
            self.daily_stats[date_today]['total_productive_time'] = total_productive
            self.daily_stats[date_today]['avg_productive_time'] = total_productive / people_count
            self.daily_stats[date_today]['people_count'] = people_count
            
            # Calculate break time (simplified)
            total_break_time = 0
            for person_id, zones in time_in_zones.items():
                for zone_id, time_spent in zones.items():
                    if self.zone_manager.zones.get(zone_id, {}).get('type') == 'break_area':
                        total_break_time += time_spent
                        
            self.daily_stats[date_today]['total_break_time'] = total_break_time
    
    def calculate_productivity_score(self, productive_time, break_time, expected_hours=8):
        """Calculate a productivity score based on time spent"""
        expected_seconds = expected_hours * 3600
        
        if expected_seconds == 0:
            return 0
            
        # Simple calculation: productive time / expected time
        # Adjusted slightly for break time (allowing for reasonable breaks)
        reasonable_break = min(break_time, 0.15 * expected_seconds)  # 15% of day for breaks is reasonable
        excessive_break = max(0, break_time - reasonable_break)
        
        # Score calculation (0-100)
        score = (productive_time - excessive_break) / expected_seconds * 100
        
        # Clamp score between 0 and 100
        return max(0, min(100, score))
    
    def detect_anomalies(self, tracking_data, thresholds=None):
        """Detect anomalies in the tracking data"""
        if thresholds is None:
            thresholds = {
                'idle_time': 30 * 60,  # 30 minutes of idle time
                'unauthorized_zone': True,  # Flag unauthorized zone access
                'meeting_capacity': 1.0  # Meeting room at 100% capacity
            }
            
        anomalies = []
        
        # Process each person's data
        time_in_zones = tracking_data.get('time_in_zones', {})
        current_time = time.time()
        
        for person_id, zones in time_in_zones.items():
            # Check for idle time
            if not zones:  # No zones recorded
                anomalies.append({
                    'type': 'idle_time',
                    'person_id': person_id,
                    'details': 'No activity detected'
                })
                continue
                
            # Check for unauthorized zone access
            for zone_id in zones.keys():
                if zone_id not in self.zone_manager.zones:
                    anomalies.append({
                        'type': 'unauthorized_zone',
                        'person_id': person_id,
                        'zone_id': zone_id,
                        'details': f'Access to undefined zone {zone_id}'
                    })
        
        # Check meeting room capacity
        for zone_id, zone in self.zone_manager.zones.items():
            if zone['type'] == 'meeting_room':
                # Count people in this meeting room
                count = sum(1 for person_zones in time_in_zones.values() 
                           if zone_id in person_zones)
                
                # Simple capacity check (assuming capacity of 4 people per meeting room)
                capacity = 4  # This could be defined in zone properties
                if count > capacity:
                    anomalies.append({
                        'type': 'meeting_capacity',
                        'zone_id': zone_id,
                        'zone_name': zone['name'],
                        'count': count,
                        'capacity': capacity,
                        'details': f'Meeting room at {count/capacity*100:.0f}% capacity'
                    })
                    
        return anomalies
    
    def analyze_zone_transitions(self, tracking_data, interval=3600):
        """Analyze zone transitions to identify traffic patterns"""
        # This would require time-series data, which we don't have in the current implementation
        # For now, we'll simulate it with a placeholder
        return {
            'high_traffic_zones': self._get_most_utilized_zones(3),
            'low_traffic_zones': self._get_least_utilized_zones(3),
            'transition_matrix': self._generate_dummy_transition_matrix()
        }
    
    def _get_most_utilized_zones(self, count=3):
        """Get the most utilized zones"""
        sorted_zones = sorted(self.zone_utilization.items(), 
                              key=lambda x: x[1], reverse=True)
        
        result = []
        for zone_id, time_spent in sorted_zones[:count]:
            if zone_id in self.zone_manager.zones:
                result.append({
                    'zone_id': zone_id,
                    'zone_name': self.zone_manager.zones[zone_id]['name'],
                    'time_spent': time_spent
                })
                
        return result
    
    def _get_least_utilized_zones(self, count=3):
        """Get the least utilized zones"""
        sorted_zones = sorted(self.zone_utilization.items(), 
                              key=lambda x: x[1])
        
        result = []
        for zone_id, time_spent in sorted_zones[:count]:
            if zone_id in self.zone_manager.zones:
                result.append({
                    'zone_id': zone_id,
                    'zone_name': self.zone_manager.zones[zone_id]['name'],
                    'time_spent': time_spent
                })
                
        return result
    
    def _generate_dummy_transition_matrix(self):
        """Generate a dummy transition matrix for visualization"""
        # This would be calculated from actual data in a real implementation
        zones = list(self.zone_manager.zones.keys())
        matrix = {}
        
        for from_zone in zones:
            matrix[from_zone] = {}
            total_transitions = 0
            
            for to_zone in zones:
                if from_zone != to_zone:
                    # Generate random transition count
                    transitions = np.random.randint(0, 10)
                    matrix[from_zone][to_zone] = transitions
                    total_transitions += transitions
            
            # Normalize if there were any transitions
            if total_transitions > 0:
                for to_zone in zones:
                    if from_zone != to_zone:
                        matrix[from_zone][to_zone] /= total_transitions
        
        return matrix
    
    def generate_report(self, output_file=None):
        """Generate a productivity report"""
        report = {
            'daily_stats': self.daily_stats,
            'zone_utilization': dict(self.zone_utilization),
            'top_zones': self._get_most_utilized_zones(5),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
                
        return report