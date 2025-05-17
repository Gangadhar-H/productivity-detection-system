# src/dashboard/dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import json
import time
import os
import matplotlib.pyplot as plt
import datetime
from PIL import Image
from collections import defaultdict

# Set page configuration
st.set_page_config(
    page_title="Productivity Detection Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to load zone definitions
def load_zones(zones_file):
    if not os.path.exists(zones_file):
        st.error(f"Zone file not found: {zones_file}")
        return {}
    
    with open(zones_file, 'r') as f:
        return json.load(f)
    
# Function to load tracking data
def load_tracking_data(data_dir):
    all_data = {
        "time_in_zones": {},
        "daily_productive_time": {}
    }
    
    # Find all JSON files in directory
    data_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not data_files:
        return all_data
    
    # Sort by timestamp to get latest first
    data_files.sort(reverse=True)
    
    # Load the most recent file
    latest_file = os.path.join(data_dir, data_files[0])
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        st.error(f"Error loading tracking data: {e}")
        return all_data

# Function to generate heatmap
def generate_heatmap(zones, time_in_zones, frame_size=(640, 480)):
    heatmap = np.zeros((frame_size[1], frame_size[0]), dtype=np.float32)
    
    # Create heatmap based on time spent
    for zone_id, zone in zones.items():
        # Get total time spent in this zone across all people
        total_time = sum(person_zones.get(zone_id, 0) 
                         for person_id, person_zones in time_in_zones.items())
        
        if total_time > 0:
            # Create a mask for this zone
            mask = np.zeros((frame_size[1], frame_size[0]), dtype=np.uint8)
            points = np.array(zone["points"], np.int32)
            points = points.reshape((-1, 1, 2))
            cv2.fillPoly(mask, [points], 255)
            
            # Add heat proportional to time spent
            intensity = min(1.0, total_time / 3600)  # Normalize to 0-1 (1 hour max)
            heatmap[mask > 0] += intensity
    
    # Normalize and convert to color
    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)
    
    # Convert to a colored heatmap
    heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
    
    # Create a transparent overlay
    alpha = 0.7
    overlay = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)
    for i in range(3):
        overlay[:, :, i] = heatmap_colored[:, :, i] * heatmap * alpha
    
    # Convert to PIL Image for Streamlit
    return Image.fromarray(overlay.astype(np.uint8))

