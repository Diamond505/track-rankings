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

def process_current_seasonal_standings(input_folder, output_file, season_start_date=None, season_end_date=None):
    """
    Process race results for championship standings.
    
    Args:
        input_folder: Folder containing JSON result files
        output_file: Output CSV file path
        season_start_date: Optional start date (format: YYMMDD, e.g., '251001' for Oct 1, 2025)
        season_end_date: Optional end date (format: YYMMDD)
    """
    print(f"Scanning folder for RACE results: {input_folder}")
    if season_start_date or season_end_date:
        print(f"Season filter: {season_start_date or 'start'} to {season_end_date or 'end'}")
    
    search_pattern = os.path.join(input_folder, "*.json")
    files = glob.glob(search_pattern)
    
    if not files:
        print("No JSON files found.")
        return

    print(f"Found {len(files)} JSON files to process.")
    
    driver_stats = {}
    skipped_races = 0
    processed_races = 0
    MINIMUM_PARTICIPANTS = 10  # Minimum drivers for a race to count as a league race

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
        
        # Check if this is a MAIN RACE file (ends with _R.json ONLY, not _R2.json)
        # File format: YYMMDD_HHMMSS_<SESSION>.json
        if not re.search(r'_R\.json$', filename, re.IGNORECASE):
            # Skip non-race files (FP, Q, R2, etc.)
            continue
        
        # Check date range if specified
        if season_start_date or season_end_date:
            # Extract date from filename (first 6 characters: YYMMDD)
            file_date = filename[:6]
            if season_start_date and file_date < season_start_date:
                continue
            if season_end_date and file_date > season_end_date:
                continue
        
        data = load_json_from_file(file_path)
        
        if not data:
            continue
            
        session_result = data.get('sessionResult', {})
        leaderboard = session_result.get('leaderBoardLines', [])
        
        # Check if this race has enough participants to be a league race
        participant_count = len(leaderboard)
        if participant_count < MINIMUM_PARTICIPANTS:
            print(f"Skipping {filename}: Only {participant_count} participants (minimum {MINIMUM_PARTICIPANTS} required)")
            skipped_races += 1
            continue
        
        print(f"Processing {filename}: {participant_count} participants")
        processed_races += 1
        
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
            
            # GT3 Class Filter: Only process GT3 cars
            # ACC carModel IDs: GT3 cars are typically 0-50, GT4 cars are 50+
            # If carModel is not in GT3 range, skip this driver
            try:
                car_model_num = int(car_model_id)
                if car_model_num > 50:  # Not a GT3 car (likely GT4 or other class)
                    continue
            except (ValueError, TypeError):
                # If we can't determine car model, skip it
                continue
            
            stats = get_entry(steam_id, f_name, l_name, 'GT3')
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
        print(f"\n{'='*60}")
        print(f"Successfully generated current standings with {len(df)} drivers.")
        print(f"Processed {processed_races} league races (10+ participants)")
        print(f"Skipped {skipped_races} non-league races (< 10 participants)")
        print(f"Saved to: {output_file}")
        print(f"{'='*60}")
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
    
    # Ask user for season date range (optional)
    print("\n" + "="*60)
    print("SEASON DATE RANGE (Optional)")
    print("="*60)
    print("Leave blank to process ALL race files.")
    print("Format: YYMMDD (e.g., 260101 for Jan 1, 2026)")
    print()
    
    season_start = input("Season start date (YYMMDD) or press Enter to skip: ").strip()
    season_end = input("Season end date (YYMMDD) or press Enter to skip: ").strip()
    
    # Validate format
    if season_start and len(season_start) != 6:
        print("Invalid start date format. Processing all files.")
        season_start = None
    if season_end and len(season_end) != 6:
        print("Invalid end date format. Processing all files.")
        season_end = None
    
    process_current_seasonal_standings(
        INPUT_DIR, 
        OUTPUT_FILE,
        season_start_date=season_start if season_start else None,
        season_end_date=season_end if season_end else None
    )
