import os
import json
import base64
import argparse
import requests
from dotenv import load_dotenv
import time
from datetime import datetime

# Load environment variables
load_dotenv()

def encode_image(image_path):
    """Encode an image file to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def create_analysis_prompt(custom_queries=None, safety_checks=None):
    """Create a dynamic analysis prompt based on configuration"""
    
    # Default safety checks if none provided
    if not safety_checks:
        safety_checks = {
            "ppe": True,
            "dangerous_positions": True,
            "improper_equipment": True,
            "blocked_exits": True,
            "other_hazards": True
        }
    
    # Build the base prompt
    base_prompt = "Analyze this construction site image for safety violations.\nCheck for:"
    
    if safety_checks.get("ppe", True):
        base_prompt += "\n1. Missing PPE (hard hats, vests, gloves, harnesses)"
    if safety_checks.get("dangerous_positions", True):
        base_prompt += "\n2. Workers in dangerous positions"
    if safety_checks.get("improper_equipment", True):
        base_prompt += "\n3. Improper equipment usage"
    if safety_checks.get("blocked_exits", True):
        base_prompt += "\n4. Blocked emergency exits or pathways"
    if safety_checks.get("other_hazards", True):
        base_prompt += "\n5. Any other safety hazards"
    
    # Format requirements
    base_prompt += """
    
    Format your response as JSON with these fields:
    - violations: [list of specific violations]
    - locations: [descriptions of where in the image]
    - severity: [low/medium/high for each violation]
    - recommendations: [how to fix each issue]
    - worker_count: [integer number of workers visible in this frame]
    - worker_positions: [descriptions of worker positions to help with tracking]
    
    If there are no violations visible, return an empty violations list.
    """
    
    # Add custom queries if provided
    if custom_queries and len(custom_queries) > 0:
        base_prompt += "\n\nAdditionally, please answer these specific questions about the image:\n"
        for i, query in enumerate(custom_queries):
            base_prompt += f"{i+1}. {query}\n"
        
        base_prompt += """
        For each question, provide a direct answer in this format:
        - query_answers: [
            {
                "question": "the original question",
                "answer": "a direct answer to the question",
                "confidence": "high/medium/low"
            }
        ]
        """
    
    # Add worker tracking information
    base_prompt += """
    For each worker with a violation:
    - Assign a unique ID based on their appearance (e.g., "worker_red_helmet_1", "worker_blue_shirt_no_helmet")
    - Include distinctive features that would identify the same worker in different frames
    
    Format this information in your response as:
    - worker_identifiers: [
        {
            "worker_id": "unique identifier",
            "features": "description of distinctive features", 
            "violations": ["list of violation indices that apply to this worker"]
        }
    ]
    """
    
    return base_prompt

def analyze_with_ai(image_path, api_key, prompt=None, custom_queries=None):
    """Analyze an image with OpenAI Vision"""
    if not prompt:
        prompt = create_analysis_prompt(custom_queries)
        
    base64_image = encode_image(image_path)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 1500
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for error status codes
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON from response
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].strip()
        else:
            json_str = content
        
        # Parse JSON and add metadata
        analysis_result = json.loads(json_str)
        analysis_result["image_path"] = image_path
        analysis_result["timestamp"] = datetime.now().isoformat()
        
        return analysis_result
        
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        return {"error": str(e), "image_path": image_path}
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response: {content}")
        return {"error": f"JSON parse error: {str(e)}", "raw_response": content, "image_path": image_path}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e), "image_path": image_path}

def analyze_frames_in_directory(frames_dir, output_dir, api_key, custom_queries=None, 
                               safety_checks=None, batch_size=10, progress_callback=None):
    """Analyze all frames in a directory"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of image files
    image_files = []
    for root, _, files in os.walk(frames_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(root, file))
    
    total_frames = len(image_files)
    print(f"Found {total_frames} images to analyze")
    
    # Initialize progress tracking
    if progress_callback:
        progress_callback(0, total_frames, 0)
    
    # Create analysis prompt once for all images
    prompt = create_analysis_prompt(custom_queries, safety_checks)
    
    # Process images in batches to show progress
    for i, image_path in enumerate(image_files):
        print(f"Processing image {i+1}/{total_frames}: {image_path}")
        
        # Get relative path for organizing results
        rel_path = os.path.relpath(image_path, frames_dir)
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Create output directory structure
        result_dir = os.path.join(output_dir, os.path.dirname(rel_path))
        os.makedirs(result_dir, exist_ok=True)
        
        # Analyze image
        result = analyze_with_ai(image_path, api_key, prompt)
        
        # Save result
        output_file = os.path.join(result_dir, f"{image_name}_analysis.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"Saved analysis to {output_file}")
        
        # Update progress
        if progress_callback:
            progress_callback(i+1, total_frames, (i+1)/total_frames)
        
        # Avoid rate limiting
        time.sleep(1)
    
    print(f"Completed analysis of {total_frames} images")
    return total_frames

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze frames for construction safety violations")
    parser.add_argument("--input", default="data/frames", help="Input frames directory")
    parser.add_argument("--output", default="results", help="Output results directory")
    parser.add_argument("--queries", nargs="+", help="Custom queries to include in analysis")
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    analyze_frames_in_directory(args.input, args.output, api_key, custom_queries=args.queries)