import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import json
import tempfile
import glob

# Add scripts directory to path
sys.path.append("scripts")

# Import processing scripts
from extract_frames import extract_frames
from analyze_frames import analyze_frames_in_directory, create_analysis_prompt
from create_database import create_database, import_analysis_files

# Set page config - removed VISOR branding
st.set_page_config(
    page_title="Construction Safety Monitor",
    page_icon="🚧",
    layout="wide"
)

# Updated CSS to remove box shadows and empty containers
st.markdown("""
<style>
    /* Base colors - everything black and white */
    .stApp {
        background-color: white;
    }
    
    /* ALL text black */
    p, h1, h2, h3, h4, h5, h6, span, div, label, li, a {
        color: #000000 !important;
    }
    
    /* ALL headings black (override blues) */
    .main-title, 
    .section-heading, 
    h3[style*="color: #1e40af"],
    p[style*="color: #1e40af"],
    p[style*="color: #1e3a8a"],
    div[style*="color: #1e40af"],
    .metric-value {
        color: #000000 !important; 
    }
    
    /* Severity indicators - all black text on light grey background */
    .severity-high, .severity-medium, .severity-low {
        color: #000000 !important;
        font-weight: 600;
        background-color: #f3f4f6;
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    /* Make buttons black */
    button[data-testid="baseButton-primary"] {
        background-color: #000000 !important;
        color: white !important;
    }
    
    /* Make tab indicators black */
    .stTabs [aria-selected="true"] {
        color: #000000 !important;
        border-bottom-color: #000000 !important;
    }
    
    /* Make progress indicators black */
    .progress-label, .stage-active {
        color: #000000 !important;
    }
    
    .stage-active {
        border-color: #000000 !important;
        background-color: rgba(0, 0, 0, 0.05) !important;
    }
    
    /* Streamlit progress bar */
    .stProgress > div > div > div {
        background-color: #000000 !important;
    }
    
    /* Override all alert colors to black/white */
    div[data-testid="stError"], div[data-testid="stWarning"], div[data-testid="stInfo"], div[data-testid="stSuccess"] {
        background-color: #f8f8f8 !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }
    
    /* Override expander styling */
    .streamlit-expanderHeader {
        color: #000000 !important;
    }
    
    /* Fix recommendation headers */
    div[style*="color: #1e40af"] {
        color: #000000 !important;
    }
    
    /* Charts should use grayscale */
    .js-plotly-plot .plotly .modebar {
        filter: grayscale(100%);
    }
    
    /* Slider track & thumb */
    [data-testid="stSlider"] > div > div > div {
        background-color: #000000 !important;
    }
    
    /* Checkbox color */
    [data-testid="stCheckbox"] svg {
        fill: #000000 !important;
    }
    
    /* Any remaining blue accents */
    div[style*="background-color: rgba(30, 64, 175, 0.1)"] {
        background-color: rgba(0, 0, 0, 0.05) !important;
    }
    
    div[style*="border: 1px solid #1e40af"] {
        border: 1px solid #000000 !important;
    }
    
    /* Override pie chart colors to grayscale */
    svg .trace.scatter .points path {
        fill: #000000 !important;
    }
    
    /* Make all chart text black */
    .js-plotly-plot .plotly text {
        fill: #000000 !important;
        color: #000000 !important;
    }
    
    /* Make chart axes black */
    .js-plotly-plot .plotly .xtick text,
    .js-plotly-plot .plotly .ytick text {
        fill: #000000 !important;
    }
    
    /* Change dark backgrounds to white with black borders */
    div[data-testid="stFileUploader"] {
        background-color: white !important;
        border: 1px solid #000000 !important;
    }
    
    /* Make all input fields white with black text */
    input, textarea, [data-testid="stTextInput"] > div {
        background-color: white !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }
    
    /* Convert red elements to black or white */
    .st-emotion-cache-1w9aeh3 {
        background-color: white !important;
        color: #000000 !important;
    }
    
    /* Override any remaining colored elements */
    [data-testid="stCheckbox"] > div > div {
        background-color: white !important;
        border: 1px solid #000000 !important;
    }
    
    /* File uploader background (dark box in screenshot) */
    [data-testid="stFileUploader"] > section {
        background-color: white !important;
        border: 1px solid #000000 !important;
    }
    
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] svg {
        color: #000000 !important;
        fill: #000000 !important;
    }
    
    /* File uploader button */
    [data-testid="stFileUploader"] button {
        background-color: white !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }
    
    /* API Key input field (dots) */
    input[type="password"] {
        color: #000000 !important;
    }
    
    /* Slider track - make it black */
    [data-testid="stSlider"] > div > div > div:first-child {
        background-color: #DDDDDD !important;
    }
    
    /* Slider thumb - make it black */
    [data-testid="stSlider"] > div > div > div:nth-child(2) {
        background-color: #000000 !important;
    }
    
    /* Checkbox - make checked state black */
    [data-testid="stCheckbox"] svg {
        fill: #000000 !important;
    }
    
    /* Fix for dark buttons with black text */
    button[kind="secondary"], 
    button.stButton button,
    button.streamlit-button,
    .stButton>button {
        color: white !important;
        background-color: #000000 !important;
        border: 1px solid #000000 !important;
    }
    
    /* Fix specifically for "Clear All Previous Results" button */
    button:contains("Clear All Previous Results"),
    button:contains("Deploy") {
        color: white !important;
        background-color: #000000 !important;
    }
    
    /* Alt approach - fixing any button with dark background */
    button[style*="background-color: rgb(38, 39, 48)"],
    button[style*="background-color: #262730"],
    button[style*="background-color: rgb(23, 23, 23)"] {
        color: white !important;
    }
    
    /* Target footer buttons like Deploy */
    .css-10pw50, .css-fblp2m {
        color: white !important;
    }
    
    /* Target bottom footer menu */
    [data-testid="stAppViewBlockContainer"] > div:last-child button,
    [data-testid="baseButton-secondary"] {
        color: white !important;
    }
    
    /* Safety measure - any dark background should have white text */
    button {
        color: white !important;
    }
    
    /* Prevent any buttons from having inherit colors */
    button * {
        color: inherit !important;
    }
    
    /* Style the Clear Results button specifically */
    .clear-results-button {
        background-color: #000000;
        color: white !important;
        padding: 10px 15px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        font-weight: bold;
        display: inline-block;
        text-align: center;
        text-decoration: none;
        margin: 10px 0;
    }
    
    /* Checkbox label should be black */
    .confirmation-text {
        color: #000000 !important;
        font-weight: normal;
    }
</style>
""", unsafe_allow_html=True)

