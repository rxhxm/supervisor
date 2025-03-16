import cv2
import os
import argparse
from datetime import datetime

def extract_frames(video_path, output_dir, interval_seconds=2, progress_callback=None):
    """
    Extracts frames from a video at specified intervals
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save extracted frames
        interval_seconds: Extract a frame every X seconds
        progress_callback: Function to call with progress updates
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video file name without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Create a subdirectory for this video
    video_output_dir = os.path.join(output_dir, video_name)
    os.makedirs(video_output_dir, exist_ok=True)
    
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Error: Could not open video {video_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    
    print(f"Video: {video_name}")
    print(f"FPS: {fps}, Duration: {duration:.2f} seconds")
    
    # Calculate frame interval
    frame_interval = int(fps * interval_seconds)
    
    # Calculate approximate expected frames
    expected_frames = int(duration / interval_seconds)
    
    # Initialize progress tracking
    if progress_callback:
        progress_callback(0, expected_frames, 0)
    
    frame_num = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Save frame at intervals
        if frame_num % frame_interval == 0:
            # Calculate timestamp
            timestamp = frame_num / fps
            minutes = int(timestamp / 60)
            seconds = int(timestamp % 60)
            
            # Format the output filename
            output_filename = f"{video_name}_frame_{saved_count:04d}_{minutes:02d}m{seconds:02d}s.jpg"
            output_path = os.path.join(video_output_dir, output_filename)
            
            # Save the frame
            cv2.imwrite(output_path, frame)
            saved_count += 1
            
            print(f"Saved frame at {minutes:02d}:{seconds:02d} to {output_filename}")
            
            # Update progress
            if progress_callback:
                progress_callback(saved_count, expected_frames, min(saved_count/expected_frames, 1.0))
        
        frame_num += 1
    
    cap.release()
    print(f"Extracted {saved_count} frames from {video_name}")
    return video_output_dir

def process_videos_in_directory(input_dir, output_dir, interval_seconds=2):
    """Process all videos in a directory"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    
    videos_processed = 0
    for filename in os.listdir(input_dir):
        if any(filename.lower().endswith(ext) for ext in video_extensions):
            video_path = os.path.join(input_dir, filename)
            print(f"Processing video: {filename}")
            extract_frames(video_path, output_dir, interval_seconds)
            videos_processed += 1
    
    print(f"Completed processing {videos_processed} videos")
    return videos_processed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from videos")
    parser.add_argument("--input", default="data/videos", help="Input video directory or file")
    parser.add_argument("--output", default="data/frames", help="Output frames directory")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between frames (seconds)")
    
    args = parser.parse_args()
    
    if os.path.isdir(args.input):
        process_videos_in_directory(args.input, args.output, args.interval)
    else:
        extract_frames(args.input, args.output, args.interval)