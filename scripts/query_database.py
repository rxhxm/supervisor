import sqlite3
import json
import argparse
import pandas as pd
import os
from datetime import datetime

def connect_db(db_path="database.sqlite"):
    """Connect to the SQLite database"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")
    return sqlite3.connect(db_path)

def get_violation_stats(conn):
    """Get overall violation statistics"""
    cursor = conn.cursor()
    
    # Count total violations
    cursor.execute("SELECT COUNT(*) FROM violations")
    total_violations = cursor.fetchone()[0]
    
    # Count violations by type
    cursor.execute("""
    SELECT violation_type, COUNT(*) as count
    FROM violations
    GROUP BY violation_type
    ORDER BY count DESC
    """)
    violation_types = cursor.fetchall()
    
    # Count violations by severity
    cursor.execute("""
    SELECT severity, COUNT(*) as count
    FROM violations
    GROUP BY severity
    ORDER BY 
        CASE severity
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
        END
    """)
    severity_counts = cursor.fetchall()
    
    # Frames with violations
    cursor.execute("""
    SELECT COUNT(DISTINCT frame_id) 
    FROM violations
    """)
    frames_with_violations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM frames")
    total_frames = cursor.fetchone()[0]
    
    return {
        "total_violations": total_violations,
        "violation_types": violation_types,
        "severity_counts": severity_counts,
        "frames_with_violations": frames_with_violations,
        "total_frames": total_frames,
        "violation_rate": (frames_with_violations/total_frames*100) if total_frames > 0 else 0
    }

def find_worst_frames(conn, limit=5):
    """Find frames with the most violations"""
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT 
        v.video_name, 
        f.frame_number, 
        COUNT(*) as violation_count,
        f.image_path,
        f.timestamp_seconds
    FROM 
        violations viol
        JOIN frames f ON viol.frame_id = f.id
        JOIN videos v ON f.video_id = v.id
    GROUP BY 
        f.id
    ORDER BY 
        violation_count DESC
    LIMIT ?
    """, (limit,))
    
    return cursor.fetchall()

def get_violation_trends(conn):
    """Get violation trends over time"""
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        f.timestamp_seconds,
        COUNT(v.id) as violation_count
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
    GROUP BY 
        f.timestamp_seconds
    ORDER BY 
        f.timestamp_seconds
    """)
    
    results = cursor.fetchall()
    return pd.DataFrame(results, columns=['Timestamp', 'Count']) if results else None

def get_violations_by_filter(conn, violation_type=None, severity=None, limit=50):
    """Get violations filtered by type and/or severity"""
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
        f.timestamp_seconds,
        vid.video_name
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
        JOIN videos vid ON f.video_id = vid.id
    """
    
    conditions = []
    params = []
    
    if violation_type:
        conditions.append("v.violation_type = ?")
        params.append(violation_type)
    
    if severity:
        conditions.append("v.severity = ?")
        params.append(severity.lower())
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY v.id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    return cursor.fetchall()

def search_query_answers(conn, search_text, limit=20):
    """Search through custom query answers"""
    cursor = conn.cursor()
    
    query = """
    SELECT
        q.question,
        q.answer,
        q.confidence,
        f.image_path,
        vid.video_name,
        f.timestamp_seconds
    FROM
        query_answers q
        JOIN frames f ON q.frame_id = f.id
        JOIN videos vid ON f.video_id = vid.id
    WHERE
        q.question LIKE ? OR
        q.answer LIKE ?
    ORDER BY
        q.id DESC
    LIMIT ?
    """
    
    search_pattern = f"%{search_text}%"
    cursor.execute(query, (search_pattern, search_pattern, limit))
    return cursor.fetchall()

def export_violations_report(conn, output_file="violations_report.json"):
    """Export violations data to JSON file"""
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
        f.timestamp_seconds,
        vid.video_name,
        f.frame_number
    FROM 
        violations v
        JOIN frames f ON v.frame_id = f.id
        JOIN videos vid ON f.video_id = vid.id
    ORDER BY
        vid.video_name,
        f.timestamp_seconds
    """
    
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    
    # Convert to list of dictionaries
    violations = []
    for row in results:
        violation = dict(zip(columns, row))
        violations.append(violation)
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump({"violations": violations, "exported_at": datetime.now().isoformat()}, f, indent=2)
    
    print(f"Exported {len(violations)} violations to {output_file}")
    return len(violations)

def main():
    parser = argparse.ArgumentParser(description="Query the safety violations database")
    parser.add_argument("--db", default="database.sqlite", help="Path to SQLite database file")
    parser.add_argument("--stats", action="store_true", help="Show violation statistics")
    parser.add_argument("--worst", type=int, default=5, help="Show worst frames with most violations")
    parser.add_argument("--type", help="Filter violations by type")
    parser.add_argument("--severity", choices=["high", "medium", "low"], help="Filter violations by severity")
    parser.add_argument("--search", help="Search text in custom query answers")
    parser.add_argument("--export", help="Export violations to JSON file")
    
    args = parser.parse_args()
    
    try:
        conn = connect_db(args.db)
        
        if args.stats:
            stats = get_violation_stats(conn)
            print("\n=== Violation Statistics ===")
            print(f"Total violations: {stats['total_violations']}")
            
            print("\n=== Violation Types ===")
            for vtype, count in stats['violation_types']:
                print(f"{vtype}: {count} violations")
            
            print("\n=== Severity Breakdown ===")
            for severity, count in stats['severity_counts']:
                print(f"{severity}: {count} violations")
            
            print(f"\nFrames with violations: {stats['frames_with_violations']}/{stats['total_frames']} ({stats['violation_rate']:.1f}%)")
        
        if args.worst:
            worst_frames = find_worst_frames(conn, args.worst)
            print("\n=== Worst Frames ===")
            for video, frame, count, path, timestamp in worst_frames:
                mins = timestamp // 60
                secs = timestamp % 60
                print(f"{video} frame {frame} at {mins:02d}:{secs:02d}: {count} violations - {path}")
        
        if args.type or args.severity:
            violations = get_violations_by_filter(conn, args.type, args.severity)
            print(f"\n=== Filtered Violations ({len(violations)} results) ===")
            for i, v in enumerate(violations[:10]):  # Show just the first 10
                print(f"{i+1}. {v[4]} - {v[1]} ({v[3].upper()} severity)")
                print(f"   Location: {v[2]}")
                if v[5]:
                    print(f"   Recommendation: {v[5]}")
                print()
            
            if len(violations) > 10:
                print(f"... and {len(violations) - 10} more violations")
        
        if args.search:
            results = search_query_answers(conn, args.search)
            print(f"\n=== Search Results for '{args.search}' ({len(results)} matches) ===")
            for i, (question, answer, confidence, image, video, timestamp) in enumerate(results):
                mins = timestamp // 60
                secs = timestamp % 60
                print(f"{i+1}. Question: {question}")
                print(f"   Answer: {answer}")
                print(f"   Confidence: {confidence}")
                print(f"   Source: {video} at {mins:02d}:{secs:02d}")
                print()
        
        if args.export:
            count = export_violations_report(conn, args.export)
            print(f"Exported {count} violations to {args.export}")
        
        if not any([args.stats, args.worst, args.type, args.severity, args.search, args.export]):
            # If no specific query requested, show basic stats
            stats = get_violation_stats(conn)
            print("\n=== Overview ===")
            print(f"Total violations: {stats['total_violations']}")
            print(f"Videos analyzed: {len(set([v[0] for v in stats['violation_types']]))}")
            print(f"Frames analyzed: {stats['total_frames']}")
            print("\nUse --help to see available query options")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()