# Function to create a database connection
@st.cache_resource
def get_connection():
    # Create database if it doesn't exist
    if not os.path.exists("database.sqlite"):
        create_database("database.sqlite")
    return sqlite3.connect("database.sqlite", check_same_thread=False)

# Create database connection
conn = get_connection()

# Functions for database queries
def get_violation_stats(current_only=True):
    """Get statistics about violations from the database"""
    cursor = conn.cursor()
    
    # Base query parts
    select_total = "SELECT COUNT(*) FROM violations v JOIN frames f ON v.frame_id = f.id JOIN videos vid ON f.video_id = vid.id"
    select_severity = """
    SELECT severity, COUNT(*) FROM violations v 
    JOIN frames f ON v.frame_id = f.id 
    JOIN videos vid ON f.video_id = vid.id
    """
    select_types = """
    SELECT violation_type, COUNT(*) FROM violations v
    JOIN frames f ON v.frame_id = f.id
    JOIN videos vid ON f.video_id = vid.id
    """
    
    # Add filter for current videos
    where_current = ""
    params = []
    
    if current_only and st.session_state.current_videos:
        placeholders = ', '.join(['?'] * len(st.session_state.current_videos))
        where_current = f"WHERE vid.video_name IN ({placeholders})"
        params.extend(st.session_state.current_videos)
    
    # Total violations
    cursor.execute(f"{select_total} {where_current}", params)
    total_violations = cursor.fetchone()[0] or 0
    
    # Violations by severity
    severity_query = select_severity
    severity_params = []
    
    if current_only and st.session_state.current_videos:
        # We need to combine the WHERE clauses properly
        severity_query += f"WHERE severity IS NOT NULL AND vid.video_name IN ({', '.join(['?'] * len(st.session_state.current_videos))})"
        severity_params.extend(st.session_state.current_videos)
    else:
        # Just the basic severity filter
        severity_query += "WHERE severity IS NOT NULL"
    
    severity_query += " GROUP BY severity"
    cursor.execute(severity_query, severity_params)
    severity_results = cursor.fetchall()
    severity_counts = {s.lower(): c for s, c in severity_results}
    
    # Violations by type
    types_query = select_types
    types_params = []
    
    if current_only and st.session_state.current_videos:
        types_query += f"WHERE vid.video_name IN ({', '.join(['?'] * len(st.session_state.current_videos))})"
        types_params.extend(st.session_state.current_videos)
    
    types_query += " GROUP BY violation_type ORDER BY COUNT(*) DESC"
    cursor.execute(types_query, types_params)
    violation_types = cursor.fetchall()
    
    return {
        'total': total_violations,
        'high': severity_counts.get('high', 0),
        'medium': severity_counts.get('medium', 0),
        'low': severity_counts.get('low', 0),
        'types': violation_types
    }