# Function to render the workspace map with zones
def render_workspace_map(zones, frame_size=(640, 480), occupancy=None):
    if occupancy is None:
        occupancy = {}
    
    # Create a blank image
    frame = np.ones((frame_size[1], frame_size[0], 3), dtype=np.uint8) * 255
    
    # Define colors for different zone types
    colors = {
        "desk": (0, 255, 0),       # Green
        "meeting_room": (0, 0, 255),  # Blue
        "break_area": (0, 255, 255),  # Yellow
        "hallway": (128, 128, 128)   # Gray
    }
    
    # Draw each zone
    for zone_id, zone in zones.items():
        color = colors.get(zone["type"], (255, 255, 255))
        points = np.array(zone["points"], np.int32)
        points = points.reshape((-1, 1, 2))
        
        # Draw filled polygon with transparency
        overlay = frame.copy()
        cv2.fillPoly(overlay, [points], color)
        alpha = 0.4  # Transparency factor
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Draw outline
        cv2.polylines(frame, [points], True, color, 2)
        
        # Add zone name and occupancy
        centroid = np.mean(points, axis=0).astype(int)
        zone_text = f"{zone['name']}"
        if zone_id in occupancy:
            zone_text += f": {occupancy[zone_id]} people"
        
        cv2.putText(frame, zone_text, 
                  (centroid[0][0], centroid[0][1]), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Convert to PIL Image for Streamlit
    return Image.fromarray(frame)

# Function to calculate zone occupancy from time_in_zones
def calculate_recent_occupancy(time_in_zones, threshold=300):  # 5 minutes threshold
    """Estimate current occupancy based on recent activity"""
    occupancy = defaultdict(int)
    current_time = time.time()
    
    # This is a simplified estimation since we don't have real-time data in the dashboard
    # In a real system, this would come directly from the real-time tracker
    for person_id, zones in time_in_zones.items():
        for zone_id, time_spent in zones.items():
            if time_spent > threshold:  # Consider only significant time spent
                occupancy[zone_id] += 1
    
    return occupancy

# Function to format time
def format_time(seconds):
    """Format seconds into hours and minutes"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def main():
    # Add title and description
    st.title("Real-Time Productivity Detection Dashboard")
    st.write("Monitor workspace utilization and productivity in real-time")
    
    # Sidebar configuration
    st.sidebar.title("Configuration")
    
    # Set paths
    data_dir = st.sidebar.text_input("Data Directory", value="data/output")
    zones_file = st.sidebar.text_input("Zones File", value="data/zones/default_zones.json")
    
    # Refresh rate
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", min_value=1, max_value=60, value=5)
    
    # Load data
    zones = load_zones(zones_file)
    tracking_data = load_tracking_data(data_dir)
    
    # Convert string keys to proper types
    time_in_zones = {
        int(person_id): {int(zone_id) if zone_id.isdigit() else zone_id: time 
                          for zone_id, time in zones.items()}
        for person_id, zones in tracking_data.get("time_in_zones", {}).items()
    }
    
    productive_time = {int(person_id): time 
                       for person_id, time in tracking_data.get("daily_productive_time", {}).items()}
    
    # Calculate occupancy (simulated for dashboard)
    occupancy = calculate_recent_occupancy(time_in_zones)
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Live View", "Productivity Analytics", "Heatmap", "Settings"])
    
    with tab1:
        st.header("Live Workspace View")
        
        # Display the last update time
        st.write(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Render workspace map
        workspace_map = render_workspace_map(zones, occupancy=occupancy)
        st.image(workspace_map, caption="Current Workspace Occupancy")
        
        # Display occupancy statistics
        st.subheader("Zone Occupancy")
        
        # Create columns for zone stats
        cols = st.columns(4)
        
        # Group zones by type
        zone_types = {}
        for zone_id, zone in zones.items():
            zone_type = zone["type"]
            if zone_type not in zone_types:
                zone_types[zone_type] = []
            zone_types[zone_type].append((zone_id, zone["name"]))
        
        # Show occupancy by zone type
        for i, (zone_type, zone_list) in enumerate(zone_types.items()):
            with cols[i % 4]:
                st.write(f"**{zone_type.replace('_', ' ').title()}**")
                for zone_id, zone_name in zone_list:
                    count = occupancy.get(zone_id, 0)
                    st.write(f"{zone_name}: {count} people")
        
        # Add a button to refresh the data
        if st.button("Refresh Data"):
            st.experimental_rerun()
            
        # Auto-refresh
        st.info(f"Auto-refreshing every {refresh_rate} seconds")
        time.sleep(refresh_rate)
        st.experimental_rerun()
    
    with tab2:
        st.header("Productivity Analytics")
        
        # Convert data to DataFrame for easier visualization
        productive_df = pd.DataFrame(
            [(person_id, time) for person_id, time in productive_time.items()],
            columns=["Person ID", "Productive Time (seconds)"]
        )
        
        if not productive_df.empty:
            # Add human-readable time column
            productive_df["Productive Time"] = productive_df["Productive Time (seconds)"].apply(format_time)
            
            # Display productive time per person
            st.subheader("Productive Time by Person")
            
            # Bar chart of productive time
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(productive_df["Person ID"].astype(str), 
                   productive_df["Productive Time (seconds)"] / 3600)  # Convert to hours
            ax.set_xlabel("Person ID")
            ax.set_ylabel("Productive Hours")
            ax.set_title("Productive Time by Person")
            st.pyplot(fig)
            
            # Display the data table
            st.dataframe(productive_df[["Person ID", "Productive Time"]])
            
            # Calculate overall statistics
            avg_productive_time = productive_df["Productive Time (seconds)"].mean()
            total_productive_time = productive_df["Productive Time (seconds)"].sum()
            
            # Display in columns
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Productive Time", format_time(avg_productive_time))
            with col2:
                st.metric("Total Productive Time", format_time(total_productive_time))
            
            # Time spent by zone type
            st.subheader("Time Spent by Zone Type")
            
            # Aggregate time by zone type
            zone_type_time = defaultdict(float)
            for person_id, person_zones in time_in_zones.items():
                for zone_id, time_spent in person_zones.items():
                    if zone_id in zones:
                        zone_type = zones[zone_id]["type"]
                        zone_type_time[zone_type] += time_spent
            
            # Create DataFrame for zone type time
            zone_type_df = pd.DataFrame([
                (zone_type, time_spent / 3600)  # Convert to hours
                for zone_type, time_spent in zone_type_time.items()
            ], columns=["Zone Type", "Hours Spent"])
            
            # Display as pie chart
            if not zone_type_df.empty:
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(zone_type_df["Hours Spent"], 
                       labels=zone_type_df["Zone Type"].apply(lambda x: x.replace("_", " ").title()),
                       autopct='%1.1f%%')
                ax.set_title("Time Distribution by Zone Type")
                st.pyplot(fig)
        else:
            st.info("No productivity data available yet.")
    
    with tab3:
        st.header("Workspace Heatmap")
        
        # Generate heatmap
        heatmap = generate_heatmap(zones, time_in_zones)
        
        # Display heatmap
        st.image(heatmap, caption="Workspace Utilization Heatmap")
        
        st.info("The heatmap shows intensity based on time spent in each zone. Brighter colors indicate more time spent.")
        
        # Allow downloading heatmap
        heatmap_byte_arr = io.BytesIO()
        heatmap.save(heatmap_byte_arr, format='PNG')
        st.download_button(
            label="Download Heatmap",
            data=heatmap_byte_arr.getvalue(),
            file_name="workspace_heatmap.png",
            mime="image/png"
        )
    
    with tab4:
        st.header("System Settings")
        
        # Display system info
        st.subheader("System Information")
        st.info(f"Zone file: {zones_file}")
        st.info(f"Data directory: {data_dir}")
        
        # Display zone information
        st.subheader("Zone Configuration")
        
        # Convert zones to DataFrame
        zones_df = pd.DataFrame([
            {
                "Zone ID": zone_id,
                "Name": zone["name"],
                "Type": zone["type"],
                "Points": str(zone["points"])
            }
            for zone_id, zone in zones.items()
        ])
        
        if not zones_df.empty:
            st.dataframe(zones_df)
        else:
            st.warning("No zones defined.")
        
        # Allow user to edit refresh rate
        new_refresh_rate = st.number_input(
            "Set Refresh Rate (seconds)",
            min_value=1,
            max_value=300,
            value=refresh_rate
        )
        
        if new_refresh_rate != refresh_rate:
            st.success(f"Refresh rate updated to {new_refresh_rate} seconds")

if __name__ == "__main__":
    try:
        import io  # Import required for download functionality
        main()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")