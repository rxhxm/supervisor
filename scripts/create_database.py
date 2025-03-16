import os
import json
import sqlite3
import glob
from datetime import datetime

def create_database(db_path="database.sqlite"):
    """Create SQLite database and tables for storing analysis results"""
    
    # Connect to database (will create if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_name TEXT NOT NULL,
        filepath TEXT,
        duration_seconds INTEGER,
        frame_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id INTEGER,
        frame_number INTEGER,
        timestamp_seconds INTEGER,
        image_path TEXT,
        worker_count INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        frame_id INTEGER,
        violation_type TEXT,
        description TEXT,
        location TEXT,
        severity TEXT,
        recommendation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (frame_id) REFERENCES frames (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_identifiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        frame_id INTEGER,
        worker_id TEXT,
        features TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (frame_id) REFERENCES frames (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS worker_violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_identifier_id INTEGER,
        violation_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_identifier_id) REFERENCES worker_identifiers (id),
        FOREIGN KEY (violation_id) REFERENCES violations (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS query_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        frame_id INTEGER,
        question TEXT,
        answer TEXT,
        confidence TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (frame_id) REFERENCES frames (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Database created at {db_path}")
    return db_path

def parse_frame_info(filename):
    """Extract video name, frame number and timestamp from filename"""
    # Example: video1_frame_0001_01m30s_analysis.json
    
    try:
        base_name = os.path.basename(filename)
        if "_analysis.json" not in base_name:
            raise ValueError(f"Unexpected filename format: {base_name}")
        
        parts = base_name.replace("_analysis.json", "").split("_")
        
        # Extract video name (could be multiple parts before "frame")
        frame_index = parts.index("frame")
        video_name = "_".join(parts[:frame_index])
        
        # Extract frame number
        frame_number = int(parts[frame_index + 1])
        
        # Parse timestamp (01m30s)
        time_part = parts[frame_index + 2]
        minutes = int(time_part.split('m')[0])
        seconds = int(time_part.split('m')[1].replace('s', ''))
        timestamp_seconds = minutes * 60 + seconds
        
        return video_name, frame_number, timestamp_seconds
    except Exception as e:
        print(f"Error parsing filename {filename}: {e}")
        # Return defaults if parsing fails
        return os.path.basename(os.path.dirname(filename)), 0, 0

def import_analysis_files(db_path, results_dir):
    """Import all analysis JSON files into the database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all JSON files
    json_files = glob.glob(os.path.join(results_dir, '**', '*_analysis.json'), recursive=True)
    print(f"Found {len(json_files)} analysis files to import")
    
    # Track videos we've already added
    videos = {}
    
    for file_path in json_files:
        try:
            # Parse filename information
            video_name, frame_number, timestamp_seconds = parse_frame_info(file_path)
            
            # Get or create video record
            if video_name not in videos:
                cursor.execute("INSERT INTO videos (video_name) VALUES (?)", (video_name,))
                video_id = cursor.lastrowid
                videos[video_name] = video_id
            else:
                video_id = videos[video_name]
            
            # Load JSON data
            with open(file_path, 'r') as f:
                try:
                    analysis = json.load(f)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in {file_path}, skipping")
                    continue
            
            # Insert frame record
            cursor.execute(
                "INSERT INTO frames (video_id, frame_number, timestamp_seconds, image_path) VALUES (?, ?, ?, ?)",
                (video_id, frame_number, timestamp_seconds, analysis.get('image_path', file_path))
            )
            frame_id = cursor.lastrowid
            
            # Insert violations
            if 'violations' in analysis and analysis['violations']:
                for i, violation in enumerate(analysis['violations']):
                    # Get corresponding location, severity, recommendation
                    location = analysis.get('locations', [])[i] if i < len(analysis.get('locations', [])) else None
                    severity = analysis.get('severity', [])[i] if i < len(analysis.get('severity', [])) else None
                    recommendation = analysis.get('recommendations', [])[i] if i < len(analysis.get('recommendations', [])) else None
                    
                    # Determine violation type
                    if ':' in violation:
                        violation_type = violation.split(':')[0].strip()
                        description = violation
                    else:
                        # Try to infer type from content
                        if 'ppe' in violation.lower() or 'hard hat' in violation.lower() or 'safety gear' in violation.lower():
                            violation_type = "Missing PPE"
                        elif 'position' in violation.lower() or 'height' in violation.lower() or 'fall' in violation.lower():
                            violation_type = "Dangerous Position"
                        elif 'equipment' in violation.lower() or 'tool' in violation.lower() or 'machinery' in violation.lower():
                            violation_type = "Improper Equipment Usage"
                        elif 'exit' in violation.lower() or 'pathway' in violation.lower() or 'block' in violation.lower():
                            violation_type = "Blocked Exit/Pathway"
                        else:
                            violation_type = "Other Hazard"
                        
                        description = violation
                    
                    cursor.execute(
                        "INSERT INTO violations (frame_id, violation_type, description, location, severity, recommendation) VALUES (?, ?, ?, ?, ?, ?)",
                        (frame_id, violation_type, description, location, severity, recommendation)
                    )
                    violation_id = cursor.lastrowid
            
            # Insert worker identifiers and their violations
            if 'worker_identifiers' in analysis and analysis['worker_identifiers']:
                for worker in analysis['worker_identifiers']:
                    cursor.execute(
                        "INSERT INTO worker_identifiers (frame_id, worker_id, features) VALUES (?, ?, ?)",
                        (frame_id, worker.get('worker_id', ''), worker.get('features', ''))
                    )
                    worker_id = cursor.lastrowid
                    
                    # Link worker to violations
                    if 'violations' in worker:
                        for violation_idx in worker['violations']:
                            # Get the violation ID from the database
                            cursor.execute(
                                "SELECT id FROM violations WHERE frame_id = ? ORDER BY id LIMIT ?, 1", 
                                (frame_id, int(violation_idx) if isinstance(violation_idx, (int, str)) else 0)
                            )
                            result = cursor.fetchone()
                            if result:
                                v_id = result[0]
                                cursor.execute(
                                    "INSERT INTO worker_violations (worker_identifier_id, violation_id) VALUES (?, ?)",
                                    (worker_id, v_id)
                                )
            
            # Insert query answers
            if 'query_answers' in analysis:
                for qa in analysis['query_answers']:
                    cursor.execute(
                        "INSERT INTO query_answers (frame_id, question, answer, confidence) VALUES (?, ?, ?, ?)",
                        (frame_id, qa.get('question'), qa.get('answer'), qa.get('confidence'))
                    )
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    conn.commit()
    conn.close()
    print(f"Imported {len(json_files)} analysis files into database")
    return len(json_files)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create and populate database from analysis results")
    parser.add_argument("--results", default="results", help="Directory containing analysis results")
    parser.add_argument("--db", default="database.sqlite", help="Path for SQLite database file")
    parser.add_argument("--recreate", action="store_true", help="Recreate database even if it exists")
    
    args = parser.parse_args()
    
    if args.recreate and os.path.exists(args.db):
        os.remove(args.db)
        print(f"Deleted existing database at {args.db}")
    
    db_path = create_database(args.db)
    import_analysis_files(db_path, args.results)