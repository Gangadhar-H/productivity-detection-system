# src/main.py
import cv2
import time
import argparse
import os
import json
from src.video_processing.camera import CameraStream
from src.video_processing.detector import PersonDetector
from src.video_processing.tracker import SimpleTracker
from src.zone_tracking.zone_manager import ZoneManager
from src.zone_tracking.person_zone_tracker import PersonZoneTracker

def format_time(seconds):
    """Format seconds into hours and minutes"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def main():
    parser = argparse.ArgumentParser(description='Real-Time Productivity Detection System')
    parser.add_argument('--source', type=str, default='0', help='Source of the video (webcam index or video file path)')
    parser.add_argument('--zones', type=str, default='data/zones/default_zones.json', help='Path to zones definition file')
    parser.add_argument('--output', type=str, default='data/output', help='Output directory for generated data')
    parser.add_argument('--display', action='store_true', help='Display video feed with detections')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Initialize components
    print("Initializing camera...")
    camera = CameraStream(args.source).start()
    time.sleep(1)  # Allow camera to warm up
    
    print("Loading person detector...")
    detector = PersonDetector(confidence=0.5)
    
    print("Setting up tracker...")
    tracker = SimpleTracker(max_disappeared=30, min_iou=0.3)
    
    print("Initializing zone manager...")
    zone_manager = ZoneManager(args.zones)
    
    # Create default zones if no zones file exists
    if not os.path.exists(args.zones):
        print("Creating default zones...")
        # Create example zones based on 640x480 frame
        zone_manager.create_zone(
            "desk1", "Desk 1", "desk", 
            [[100, 100], [300, 100], [300, 200], [100, 200]]
        )
        zone_manager.create_zone(
            "meeting1", "Meeting Room", "meeting_room", 
            [[350, 100], [550, 100], [550, 200], [350, 200]]
        )
        zone_manager.create_zone(
            "break1", "Break Area", "break_area", 
            [[100, 250], [300, 250], [300, 350], [100, 350]]
        )
        zone_manager.save_zones(args.zones)
    
    print("Setting up zone tracker...")
    zone_tracker = PersonZoneTracker(zone_manager)
    
    print("System initialized and running...")
    
    # Save data every 5 minutes
    last_save_time = time.time()
    save_interval = 300  # 5 minutes in seconds
    
    try:
        while True:
            frame = camera.read()
            if frame is None:
                print("End of video or camera disconnected")
                break
            
            # Detect people
            detections = detector.detect(frame)
            
            # Track people
            tracked_detections = tracker.update(detections)
            
            # Update zone tracking
            zone_tracker.update(tracked_detections)
            
            # Display if requested
            if args.display:
                # Draw detections
                disp_frame = detector.draw_detections(frame.copy(), tracked_detections)
                
                # Draw zones
                disp_frame = zone_manager.draw_zones(disp_frame)
                
                # Add information overlay
                occupancy = zone_tracker.get_zone_occupancy()
                y_pos = 30
                cv2.putText(disp_frame, f"FPS: {camera.get_fps():.1f}", 
                          (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_pos += 30
                
                # Show zone occupancy
                for zone_id, count in occupancy.items():
                    if zone_id in zone_manager.zones:
                        zone_name = zone_manager.zones[zone_id]["name"]
                        cv2.putText(disp_frame, f"{zone_name}: {count} people", 
                                  (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        y_pos += 30
                
                # Show productive time for each tracked person
                for detection in tracked_detections:
                    person_id = detection[0]
                    if person_id >= 0:
                        productive_time = zone_tracker.get_productive_time(person_id)
                        formatted_time = format_time(productive_time)
                        x, y = int(detection[1]), int(detection[2])
                        cv2.putText(disp_frame, f"ID: {person_id}, Prod: {formatted_time}", 
                                  (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # Display the frame
                cv2.imshow('Real-Time Productivity Detection', disp_frame)
                
                # Exit if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # Save data periodically
            current_time = time.time()
            if current_time - last_save_time > save_interval:
                output_file = os.path.join(args.output, f"tracking_data_{int(current_time)}.json")
                zone_tracker.save_data(output_file)
                last_save_time = current_time
                print(f"Data saved to {output_file}")
    
    finally:
        # Clean up
        if args.display:
            cv2.destroyAllWindows()
        camera.stop()
        
        # Save final data
        output_file = os.path.join(args.output, f"tracking_data_final.json")
        zone_tracker.save_data(output_file)
        print(f"Final data saved to {output_file}")
        
if __name__ == "__main__":
    main()