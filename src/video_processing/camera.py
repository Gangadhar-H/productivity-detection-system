# src/video_processing/camera.py
import cv2
import time
import threading

class CameraStream:
    """Class to handle video stream from camera or video file"""
    
    def __init__(self, source=0):
        """Initialize with camera index or video file path"""
        self.source = source
        self.cap = None
        self.frame = None
        self.stopped = False
        self.fps = 0
        self.last_frame_time = 0
        
    def start(self):
        """Start the video stream thread"""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise ValueError(f"Unable to open video source {self.source}")
            
        # Start the thread to read frames
        threading.Thread(target=self.update, daemon=True).start()
        return self
        
    def update(self):
        """Keep reading frames until stopped"""
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                self.stopped = True
                break
                
            # Calculate FPS
            current_time = time.time()
            if self.last_frame_time > 0:
                self.fps = 1 / (current_time - self.last_frame_time)
            self.last_frame_time = current_time
                
            self.frame = frame
            
    def read(self):
        """Return the current frame"""
        return self.frame
        
    def get_fps(self):
        """Return the current FPS"""
        return self.fps
        
    def stop(self):
        """Stop the video stream"""
        self.stopped = True
        if self.cap:
            self.cap.release()