def get_violations(severity=None, violation_type=None, limit=50, current_only=True):
    """Get violations filtered by severity and type"""
    cursor = conn.cursor()
    
    query = """
    SELECT 
        v.id, 
        v.description, 
        v.location, 
        v.severity, 
        v.violation_type,
        v.recommendation,
        f.image_path,
        vid.video_name
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
        JOIN videos vid ON f.video_id = vid.id
    """
    
    conditions = []
    params = []
    
    if severity and severity != "All":
        conditions.append("v.severity = ?")
        params.append(severity.lower())
    
    if violation_type and violation_type != "All":
        conditions.append("v.violation_type = ?")
        params.append(violation_type)
    
    # Add filter for current videos only
    if current_only and st.session_state.current_videos:
        placeholders = ', '.join(['?'] * len(st.session_state.current_videos))
        conditions.append(f"vid.video_name IN ({placeholders})")
        params.extend(st.session_state.current_videos)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY v.id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    violations = cursor.fetchall()
    
    return [{
        "id": v[0],
        "desc": v[1],
        "location": v[2],
        "severity": v[3],
        "type": v[4],
        "recommendation": v[5],
        "image_path": v[6],
        "video_name": v[7]  # Include video name in results
    } for v in violations]

def get_violation_trends(current_only=True):
    """Get violation trends over time"""
    cursor = conn.cursor()
    
    query = """
    SELECT 
        f.timestamp_seconds,
        COUNT(v.id) as violation_count
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
        JOIN videos vid ON f.video_id = vid.id
    """
    
    params = []
    if current_only and st.session_state.current_videos:
        placeholders = ', '.join(['?'] * len(st.session_state.current_videos))
        query += f" WHERE vid.video_name IN ({placeholders})"
        params.extend(st.session_state.current_videos)
    
    query += """
    GROUP BY 
        f.timestamp_seconds
    ORDER BY 
        f.timestamp_seconds
    """
    
    cursor.execute(query, params)
    
    results = cursor.fetchall()
    if results:
        df = pd.DataFrame(results, columns=['Timestamp', 'Count'])
        return df
    return pd.DataFrame({"Timestamp": [], "Count": []})

def search_violations_by_query(query_text):
    """Search for violations matching a query"""
    cursor = conn.cursor()
    search_text = f"%{query_text}%"
    
    cursor.execute("""
    SELECT 
        v.id, 
        v.description, 
        v.location, 
        v.severity, 
        v.violation_type,
        v.recommendation,
        f.image_path
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
    WHERE 
        v.description LIKE ? OR
        v.location LIKE ? OR
        v.violation_type LIKE ?
    ORDER BY v.id DESC
    LIMIT 10
    """, (search_text, search_text, search_text))
    
    violations = cursor.fetchall()
    
    return [{
        "id": v[0],
        "desc": v[1],
        "location": v[2],
        "severity": v[3],
        "type": v[4],
        "recommendation": v[5],
        "image_path": v[6]
    } for v in violations]

# Remove animation elements
if 'animation_shown' not in st.session_state:
    st.session_state.animation_shown = True

