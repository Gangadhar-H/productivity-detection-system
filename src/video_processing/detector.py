# src/video_processing/detector.py
from ultralytics import YOLO
import cv2
import numpy as np

class PersonDetector:
    """Class to detect people in frames using YOLOv8"""
    
    def __init__(self, model_path='yolov8n.pt', confidence=0.5):
        """Initialize with model path and confidence threshold"""
        # Load the YOLOv8 model
        self.model = YOLO(model_path)
        self.confidence = confidence
        
    def detect(self, frame):
        """
        Detect people in the frame
        Returns: list of detection results with format [id, x, y, w, h, confidence]
        """
        if frame is None:
            return []
        
        # Run detection
        results = self.model(frame, classes=0)  # class 0 is person in COCO dataset
        
        detections = []
        
        # Process results
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = box.conf[0].cpu().numpy()
                
                if confidence >= self.confidence:
                    # Calculate center, width, height
                    x = (x1 + x2) / 2
                    y = (y1 + y2) / 2
                    w = x2 - x1
                    h = y2 - y1
                    
                    # Assign a temporary ID (will be replaced by tracker)
                    temp_id = -1
                    
                    detections.append([temp_id, x, y, w, h, confidence])
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw detection boxes on the frame"""
        for det in detections:
            _, x, y, w, h, conf = det
            
            # Calculate box coordinates
            x1 = int(x - w/2)
            y1 = int(y - h/2)
            x2 = int(x + w/2)
            y2 = int(y + h/2)
            
            # Draw box and label
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person: {conf:.2f}", 
                       (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0, 255, 0), 2)
        
        return frame