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
        
        # Save to master CSV
        merged_df.to_csv(output_file, index=False, sep=';')
        print(f"\nSuccessfully merged into {output_file} ({len(merged_df)} total records)")
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
