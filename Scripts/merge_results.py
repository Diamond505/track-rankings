import pandas as pd
import os
import glob

def merge_csv_files(input_folder, output_file):
    print(f"Scanning folder: {input_folder}")
    
    # Find all *_results.csv files
    search_pattern = os.path.join(input_folder, "*_results.csv")
    files = glob.glob(search_pattern)
    
    if not files:
        print("No files found matching '*_results.csv'")
        return

    print(f"Found {len(files)} files to merge.")
    
    all_data = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        # Extract track name: "imola_results.csv" -> "imola"
        track_name = filename.replace("_results.csv", "").replace("_", " ").title()
        
        try:
            # Read CSV with semicolon delimiter
            df = pd.read_csv(file_path, delimiter=';')
            
            # Normalize Columns
            # Remove 'Class' (Driver Category) as requested
            if 'Class' in df.columns:
                df.drop(columns=['Class'], inplace=True)
            
            # Derive 'Car Class' from 'Car' name
            def get_car_class(car_name):
                car_name = str(car_name).upper()
                if 'GT3' in car_name:
                    return 'GT3'
                elif 'GT4' in car_name:
                    return 'GT4'
                elif 'TCX' in car_name:
                    return 'TCX'
                elif 'CUP' in car_name: # Porsche Cup often just says Cup
                    return 'Cup'
                else:
                    return 'GT3' # Default to GT3 as requested

            if 'Car' in df.columns:
                df['Car Class'] = df['Car'].apply(get_car_class)
            
            # Add Track column
            df['Track'] = track_name
            
            all_data.append(df)
            print(f"Positioned {filename} as '{track_name}' ({len(df)} rows)")
            
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    if all_data:
        # Concatenate all dataframes
        merged_df = pd.concat(all_data, ignore_index=True)
        
        # Ensure we don't have duplicate columns due to whitespace
        merged_df.columns = merged_df.columns.str.strip()
        
        # DEDUPLICATION: Keep only the FASTEST lap per track per class (ONE record per track/class)
        # This means only the driver with the absolute fastest lap at each track in each class gets points
        print(f"\nTotal records before deduplication: {len(merged_df)}")
        
        # Ensure BestLap is numeric for proper sorting
        if 'BestLap' in merged_df.columns:
            # Convert BestLap to numeric (in case it's stored as string)
            merged_df['BestLap'] = pd.to_numeric(merged_df['BestLap'], errors='coerce')
            
            # Group by Track and Car Class, keep ONLY the row with the minimum BestLap
            # This gives us ONE record per track per class - the absolute fastest
            idx = merged_df.groupby(['Track', 'Car Class'])['BestLap'].idxmin()
            merged_df = merged_df.loc[idx].reset_index(drop=True)
            
            print(f"Total records after deduplication: {len(merged_df)}")
            print("(Kept only the absolute fastest lap per track per class)")
        
        # Save to master CSV
        merged_df.to_csv(output_file, index=False, sep=';')
        print(f"\nSuccessfully merged and deduplicated into {output_file}")
    else:
        print("No data collected.")

if __name__ == "__main__":
    # Define paths
    # Assuming script is in Scripts/ and data is in Files/Results S16/
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_DIR = os.path.join(BASE_DIR, "..", "Files", "Results_csv")
    OUTPUT_FILE = os.path.join(INPUT_DIR, "all_tracks_data.csv")
    
    # Normalize paths
    INPUT_DIR = os.path.normpath(INPUT_DIR)
    OUTPUT_FILE = os.path.normpath(OUTPUT_FILE)
    
    merge_csv_files(INPUT_DIR, OUTPUT_FILE)
