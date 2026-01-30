import os
import glob
import json
import pandas as pd
import re

# Scoring System
# 1st-10th: 50, 45, 42, 39, 36, 33, 30, 27, 24, 21
# 11th-20th: 20, 19, 18, 17, 16, 15, 14, 13, 12, 11
# 21st-30th: 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
POINTS_MAP = {
    1: 50, 2: 45, 3: 42, 4: 39, 5: 36,
    6: 33, 7: 30, 8: 27, 9: 24, 10: 21
}
# Fill 11-30
for i in range(11, 31):
    POINTS_MAP[i] = 31 - i  # 11 -> 20, 20 -> 11, 21 -> 10, 30 -> 1

def load_json_from_file(file_path):
    """Load JSON data from a file with error handling and repair invalid JSON."""
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read().strip()
                # Basic sanitization
                content = ''.join(c for c in content if c.isprintable())
                content = re.sub(r"(?<!\\)'", "\"", content)
                content = re.sub(r"(?<=[{,])\s*([a-zA-Z0-9_]+)\s*:", r'"\1":', content)
                content = re.sub(r",\s*([\]}])", r"\1", content)
                return json.loads(content)
        except Exception as e:
            if encoding == encodings[-1]:
                print(f'Error loading JSON from {file_path}: {e}')
    return None

def process_current_seasonal_standings(input_folder, output_file):
    print(f"Scanning folder for JSON results: {input_folder}")
    
    search_pattern = os.path.join(input_folder, "*.json")
    files = glob.glob(search_pattern)
    
    if not files:
        print("No JSON files found.")
        return

    print(f"Found {len(files)} JSON files to process.")
    
    driver_stats = {}

    def get_entry(steam_id, first_name, last_name, car_class):
        steam_id = str(steam_id)
        if steam_id not in driver_stats:
            driver_stats[steam_id] = {
                'FirstName': first_name,
                'LastName': last_name,
                'Car Class': car_class,
                'TotalPoints': 0,
                'Races': 0,
                'Wins': 0
            }
        return driver_stats[steam_id]

    for file_path in files:
        filename = os.path.basename(file_path)
        data = load_json_from_file(file_path)
        
        if not data:
            continue
            
        session_result = data.get('sessionResult', {})
        leaderboard = session_result.get('leaderBoardLines', [])
        
        # Sort leaderboard by position (just in case)
        # Trusting the file order for position (standard ACC output)
        
        # Process each driver in the race
        # Note: JSON 'leaderBoardLines' are usually ordered by position for Race sessions.
        # Explicit 'position' key might be missing.
        for i, entry in enumerate(leaderboard):
            position = i + 1
            
            car_info = entry.get('car', {})
            drivers = car_info.get('drivers', [])
            if not drivers:
                continue
                
            driver_info = drivers[0]
            steam_id = driver_info.get('playerId')
            
            # Skip invalid IDs
            if not steam_id or steam_id == 'M2533274796928070':
                continue

            points = POINTS_MAP.get(position, 0)
            
            # Get driver details
            f_name = driver_info.get('firstName', '')
            l_name = driver_info.get('lastName', '')
            # Try to get class from existing sources or default
            # JSON might not have Class directly in 'car', sometimes it's external.
            # For now, we'll try to guess or leave generic if missing from JSON structure.
            # The previous scripts loaded class from an external CSV. 
            # Let's check if we can get it from the JSON.
            # Often 'carModel' matches a class.
            # For this standalone script, let's store what we have.
            car_model_id = car_info.get('carModel', '')
            # We could map model ID to class if we had the map here, 
            # but user didn't ask for class separation in scoring, just series scoring.
            
            stats = get_entry(steam_id, f_name, l_name, 'Unknown')
            stats['TotalPoints'] += points
            stats['Races'] += 1
            if position == 1:
                stats['Wins'] += 1
                
    # Convert to DataFrame
    results = []
    for steam_id, stats in driver_stats.items():
        stats['SteamId'] = steam_id
        results.append(stats)
        
    df = pd.DataFrame(results)
    
    if not df.empty:
        df = df.sort_values(['TotalPoints', 'Wins'], ascending=[False, False])
        df['Rank'] = range(1, len(df) + 1)
        
        df.to_csv(output_file, index=False, sep=';')
        print(f"Successfully generated current standings with {len(df)} drivers.")
        print(f"Saved to: {output_file}")
    else:
        print("No driver data found.")

if __name__ == "__main__":
     # Adjust paths as needed
    INPUT_DIR = "../Files/Results_json"
    OUTPUT_FILE = "../Files/Results_csv/current_standings.csv"
    
    # Check if we are running from 'Scripts' folder or root
    if not os.path.exists(INPUT_DIR):
        # Fallback for different CWD
        INPUT_DIR = "Files/Results_json"
        OUTPUT_FILE = "Files/Results_csv/current_standings.csv"
        
    process_current_seasonal_standings(INPUT_DIR, OUTPUT_FILE)
