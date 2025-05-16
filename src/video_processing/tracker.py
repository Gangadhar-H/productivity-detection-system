# src/video_processing/tracker.py
import numpy as np
from scipy.optimize import linear_sum_assignment

class SimpleTracker:
    """Simple tracker using IoU matching"""
    
    def __init__(self, max_disappeared=30, min_iou=0.3):
        """Initialize with parameters"""
        self.next_object_id = 0
        self.objects = {}  # Dictionary of tracked objects {id: [x, y, w, h]}
        self.disappeared = {}  # Number of frames object has disappeared
        self.max_disappeared = max_disappeared
        self.min_iou = min_iou
        
    def register(self, centroid):
        """Register a new object with a new ID"""
        self.objects[self.next_object_id] = centroid
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
        
    def deregister(self, object_id):
        """Deregister an object that is no longer tracked"""
        del self.objects[object_id]
        del self.disappeared[object_id]
        
    def calculate_iou(self, boxA, boxB):
        """Calculate IoU between two boxes"""
        # Extract coordinates
        xA, yA, wA, hA = boxA
        xB, yB, wB, hB = boxB
        
        # Convert to corner format
        x1A, y1A = xA - wA/2, yA - hA/2
        x2A, y2A = xA + wA/2, yA + hA/2
        x1B, y1B = xB - wB/2, yB - hB/2
        x2B, y2B = xB + wB/2, yB + hB/2
        
        # Calculate intersection
        xA_i = max(x1A, x1B)
        yA_i = max(y1A, y1B)
        xB_i = min(x2A, x2B)
        yB_i = min(y2A, y2B)
        
        # Calculate intersection area
        inter_area = max(0, xB_i - xA_i) * max(0, yB_i - yA_i)
        
        # Calculate union area
        boxA_area = (x2A - x1A) * (y2A - y1A)
        boxB_area = (x2B - x1B) * (y2B - y1B)
        union_area = boxA_area + boxB_area - inter_area
        
        # Calculate IoU
        iou = inter_area / union_area if union_area > 0 else 0
        
        return iou
        
    def update(self, detections):
        """Update tracker with new detections"""
        # If no detections, mark all objects as disappeared
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects
                    
        # If no objects are being tracked yet, register all detections
        if len(self.objects) == 0:
            for detection in detections:
                _, x, y, w, h, _ = detection
                self.register([x, y, w, h])
        else:
            # Get existing object IDs and centroids
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())
            
            # Calculate IoU between each detection and tracked object
            iou_matrix = np.zeros((len(object_centroids), len(detections)))
            for i, obj in enumerate(object_centroids):
                for j, det in enumerate(detections):
                    _, x, y, w, h, _ = det
                    iou_matrix[i, j] = self.calculate_iou(obj, [x, y, w, h])
            
            # Solve assignment problem using Hungarian algorithm
            row_idx, col_idx = linear_sum_assignment(-iou_matrix)  # Negative because we want max IoU
            
            # Keep track of matched objects and detections
            used_objects = set()
            used_detections = set()
            
            # Update matched objects
            for row, col in zip(row_idx, col_idx):
                # Only match if IoU is above threshold
                if iou_matrix[row, col] >= self.min_iou:
                    object_id = object_ids[row]
                    _, x, y, w, h, _ = detections[col]
                    self.objects[object_id] = [x, y, w, h]
                    self.disappeared[object_id] = 0
                    used_objects.add(object_id)
                    used_detections.add(col)
            
            # Check for disappeared objects
            for object_id in object_ids:
                if object_id not in used_objects:
                    self.disappeared[object_id] += 1
                    if self.disappeared[object_id] > self.max_disappeared:
                        self.deregister(object_id)
            
            # Register new detections
            for i, detection in enumerate(detections):
                if i not in used_detections:
                    _, x, y, w, h, _ = detection
                    self.register([x, y, w, h])
        
        # Update detection IDs
        tracked_detections = []
        for i, detection in enumerate(detections):
            _, x, y, w, h, conf = detection
            
            # Find matching object
            matched_id = None
            for object_id, obj in self.objects.items():
                obj_x, obj_y, obj_w, obj_h = obj
                if abs(x - obj_x) < 10 and abs(y - obj_y) < 10:  # Simple matching by position
                    matched_id = object_id
                    break
            
            if matched_id is not None:
                tracked_detections.append([matched_id, x, y, w, h, conf])
            else:
                tracked_detections.append([-1, x, y, w, h, conf])  # Unmatched detection
        
        return tracked_detections