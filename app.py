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

# Set page config
st.set_page_config(
    page_title="VISOR - Construction Safety Monitor",
    page_icon="🚧",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #0a192f;
        color: #e6f1ff;
    }
    
    /* Header styling */
    .header-container {
        display: flex;
        align-items: center;
        margin-bottom: 2rem;
    }
    
    .logo-container {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: radial-gradient(circle at center,
            #ffcc00 0%,
            #ff9d00 40%,
            #ff7b00 70%,
            #ff6b00 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 20px;
        box-shadow: 0 0 20px rgba(255, 204, 0, 0.5);
    }
    
    .logo-text {
        color: #0a192f;
        font-weight: bold;
        font-size: 16px;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(to right, #ffcc00, #ff6b00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Section headings */
    .section-heading {
        font-size: 1.5rem;
        color: #64ffda;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 5px;
        border-bottom: 1px solid #1d304f;
    }
    
    /* Cards styling */
    .card {
        background-color: #112240;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #1d304f;
    }
    
    /* Buttons styling */
    .primary-button {
        background-color: #ffcc00 !important;
        color: #0a192f !important;
        font-weight: bold !important;
    }
    
    /* Error message */
    .error-message {
        background-color: rgba(255, 0, 0, 0.1);
        color: #ff6b6b;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ff6b6b;
    }
    
    /* Success message */
    .success-message {
        background-color: rgba(0, 255, 0, 0.1);
        color: #64ffda;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #64ffda;
    }
    
    /* Metrics styling */
    .metric-container {
        background-color: #112240;
        border-radius: 8px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #1d304f;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffcc00;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #8892b0;
    }
    
    /* Violation card */
    .violation-card {
        background-color: #112240;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #1d304f;
    }
    
    .violation-header {
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .violation-detail {
        color: #8892b0;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
    }
    
    .severity-high {
        color: #ff6b6b;
        font-weight: 600;
    }
    
    .severity-medium {
        color: #ffcc00;
        font-weight: 600;
    }
    
    .severity-low {
        color: #64ffda;
        font-weight: 600;
    }
    
    /* Upload box */
    .upload-box {
        border: 2px dashed #1d304f;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        background-color: rgba(29, 48, 79, 0.3);
    }
    
    /* Animation elements */
    @keyframes zoom-out {
        0% { 
            transform: scale(1) translate(-50%, -50%); 
            top: 50%;
            left: 50%;
        }
        100% { 
            transform: scale(0.3) translate(0, 0); 
            top: 20px;
            right: 20px;
            left: auto;
        }
    }
    
    .safety-lens {
        position: fixed;
        width: 200vh;
        height: 200vh;
        border-radius: 50%;
        background: radial-gradient(circle at center,
            #ffcc00 0%,
            #ff9d00 40%,
            #ff7b00 70%,
            #ff6b00 100%);
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: zoom-out 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
        animation-delay: 0.5s;
    }
    
    .content {
        opacity: 0;
        animation: fade-in 0.5s ease-in forwards;
        animation-delay: 1.8s;
    }
    
    @keyframes fade-in {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    
    .lens-content {
        color: #0a192f;
        font-weight: bold;
        font-size: 10vh;
        opacity: 0;
        animation: fade-in 0.5s ease-in forwards, 
                   scale-down 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
        animation-delay: 0s, 0.5s;
    }
    
    @keyframes scale-down {
        0% { 
            transform: scale(1);
            font-size: 10vh;
        }
        100% { 
            transform: scale(0.3);
            font-size: 16px;
        }
    }
    
    /* Add to your existing styles */
    .progress-label {
        color: #64ffda;
        font-size: 0.9rem;
        margin-bottom: 0.2rem;
    }
    
    .progress-detail {
        color: #8892b0;
        font-size: 0.8rem;
        margin-top: 0.2rem;
    }
    
    .progress-container {
        background-color: rgba(29, 48, 79, 0.3);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #1d304f;
    }
    
    .stage-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 1rem;
    }
    
    .stage {
        text-align: center;
        padding: 0.5rem;
        border-radius: 4px;
        flex: 1;
        margin: 0 0.2rem;
    }
    
    .stage-active {
        background-color: rgba(100, 255, 218, 0.2);
        border: 1px solid #64ffda;
        color: #64ffda;
    }
    
    .stage-complete {
        background-color: rgba(100, 255, 218, 0.1);
        border: 1px solid #1d304f;
        color: #8892b0;
    }
    
    .stage-pending {
        background-color: transparent;
        border: 1px dashed #1d304f;
        color: #3d4550;
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

# Animation elements (shown only on the first load)
if 'animation_shown' not in st.session_state:
    st.session_state.animation_shown = True
    
    # Display the animation elements
    st.markdown("""
    <div class="safety-lens">
        <div class="lens-content">VISOR</div>
    </div>
    <div class="content">
    """, unsafe_allow_html=True)
else:
    # Skip animation if already shown
    st.markdown('<div class="content">', unsafe_allow_html=True)

# Custom header with logo
st.markdown("""
<div class="header-container">
    <div class="logo-container">
        <div class="logo-text">VISOR</div>
    </div>
    <h1 class="main-title">Construction Safety Monitor</h1>
</div>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'custom_queries' not in st.session_state:
    st.session_state.custom_queries = []
if 'videos_analyzed' not in st.session_state:
    st.session_state.videos_analyzed = False
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
if 'current_videos' not in st.session_state:
    st.session_state.current_videos = []

# Main content area
st.markdown('<div class="section-heading">Upload & Analyze Construction Videos</div>', unsafe_allow_html=True)

# Create layout with two columns
col1, col2 = st.columns([2, 1])

with col1:
    # Video upload section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Video upload widget
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload construction site videos", 
                                     type=["mp4", "avi", "mov", "mkv"], 
                                     accept_multiple_files=True)
    st.markdown('<p style="color: #8892b0; font-size: 0.8rem;">Supported formats: MP4, AVI, MOV, MKV | Max size: 200MB</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_files:
        st.success(f"Uploaded {len(uploaded_files)} video(s)")
        
        # Display video thumbnails in a grid
        video_count = len(uploaded_files)
        cols_per_row = min(3, video_count)
        
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
                        
                        # Display video thumbnail
                        st.video(temp_path)
                        st.caption(uploaded_files[i+j].name)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # API Key and Smart Query section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # API Key input
    st.markdown('<div style="margin-bottom: 1rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color: #64ffda; font-weight: 600; margin-bottom: 0.5rem;">OpenAI API Key</p>', unsafe_allow_html=True)
    api_key = st.text_input("OpenAI API Key", 
                          value=st.session_state.openai_api_key,
                          type="password",
                          help="Required for video analysis")
    
    if api_key:
        st.session_state.openai_api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Smart Query section
    st.markdown('<p style="color: #64ffda; font-weight: 600; margin-bottom: 0.5rem;">Smart Query</p>', unsafe_allow_html=True)
    st.markdown('<p style="color: #8892b0; font-size: 0.9rem;">Ask specific questions about violations you want to detect:</p>', unsafe_allow_html=True)
    
    query_input = st.text_area("Smart Query", 
                              placeholder="Example: 'Find workers without harnesses near edges'",
                              height=80, 
                              label_visibility="collapsed")
    
    if query_input and st.button("Add Query", type="primary"):
        st.markdown(f'<div style="background-color: rgba(100, 255, 218, 0.1); padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem;">Added: "{query_input}"</div>', unsafe_allow_html=True)
        
        # Add query to session state
        if query_input not in st.session_state.custom_queries:
            st.session_state.custom_queries.append(query_input)
    
    # Display current queries
    if st.session_state.custom_queries:
        st.markdown('<div style="margin-top: 1rem;">', unsafe_allow_html=True)
        st.markdown('<p style="color: #8892b0;">Your queries:</p>', unsafe_allow_html=True)
        
        for i, query in enumerate(st.session_state.custom_queries):
            cols = st.columns([9, 1])
            with cols[0]:
                st.markdown(f'<div style="font-size: 0.9rem; padding: 0.3rem;">{i+1}. {query[:40]}{"..." if len(query) > 40 else ""}</div>', unsafe_allow_html=True)
            with cols[1]:
                if st.button("×", key=f"del_{i}"):
                    st.session_state.custom_queries.pop(i)
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Analysis Configuration section
st.markdown('<div class="section-heading">Analysis Configuration</div>', unsafe_allow_html=True)

with st.expander("Configure Detection Settings", expanded=True):
    config_cols = st.columns(2)
    
    with config_cols[0]:
        st.markdown('<p style="color: #64ffda; font-weight: 600;">Safety Violations to Detect</p>', unsafe_allow_html=True)
        
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
        st.markdown('<p style="color: #64ffda; font-weight: 600;">Processing Options</p>', unsafe_allow_html=True)
        
        # Frame extraction settings
        frame_interval = st.slider("Extract frames every ___ seconds", 1, 10, 2)
        
        # Worker tracking
        enable_tracking = st.checkbox("Enable worker tracking and identification", value=True)
        
        # If we have custom queries, show them
        if st.session_state.custom_queries:
            st.markdown('<p style="color: #64ffda; font-weight: 600; margin-top: 1rem;">Your Custom Queries</p>', unsafe_allow_html=True)
            for query in st.session_state.custom_queries:
                st.markdown(f'<div style="color: #8892b0; font-size: 0.9rem; margin-bottom: 0.3rem;">• {query}</div>', unsafe_allow_html=True)

# Analysis Button
if uploaded_files:
    st.markdown('<div style="margin-top: 1.5rem;">', unsafe_allow_html=True)
    
    process_button = st.button("Start Safety Analysis", type="primary", use_container_width=True)
    
    if process_button:
        # Reset current videos list at the start of a new analysis
        st.session_state.current_videos = []
        
        # Check for API key
        if not st.session_state.openai_api_key:
            st.error("OpenAI API Key is required for video analysis. Please enter your API key.")
        else:
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
                
    st.markdown('</div>', unsafe_allow_html=True)

# Results section - show if we have analyzed videos or have data in the database
violation_stats = get_violation_stats()

if violation_stats['total'] > 0 or st.session_state.videos_analyzed:
    st.markdown('<div class="section-heading">Analysis Results</div>', unsafe_allow_html=True)
    
    # Create tabs for different views of the data
    tabs = st.tabs(["Summary", "Violations Gallery", "Custom Query Results", "Dashboard"])
    
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
                <div class="metric-value">{violation_stats['total']}</div>
                <div class="metric-label">Total Violations</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[1]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{violation_stats['high']}</div>
                <div class="metric-label">High Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[2]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{violation_stats['medium']}</div>
                <div class="metric-label">Medium Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with metric_cols[3]:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{violation_stats['low']}</div>
                <div class="metric-label">Low Severity</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Violation type breakdown
        st.markdown('<p style="color: #64ffda; font-weight: 600; margin-top: 1.5rem;">Violation Type Breakdown</p>', unsafe_allow_html=True)
        
        if violation_stats['types']:
            chart_data = pd.DataFrame(violation_stats['types'], columns=["Violation Type", "Count"])
            
            fig = px.bar(
                chart_data,
                x="Violation Type",
                y="Count",
                color="Count",
                color_continuous_scale=px.colors.sequential.Viridis,
                text="Count"
            )
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e6f1ff'),
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                coloraxis_showscale=False
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
                            
                            with st.expander(f"{violation['severity'].upper() if violation['severity'] else 'UNKNOWN'} - {violation['desc'][:40]}...", expanded=False):
                                # Show violation image if available
                                if violation['image_path'] and os.path.exists(violation['image_path']):
                                    try:
                                        st.image(Image.open(violation['image_path']), use_column_width=True)
                                    except Exception as e:
                                        st.warning(f"Could not display image: {e}")
                                
                                # Violation details
                                st.markdown(f"""
                                <div class="violation-card">
                                    <div class="violation-detail"><strong>Type:</strong> {violation['type'] or 'Unknown'}</div>
                                    <div class="violation-detail"><strong>Description:</strong> {violation['desc']}</div>
                                    <div class="violation-detail"><strong>Location:</strong> {violation['location'] or 'Not specified'}</div>
                                    <div class="violation-detail"><strong>Severity:</strong> <span class="{severity_class}">{(violation['severity'] or 'Unknown').upper()}</span></div>
                                    <div class="violation-detail"><strong>Recommendation:</strong> {violation['recommendation'] or 'No recommendation available'}</div>
                                </div>
                                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No violations found matching your filters. Try changing the filters or analyze more videos.")
    
    with tabs[2]:  # Custom Query Results
        if st.session_state.custom_queries:
            for i, query in enumerate(st.session_state.custom_queries):
                st.markdown(f'<p style="color: #64ffda; font-weight: 600; margin-top: 1rem;">Results for: "{query}"</p>', unsafe_allow_html=True)
                
                # Search for violations matching this query
                matching_violations = search_violations_by_query(query)
                
                if matching_violations:
                    st.markdown(f"""
                    <div style="background-color: rgba(100, 255, 218, 0.1); padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem;">
                        <p style="color: #8892b0; font-size: 0.9rem;">Found {len(matching_violations)} matches for this query</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for violation in matching_violations:
                        severity_class = f"severity-{violation['severity']}" if violation['severity'] else ""
                        
                        st.markdown(f"""
                        <div class="violation-card">
                            <div class="violation-header">{violation["desc"]}</div>
                            <div class="violation-detail"><strong>Type:</strong> {violation["type"] or 'Unknown'}</div>
                            <div class="violation-detail"><strong>Location:</strong> {violation["location"] or 'Not specified'}</div>
                            <div class="violation-detail"><strong>Severity:</strong> <span class="{severity_class}">{(violation['severity'] or 'Unknown').upper()}</span></div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show image if available
                        if violation['image_path'] and os.path.exists(violation['image_path']):
                            try:
                                st.image(Image.open(violation['image_path']), width=400)
                            except Exception:
                                st.warning("Could not display image")
                else:
                    st.info(f"No violations found matching query: '{query}'")
        else:
            st.info("No custom queries were provided. Add queries in the Smart Query section to see targeted results.")
    
    with tabs[3]:  # Dashboard tab
        show_current_only_dashboard = st.checkbox("Show current video results only", value=True, key="dashboard_filter")
        
        # Create subtabs for the dashboard
        dashboard_tabs = st.tabs(["Trends", "Severity Analysis", "Recommendations"])
        
        with dashboard_tabs[0]:  # Trends subtab
            st.markdown('<p style="color: #64ffda; font-weight: 600;">Violations Over Time</p>', unsafe_allow_html=True)
            
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
                    font=dict(color='#e6f1ff'),
                    height=400,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis_title="Time (seconds)",
                    yaxis_title="Number of Violations"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No trend data available yet.")
        
        with dashboard_tabs[1]:  # Severity Analysis
            st.markdown('<p style="color: #64ffda; font-weight: 600;">Violation Severity Distribution</p>', unsafe_allow_html=True)
            
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
                        "High": '#ff6b6b', 
                        "Medium": '#ffcc00', 
                        "Low": '#64ffda'
                    },
                    hole=0.4
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e6f1ff'),
                    height=400,
                    margin=dict(l=20, r=20, t=30, b=20)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No severity data available yet.")
        
        with dashboard_tabs[2]:  # Recommendations
            st.markdown('<p style="color: #64ffda; font-weight: 600;">Top Safety Recommendations</p>', unsafe_allow_html=True)
            
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
                    <div style="background-color: #112240; padding: 1rem; border-radius: 8px; margin-bottom: 0.8rem; border: 1px solid #1d304f;">
                        <div style="font-weight: 600; color: #64ffda; margin-bottom: 0.5rem;">Recommendation #{i}</div>
                        <div style="margin-bottom: 0.5rem;">{recommendation}</div>
                        <div style="color: #8892b0; font-size: 0.8rem;">Found in {count} violation{'' if count == 1 else 's'}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No safety recommendations available yet.")

# Display placeholder when no videos are uploaded
elif not uploaded_files:
    st.markdown("""
    <div style="background-color: rgba(29, 48, 79, 0.3); border-radius: 8px; padding: 2rem; text-align: center; border: 1px dashed #1d304f; margin-top: 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📤</div>
        <p style="font-size: 1.2rem; margin-bottom: 1rem;">Upload construction site videos to begin analysis</p>
        <p style="color: #8892b0; font-size: 0.9rem;">We'll analyze the videos for safety violations and generate a detailed report</p>
    </div>
          
    <div style="background-color: #112240; padding: 1.5rem; border-radius: 8px; margin-top: 2rem; border: 1px solid #1d304f;">
        <p style="color: #64ffda; font-weight: 600; margin-bottom: 0.8rem;">💡 Pro Tip</p>
        <p style="margin-bottom: 1rem;">Use the Smart Query feature to specify exactly what safety violations you're looking for.</p>
        <p style="color: #8892b0; font-size: 0.9rem;">Example queries:</p>
        <ul style="color: #8892b0; font-size: 0.9rem; margin-left: 1.5rem;">
            <li>Find workers on scaffolding without proper fall protection</li>
            <li>Check for missing hard hats in active construction areas</li>
            <li>Identify improper handling of hazardous materials</li>
            <li>Detect workers operating machinery without proper clearance</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Footer section
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #1d304f; color: #8892b0; font-size: 0.8rem;">
    <p>VISOR - Construction Site Safety Monitor</p>
    <p>Powered by AI Vision Analytics</p>
</div>
</div>  <!-- Closing the "content" div from the animation -->
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
if st.button("Clear All Previous Results"):
    # Ask for confirmation
    confirm = st.checkbox("I understand this will delete all previous analysis results")
    if confirm:
        # Delete all data
        cursor = conn.cursor()
        cursor.execute("DELETE FROM violations")
        cursor.execute("DELETE FROM frames")
        cursor.execute("DELETE FROM videos")
        cursor.execute("DELETE FROM worker_identifiers")
        cursor.execute("DELETE FROM worker_violations")
        cursor.execute("DELETE FROM query_answers")
        conn.commit()
        st.success("Database cleared successfully")