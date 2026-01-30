import pandas as pd
import os

def load_and_process_data(file_path):
    """
    Loads track data from CSV and calculates rankings.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    try:
        # Load the CSV data using '; ' as delimiter based on file inspection
        df = pd.read_csv(file_path, delimiter=';')
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Filter valid laps
        # The file uses 2147483647 for invalid/no time
        valid_laps = df[df['Best lap (ms)'] < 2147483647].copy()
        
        if valid_laps.empty:
            print("No valid laps found in the data.")
            return None

        # Group by Track and Player (using SteamId for uniqueness) to find their personal best
        # We also keep FirstName, LastName, Car for display
        best_times = valid_laps.groupby(['Track', 'SteamId']).agg({
            'Best lap (ms)': 'min',
            'FirstName': 'first', # Take the first name found for this ID
            'LastName': 'first',
            'Car': 'first',
            'Best lap': 'first' # format 00:00.000 might not be the min numerical value, so we'll reconstruct it or pick one corresponding to min ms if needed. 
                                # For simplicity in this v1, since we sort by ms, we can just grab the formatted string. 
                                # A more robust way is to re-format from ms or locate the row with min ms.
        }).reset_index()

        # To be perfectly accurate with the 'Best lap' string, let's merge back the formatted string from the original row 
        # corresponding to the minimum ms. 
        # Alternatively, for simplicity, we can just sort the original valid_laps by ms, then drop duplicates.
        
        # Better approach: Sort by time, then drop duplicates keeping the fastest
        best_times_refined = valid_laps.sort_values('Best lap (ms)').drop_duplicates(subset=['Track', 'SteamId'])
        
        return best_times_refined

    except Exception as e:
        print(f"An error occurred processing the file: {e}")
        return None

def get_track_rankings(df, track_name):
    """
    Returns the leaderboard for a specific track.
    """
    if df is None:
        return None
        
    # Case-insensitive match for track name
    track_df = df[df['Track'].str.lower() == track_name.lower()].copy()
    
    if track_df.empty:
        return None
    
    # Sort by time
    track_df = track_df.sort_values('Best lap (ms)')
    
    # Add rank
    track_df['Rank'] = range(1, len(track_df) + 1)
    
    return track_df[['Rank', 'FirstName', 'LastName', 'Car', 'Best lap']]

def list_tracks(df):
    """Returns a list of available unique tracks."""
    if df is None:
        return []
    return sorted(df['Track'].unique())

if __name__ == "__main__":
    # Define valid path
    # Using raw string r'' to handle backslashes on Windows
    FILE_PATH = r"d:\Software and coding\Json sorter\Files\Results S16\all_tracks_data.csv"
    
    print("Loading data...")
    data = load_and_process_data(FILE_PATH)
    
    if data is not None:
        print("\nData loaded successfully.")
        
        tracks = list_tracks(data)
        print(f"Found {len(tracks)} tracks: {', '.join(tracks[:5])}...")

        while True:
            print("\n" + "="*30)
            user_input = input("Enter a track name to see rankings (or 'q' to quit, 'list' for all tracks): ").strip()
            
            if user_input.lower() == 'q':
                break
            
            if user_input.lower() == 'list':
                print("\nAvailable Tracks:")
                for t in tracks:
                    print(f" - {t}")
                continue

            rankings = get_track_rankings(data, user_input)
            
            if rankings is not None:
                print(f"\n--- Rankings for {user_input} ---")
                # formatting the table nicely
                print(rankings.to_string(index=False))
            else:
                print(f"Track '{user_input}' not found or no valid data.")