# Initialize session state variables
if 'custom_queries' not in st.session_state:
    st.session_state.custom_queries = []
if 'videos_analyzed' not in st.session_state:
    st.session_state.videos_analyzed = False
if 'openai_api_key' not in st.session_state:
    # Just load from environment, don't prompt user
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
if 'current_videos' not in st.session_state:
    st.session_state.current_videos = []

# Simplified header
st.markdown("""
<div class="header-container">
    <h1 class="main-title">Construction Safety Monitor</h1>
</div>
""", unsafe_allow_html=True)

# Main sections with no empty containers
st.markdown('<div class="section-heading">Upload & Configure</div>', unsafe_allow_html=True)

# VIDEO UPLOAD SECTION - Modified to show smaller videos
st.markdown('<h3 style="color: #1e40af; font-size: 1.2rem; margin-bottom: 0.5rem;">Video Upload</h3>', unsafe_allow_html=True)

# Simplified upload with no extra wrapper divs
uploaded_files = st.file_uploader("Upload construction site videos", 
                                 type=["mp4", "avi", "mov", "mkv"], 
                                 accept_multiple_files=True,
                                 label_visibility="collapsed")
st.markdown('<p style="color: #6b7280; font-size: 0.8rem;">Supported formats: MP4, AVI, MOV, MKV | Max size: 200MB</p>', unsafe_allow_html=True)

