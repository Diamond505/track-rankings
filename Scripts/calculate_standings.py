import os
import glob
import pandas as pd

def calculate_s16_standings(input_folder, output_file):
    print(f"Scanning folder for S16 results: {input_folder}")
    
    search_pattern = os.path.join(input_folder, "*_results.csv")
    files = glob.glob(search_pattern)
    
    if not files:
        print("No files found matching '*_results.csv'")
        return

    print(f"Found {len(files)} files to process.")
    
    # Structure: {steam_id: {'LastName': name, 'Participation': 0, 'TrackRecords': 0, 'KingBonus': 0, 'TotalPoints': 0}}
    driver_stats = {}
    driver_wins_count = {} # To track King Bonus (most 1st places)

    def get_entry(steam_id, last_name):
        steam_id = str(steam_id)
        if steam_id not in driver_stats:
            driver_stats[steam_id] = {
                'LastName': last_name,
                'Participation': 0,
                'TrackRecords': 0,
                'KingBonus': 0,
                'TotalPoints': 0
            }
            driver_wins_count[steam_id] = 0
        return driver_stats[steam_id]

    # 1. Process each Track File
    for file_path in files:
        filename = os.path.basename(file_path)
        track_name = filename.replace("_results.csv", "").replace("_", " ").title()
        
        try:
            # Try reading with semicolon first
            df = pd.read_csv(file_path, delimiter=';')
            
            # Check if parsing worked (if only 1 column, likely wrong delimiter)
            if len(df.columns) < 2:
                df = pd.read_csv(file_path, delimiter=',')
            
            # Ensure required columns exist
            if 'Best lap (ms)' not in df.columns or 'SteamId' not in df.columns:
                print(f"Skipping {filename}: Missing required columns.")
                continue

            # normalize columns
            df.columns = df.columns.str.strip()
            
            # --- Rule 1: Participation (10 pts per file) ---
            # Unique drivers in this file get points
            for _, row in df.iterrows():
                get_entry(row['SteamId'], row['LastName'])['Participation'] += 10

            # --- Rule 2: Track Records (3-2-1 pts per Class) ---
            # We need to group by Class first!
            if 'Class' in df.columns:
                class_col = 'Class'
            elif 'Car Class' in df.columns:
                class_col = 'Car Class'
            else:
                class_col = None

            if class_col:
                groups = df.groupby(class_col)
            else:
                groups = [('All', df)]

            for class_name, group in groups:
                 # Sort by Best lap (ms)
                # Filter valid laps
                valid_laps = group[group['Best lap (ms)'] < 2147483647].copy()
                valid_laps = valid_laps.sort_values('Best lap (ms)')
                
                # Keep best time per driver (in case of duplicates, though result files usually unique per driver)
                valid_laps = valid_laps.drop_duplicates(subset=['SteamId'])
                
                top_3 = valid_laps.head(3)
                points_dist = [3, 2, 1]
                
                for i, (idx, row) in enumerate(top_3.iterrows()):
                    entry = get_entry(row['SteamId'], row['LastName'])
                    entry['TrackRecords'] += points_dist[i]
                    
                    # Count for King Bonus (1st place only)
                    if i == 0:
                        driver_wins_count[str(row['SteamId'])] += 1
                        
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # --- Rule 3: King Bonus (1 pt) ---
    max_wins = 0
    for count in driver_wins_count.values():
        if count > max_wins:
            max_wins = count
            
    if max_wins > 0:
        for steam_id, count in driver_wins_count.items():
            if count == max_wins:
                # Add to stats
                if steam_id in driver_stats:
                    driver_stats[steam_id]['KingBonus'] += 1

    # --- Final Compilation ---
    results = []
    for steam_id, stats in driver_stats.items():
        stats['TotalPoints'] = stats['Participation'] + stats['TrackRecords'] + stats['KingBonus']
        stats['SteamId'] = steam_id
        results.append(stats)
        
    final_df = pd.DataFrame(results)
    
    if not final_df.empty:
        # Sort
        final_df = final_df.sort_values('TotalPoints', ascending=False)
        final_df['Rank'] = range(1, len(final_df) + 1)
        
        # Save
        final_df.to_csv(output_file, index=False, sep=';')
        print(f"\nSuccessfully generated standings for {len(final_df)} drivers.")
        print(f"Saved to: {output_file}")
    else:
        print("No data found to generate standings.")

if __name__ == "__main__":
    # Adjust paths as needed
    INPUT_DIR = "../Files/Results S16"
    OUTPUT_FILE = "../Files/Results_csv/s16_standings.csv"
    
    # Check if we are running from 'Scripts' folder or root
    if not os.path.exists(INPUT_DIR):
        # Fallback for different CWD
        INPUT_DIR = "Files/Results S16"
        OUTPUT_FILE = "Files/Results_csv/s16_standings.csv"
        
    calculate_s16_standings(INPUT_DIR, OUTPUT_FILE)