if uploaded_files:
    st.success(f"Uploaded {len(uploaded_files)} video(s)")
    
    # Display video thumbnails in a more compact grid
    video_count = len(uploaded_files)
    cols_per_row = min(4, video_count)  # Show more videos per row
    
    for i in range(0, video_count, cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < video_count:
                with cols[j]:
                    # Save the video temporarily
                    temp_dir = tempfile.mkdtemp()
                    temp_path = os.path.join(temp_dir, uploaded_files[i+j].name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_files[i+j].getbuffer())
                    
                    # Display smaller video thumbnail
                    st.video(temp_path)
                    st.caption(uploaded_files[i+j].name)

# ANALYSIS CONFIGURATION SECTION - Moved up since API key section was removed
st.markdown('<h3 style="color: #1e40af; font-size: 1.2rem; margin-top: 1rem; margin-bottom: 0.5rem;">Analysis Configuration</h3>', unsafe_allow_html=True)

config_cols = st.columns(2)

with config_cols[0]:
    st.markdown('<p style="color: #1e40af; font-weight: 600;">Safety Violations to Detect</p>', unsafe_allow_html=True)
    
    detect_ppe = st.checkbox("Missing PPE (hard hats, vests, gloves, harnesses)", value=True)
    detect_positions = st.checkbox("Workers in dangerous positions", value=True)
    detect_equipment = st.checkbox("Improper equipment usage", value=True)
    detect_exits = st.checkbox("Blocked emergency exits/pathways", value=True)
    detect_other = st.checkbox("Other safety hazards", value=True)
    
    # Create a safety checks dictionary
    safety_checks = {
        "ppe": detect_ppe,
        "dangerous_positions": detect_positions,
        "improper_equipment": detect_equipment,
        "blocked_exits": detect_exits,
        "other_hazards": detect_other
    }

with config_cols[1]:
    st.markdown('<p style="color: #1e40af; font-weight: 600;">Processing Options</p>', unsafe_allow_html=True)
    
    # Frame extraction settings
    frame_interval = st.slider("Extract frames every ___ seconds", 1, 10, 2)
    
    # Worker tracking
    enable_tracking = st.checkbox("Enable worker tracking and identification", value=True)

# Analysis Button (moved up to replace the query section)
if uploaded_files:
    st.markdown('<div style="margin-top: 1rem;">', unsafe_allow_html=True)
    process_button = st.button("Start Safety Analysis", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if process_button:
        # Reset current videos list at the start of a new analysis
        st.session_state.current_videos = []
        
        # Remove API key check - we assume it's already set
        # Run the analysis pipeline
        overall_progress_bar = st.progress(0)
        # Create a container for detailed progress info
        progress_container = st.container()
        with progress_container:
            st.markdown('<div class="progress-container">', unsafe_allow_html=True)
            
            # Visual stage indicator
            current_stage = 0  # 0=extraction, 1=analysis, 2=import
            st.markdown("""
            <div class="stage-indicator">
                <div class="stage stage-active" id="stage-extract">Extract Frames</div>
                <div class="stage stage-pending" id="stage-analyze">Analyze Frames</div>
                <div class="stage stage-pending" id="stage-import">Save Results</div>
            </div>
            """, unsafe_allow_html=True)
            
            stage_text = st.empty()
            frame_progress = st.empty()
            frame_progress_bar = st.empty()
            frame_status = st.empty()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        results_container = st.container()
        
        try:
            with st.spinner("Processing videos..."):
                # For each uploaded video
                for i, uploaded_file in enumerate(uploaded_files):
                    video_name = os.path.splitext(uploaded_file.name)[0]
                    stage_text.text(f"Processing video {i+1}/{len(uploaded_files)}: {video_name}")
                    
                    # Add to current videos list
                    st.session_state.current_videos.append(video_name)
                    
                    # Step 1: Save video temporarily
                    temp_dir = tempfile.mkdtemp()
                    temp_video_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_video_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Step 2: Create output directories
                    frames_dir = f"data/frames/{video_name}"
                    results_dir = f"results/{video_name}"
                    os.makedirs(frames_dir, exist_ok=True)
                    os.makedirs(results_dir, exist_ok=True)
                    
                    # Step 3: Extract frames from video
                    stage_text.text(f"Extracting frames from {video_name}...")
                    
                    # Define a callback function for frame extraction progress
                    def extraction_progress(current, total, percent):
                        frame_progress.text(f"Extracting frame {current}/{total}")
                        frame_progress_bar.progress(percent)
                        frame_status.text(f"{current} frames extracted ({percent:.1%} complete)")
                        # Also update the overall progress
                        overall_percent = ((i * 3) + (percent * 1)) / (len(uploaded_files) * 3)
                        overall_progress_bar.progress(overall_percent)
                    
                    try:
                        extract_frames(temp_video_path, "data/frames", frame_interval, extraction_progress)
                    except Exception as e:
                        st.error(f"Error extracting frames: {str(e)}")
                        continue
                    
                    # Step 4: Analyze frames
                    stage_text.text(f"Analyzing frames from {video_name} for safety violations...")
                    
                    # Define a callback function for analysis progress
                    def analysis_progress(current, total, percent):
                        frame_progress.text(f"Analyzing frame {current}/{total}")
                        frame_progress_bar.progress(percent)
                        frame_status.text(f"{current} frames analyzed ({percent:.1%} complete)")
                        # Also update the overall progress
                        overall_percent = ((i * 3) + 1 + (percent * 1)) / (len(uploaded_files) * 3)
                        overall_progress_bar.progress(overall_percent)
                    
                    try:
                        analyze_frames_in_directory(
                            frames_dir, 
                            results_dir, 
                            st.session_state.openai_api_key,
                            custom_queries=st.session_state.custom_queries,
                            safety_checks=safety_checks,
                            progress_callback=analysis_progress
                        )
                    except Exception as e:
                        st.error(f"Error analyzing frames: {str(e)}")
                        continue
                    
                    # Step 5: Import results to database
                    stage_text.text(f"Saving analysis results for {video_name}...")
                    frame_progress.text("Importing results to database...")
                    frame_progress_bar.progress(0)
                    
                    try:
                        # Count files to import for progress tracking
                        json_files = glob.glob(os.path.join(results_dir, '**', '*_analysis.json'), recursive=True)
                        total_files = len(json_files)
                        
                        # Define a custom import function that updates progress
                        def import_with_progress():
                            conn = sqlite3.connect("database.sqlite", check_same_thread=False)
                            imported = 0
                            
                            for file_path in json_files:
                                # Import logic here (simplified version)
                                try:
                                    # Your import logic from create_database.py
                                    # Process the file...
                                    
                                    # Update progress after each file
                                    imported += 1
                                    percent = imported / total_files
                                    frame_progress.text(f"Importing result {imported}/{total_files}")
                                    frame_progress_bar.progress(percent)
                                    frame_status.text(f"{imported} results imported ({percent:.1%} complete)")
                                    
                                    # Also update the overall progress
                                    overall_percent = ((i * 3) + 2 + (percent * 1)) / (len(uploaded_files) * 3)
                                    overall_progress_bar.progress(overall_percent)
                                except Exception as e:
                                    # Log error but continue with other files
                                    print(f"Error importing {file_path}: {e}")
                            
                            conn.close()
                            return imported
                        
                        # If you prefer to use your existing function instead of the custom one above:
                        import_analysis_files("database.sqlite", results_dir)
                        # Update progress after import completes
                        overall_percent = ((i * 3) + 3) / (len(uploaded_files) * 3)
                        overall_progress_bar.progress(overall_percent)
                        
                    except Exception as e:
                        st.error(f"Error importing results to database: {str(e)}")
                        continue
                
                # Complete
                overall_progress_bar.progress(1.0)
                stage_text.text("Analysis complete!")
                frame_progress.empty()
                frame_progress_bar.empty()
                frame_status.text("All videos processed successfully!")
                st.session_state.videos_analyzed = True
                
        except Exception as e:
            st.error(f"An error occurred during processing: {str(e)}")
                
# RESULTS SECTION - Modified to remove white box and custom query tab
violation_stats = get_violation_stats()

if violation_stats['total'] > 0 or st.session_state.videos_analyzed:
    st.markdown('<div class="section-heading">Analysis Results</div>', unsafe_allow_html=True)
    
    # Create tabs for different views of the data
    tabs = st.tabs(["Summary", "Violations Gallery", "Dashboard"])
    
    with tabs[0]:  # Summary tab
        # Add a toggle to filter results
        show_current_only = st.checkbox("Show current video results only", value=True)
        
        # Get filtered statistics
        violation_stats = get_violation_stats(current_only=show_current_only)
        
        # Display metrics in a row
        metric_cols = st.columns(4)
        
        with metric_cols[0]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #000000 !important;">{violation_stats['total']}</div>
                <div class="metric-label" style="color: #000000 !important;">Total Violations</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[1]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #000000 !important;">{violation_stats['high']}</div>
                <div class="metric-label" style="color: #000000 !important;">High Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[2]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #000000 !important;">{violation_stats['medium']}</div>
                <div class="metric-label" style="color: #000000 !important;">Medium Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[3]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #000000 !important;">{violation_stats['low']}</div>
                <div class="metric-label" style="color: #000000 !important;">Low Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Violation type breakdown
        st.markdown('<p style="color: #000000; font-weight: 600; margin-top: 1.5rem;">Violation Type Breakdown</p>', unsafe_allow_html=True)
        
        if violation_stats['types']:
            chart_data = pd.DataFrame(violation_stats['types'], columns=["Violation Type", "Count"])
            
            # Create a monochrome bar chart
            fig = px.bar(
                chart_data,
                x="Violation Type",
                y="Count",
                # Instead of a color scale, use a single color
                color_discrete_sequence=["#000000"],  # Black bars
                text="Count"
            )
            
            # Ensure all text is black and clearly visible
            fig.update_traces(
                textfont=dict(color="#000000", size=14),  # Black text on bars
                textposition="outside"  # Position text outside bars for better visibility
            )
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',  # Transparent background
                paper_bgcolor='rgba(0,0,0,0)',  # Transparent paper
                font=dict(color='#000000', size=14),  # Black font for all text
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis=dict(
                    title_font=dict(color="#000000", size=16),
                    tickfont=dict(color="#000000", size=14),
                    gridcolor="#EEEEEE"  # Very light grey grid lines
                ),
                yaxis=dict(
                    title_font=dict(color="#000000", size=16),
                    tickfont=dict(color="#000000", size=14),
                    gridcolor="#EEEEEE"  # Very light grey grid lines
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No violation data available yet. Analyze videos to see results.")
    
    with tabs[1]:  # Violations Gallery
        # Filtering options
        filter_cols = st.columns(4)
        
        with filter_cols[0]:
            severity_filter = st.selectbox("Filter by Severity", ["All", "High", "Medium", "Low"])
        
        with filter_cols[1]:
            # Get violation types from database
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT violation_type FROM violations WHERE violation_type IS NOT NULL")
            db_violation_types = cursor.fetchall()
            
            violation_types = ["All"]
            if db_violation_types:
                violation_types += [vt[0] for vt in db_violation_types if vt[0]]
            
            violation_filter = st.selectbox("Filter by Violation Type", violation_types)
        
        with filter_cols[2]:
            sort_options = ["Newest First", "Oldest First", "Severity (High to Low)", "Severity (Low to High)"]
            sort_by = st.selectbox("Sort by", sort_options)
        
        with filter_cols[3]:
            # Add option to show current videos only or all videos
            current_only = st.checkbox("Current videos only", value=True)
        
        # Get filtered violations
        violations = get_violations(
            severity=severity_filter if severity_filter != "All" else None,
            violation_type=violation_filter if violation_filter != "All" else None,
            limit=50,
            current_only=current_only  # Pass the checkbox value
        )
        
        if violations:
            # Display violations in a grid
            st.markdown('<div style="margin-top: 1.5rem;">', unsafe_allow_html=True)
            # Display in 2 columns
            num_cols = 2
            for i in range(0, len(violations), num_cols):
                cols = st.columns(num_cols)
                
                for j in range(num_cols):
                    if i + j < len(violations):
                        violation = violations[i + j]
                        with cols[j]:
                            severity_class = f"severity-{violation['severity']}" if violation['severity'] else ""
                            
                            # Update the expander to use colors consistently with our theme
                            with st.expander(f"{violation['severity'].upper() if violation['severity'] else 'UNKNOWN'} - {violation['desc'][:40]}...", expanded=False):
                                # Show violation image
                                if violation['image_path'] and os.path.exists(violation['image_path']):
                                    try:
                                        st.image(Image.open(violation['image_path']), use_container_width=True)
                                    except Exception as e:
                                        st.warning(f"Could not display image: {e}")
                                
                                # Violation details with updated styling
                                st.markdown(f"""
                                <div class="violation-card">
                                    <div class="violation-detail"><strong>Type:</strong> {violation['type'] or 'Unknown'}</div>
                                    <div class="violation-detail"><strong>Description:</strong> {violation['desc']}</div>
                                    <div class="violation-detail"><strong>Location:</strong> {violation['location'] or 'Not specified'}</div>
                                    <div class="violation-detail"><strong>Severity:</strong> <span class="{severity_class}">{(violation['severity'] or 'Unknown').upper()}</span></div>
                                    <div class="violation-detail"><strong>Recommendation:</strong> {violation['recommendation'] or 'No recommendation available'}</div>
                                    <div class="violation-detail"><strong>Video:</strong> {violation['video_name']}</div>
                                </div>
                                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No violations found matching your filters. Try changing the filters or analyze more videos.")
    
    with tabs[2]:  # Dashboard tab
        show_current_only_dashboard = st.checkbox("Show current video results only", value=True, key="dashboard_filter")
        
        # Create subtabs for the dashboard
        dashboard_tabs = st.tabs(["Trends", "Severity Analysis", "Recommendations"])
        
        with dashboard_tabs[0]:  # Trends subtab
            st.markdown('<p style="color: #000000; font-weight: 600;">Violations Over Time</p>', unsafe_allow_html=True)
            
            # Get trend data with filtering
            trend_data = get_violation_trends(current_only=show_current_only_dashboard)
            
            if not trend_data.empty:
                fig = px.line(
                    trend_data, 
                    x='Timestamp', 
                    y='Count',
                    markers=True,
                    line_shape='spline'
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#333'),
                    height=400,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis_title="Time (seconds)",
                    yaxis_title="Number of Violations"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trend data available yet.")
        
        with dashboard_tabs[1]:  # Severity Analysis
            st.markdown('<p style="color: #000000; font-weight: 600;">Violation Severity Distribution</p>', unsafe_allow_html=True)
            
            severity_data = pd.DataFrame({
                "Severity": ["High", "Medium", "Low"],
                "Count": [violation_stats['high'], violation_stats['medium'], violation_stats['low']]
            })
            
            if sum(severity_data['Count']) > 0:
                fig = px.pie(
                    severity_data, 
                    values='Count', 
                    names='Severity',
                    color='Severity',
                    color_discrete_map={
                        "High": '#000000',      # Black for high
                        "Medium": '#888888',    # Medium grey
                        "Low": '#DDDDDD'        # Light grey
                    },
                    hole=0.4
                )
                
                fig.update_traces(
                    textfont=dict(color="#000000", size=14),  # Make text on pie slices black
                    insidetextfont=dict(color="#FFFFFF")  # White text inside dark slices
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#000000'),  # Black font for all text
                    height=400,
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(
                        font=dict(color="#000000", size=14)  # Black legend text
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No severity data available yet.")
        
        with dashboard_tabs[2]:  # Recommendations
            st.markdown('<p style="color: #000000; font-weight: 600;">Top Safety Recommendations</p>', unsafe_allow_html=True)
            
            # Get recommendations from database
            cursor = conn.cursor()
            cursor.execute("""
            SELECT 
                recommendation,
                COUNT(*) as count
            FROM 
                violations 
            WHERE 
                recommendation IS NOT NULL AND recommendation != ''
            GROUP BY 
                recommendation
            ORDER BY 
                count DESC
            LIMIT 10
            """)
            
            recommendations = cursor.fetchall()
            
            if recommendations:
                for i, (recommendation, count) in enumerate(recommendations, 1):
                    st.markdown(f"""
                    <div style="background-color: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem; border: 1px solid #e5e7eb;">
                        <div style="font-weight: 600; color: #000000; margin-bottom: 0.5rem;">Recommendation #{i}</div>
                        <div style="margin-bottom: 0.5rem; color: #000000;">{recommendation}</div>
                        <div style="color: #000000; font-size: 0.8rem;">Found in {count} violation{'' if count == 1 else 's'}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No safety recommendations available yet.")

# Display placeholder when no videos are uploaded (update text colors)
elif not uploaded_files:
    st.markdown("""
    <div style="background-color: #f8f8f8; border-radius: 8px; padding: 2rem; text-align: center; border: 1px dashed #cccccc; margin-top: 1rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📤</div>
        <p style="font-size: 1.2rem; margin-bottom: 1rem; color: #000000;">Upload construction site videos to begin analysis</p>
        <p style="color: #000000; font-size: 0.9rem;">We'll analyze the videos for safety violations and generate a detailed report</p>
    </div>
    
    <div style="background-color: #f8f8f8; padding: 1.5rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #cccccc;">
        <p style="color: #000000; font-weight: 600; margin-bottom: 0.8rem;">💡 Tip</p>
        <p style="margin-bottom: 1rem; color: #000000;">Upload your construction videos for comprehensive safety violation detection.</p>
        <p style="color: #000000; font-size: 0.9rem;">Our AI system will detect:</p>
        <ul style="color: #000000; font-size: 0.9rem; margin-left: 1.5rem;">
            <li>Workers without proper PPE (hard hats, vests, etc.)</li>
            <li>Dangerous positioning on scaffolding</li>
            <li>Improper handling of equipment and materials</li>
            <li>Blocked emergency exits and pathways</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Updated footer with black text
st.markdown("""
<div style="text-align: center; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; color: #000000; font-size: 0.8rem;">
    <p>Construction Safety Monitor</p>
    <p>Powered by AI Vision Analytics</p>
</div>
""", unsafe_allow_html=True)

# Clean up on session end
def cleanup():
    try:
        # Close database connection
        conn.close()
        
        # Remove temporary files if needed
        # (temp files should be auto-cleaned, but we could add additional cleanup logic here)
    except Exception as e:
        pass

# Register cleanup function
import atexit
atexit.register(cleanup)

# Add this somewhere in your interface, perhaps in a settings section
with st.container():
    st.markdown("### Database Management", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        confirm = st.checkbox("I understand this will delete all previous analysis results", key="confirm_delete")
    
    with col2:
        if st.button("Clear All Previous Results", type="primary", disabled=not confirm):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM violations")
            cursor.execute("DELETE FROM frames")
            cursor.execute("DELETE FROM videos")
            cursor.execute("DELETE FROM worker_identifiers")
            cursor.execute("DELETE FROM worker_violations")
            cursor.execute("DELETE FROM query_answers")
            conn.commit()
            st.success("Database cleared successfully")