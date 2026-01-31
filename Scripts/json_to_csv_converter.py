import os
import json
import re
import pandas as pd
from collections import defaultdict

# Load car models from external file
def load_car_models(file_path):
    car_models = {}
    with open(file_path, 'r') as file:
        exec(file.read(), car_models)
    return car_models['car_models']

# Load driver classes from CSV file
def load_driver_classes(csv_file_path):
    df = pd.read_csv(csv_file_path)
    driver_classes = {}
    for _, row in df.iterrows():
        driver_id = row['ID']  # Match by 'ID'
        driver_classes[driver_id] = row['Class']  # Get the 'Class'
    return driver_classes

# Load car models and driver classes
CAR_MODELS = load_car_models('Scripts/car_models.txt')
DRIVER_CLASSES = load_driver_classes("Scripts/Class's - Sheet1.csv")

COLUMN_ORDER = [
    'Place', 'FirstName', 'LastName', 'Class', 'Car Number', 'Car', 'Car Model',
    'Laps', 'Best S1', 'Best S2', 'Best S3', 'Best lap', 'Best lap (ms)',
    'Ideal Best lap', 'Total Race Time', 'Lap Date', 'SteamId', 'Conditions'
]

EXCLUDED_STEAM_IDS = {'M2533274796928070', }

def load_json_from_file(file_path):
    """Load JSON data from a file with error handling and repair invalid JSON."""
    encodings = ['utf-8-sig', 'utf-8', 'utf-16le', 'utf-16be', 'utf-16', 'iso-8859-1', 'windows-1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                raw_content = file.read()
                
                # 1. Try loading raw content first (safest)
                try:
                    return json.loads(raw_content)
                except json.JSONDecodeError:
                    # 2. If raw fails, try sanitizing
                    sanitized = sanitize_json(raw_content)
                    return json.loads(sanitized)
                    
        except (UnicodeError, LookupError):
            continue
        except Exception as e:
            if encoding == encodings[-1]:
                print(f'Error loading JSON from file "{file_path}": {str(e)}')
            
    return None

def sanitize_json(content):
    """Fix common JSON issues systematically without breaking valid strings."""
    # Remove control characters except for common whitespace
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    
    # Fix missing quotes on keys (only if truly needed)
    # content = re.sub(r"(?<=[{,])\s*([a-zA-Z0-9_]+)\s*:", r'"\1":', content)
    
    # Remove trailing commas in arrays/objects
    content = re.sub(r",\s*([\]}])", r"\1", content)
    
    return content.strip()

def format_time(time_ms):
    """Format milliseconds into MM:SS.mmm format."""
    if time_ms:
        total_seconds = int(time_ms) / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(time_ms) % 1000
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    return ''

def format_split_time(time_ms):
    """Format milliseconds into SS.mmm format."""
    if time_ms:
        total_seconds = int(time_ms) / 1000
        seconds = int(total_seconds)
        milliseconds = int(time_ms) % 1000
        return f"{seconds:02d}.{milliseconds:03d}"
    return ''

def calculate_total_race_time(timing_info):
    """Estimate the total race time."""
    best_lap_ms = timing_info.get('bestLap', 0)
    lap_count = timing_info.get('lapCount', 0)
    if best_lap_ms and lap_count:
        total_time_ms = int(best_lap_ms) * int(lap_count)
        return format_time(total_time_ms)
    return ''

def calculate_ideal_best_lap(splits):
    """Calculate the ideal best lap time."""
    try:
        total_ms = sum(int(split) for split in splits if split)
        return format_time(total_ms)
    except ValueError:
        return ''

def json_to_csv_data(json_data, filename):
    """Convert JSON data to CSV data."""
    session_result = json_data.get('sessionResult', {})
    leaderboard_lines = session_result.get('leaderBoardLines', [])
    driver_info_list = []

    # Weather condition: 0 = Dry, 1 = Wet
    is_wet = session_result.get('isWetSession', 0)
    conditions = "Wet" if is_wet == 1 else "Dry"

    date_str = filename[:6]
    lap_date = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}"

    for line in leaderboard_lines:
        car_info = line.get('car', {})
        driver_info = car_info.get('drivers', [{}])[0]
        timing_info = line.get('timing', {})

        best_splits = timing_info.get('bestSplits', ['', '', ''])
        best_lap_ms = timing_info.get('bestLap', '')
        driver_id = driver_info.get('playerId', '')

        if driver_id in EXCLUDED_STEAM_IDS:
            continue

        car_model = str(car_info.get('carModel', ''))
        car_name = CAR_MODELS.get(car_model, f'Unknown Car Model ({car_model})')
        driver_class = DRIVER_CLASSES.get(driver_id, 'Unknown')
        total_race_time = calculate_total_race_time(timing_info)

        driver_data = {
            'Place': line.get('position', 0),
            'FirstName': driver_info.get('firstName', ''),
            'LastName': driver_info.get('lastName', ''),
            'Class': driver_class,
            'Car Number': car_info.get('raceNumber', ''),
            'Car': car_name,
            'Car Model': car_model,
            'Laps': timing_info.get('lapCount', ''),
            'Best S1': format_split_time(best_splits[0]) if len(best_splits) > 0 else '',
            'Best S2': format_split_time(best_splits[1]) if len(best_splits) > 1 else '',
            'Best S3': format_split_time(best_splits[2]) if len(best_splits) > 2 else '',
            'Best lap': format_time(best_lap_ms),
            'Best lap (ms)': best_lap_ms,
            'Ideal Best lap': calculate_ideal_best_lap(best_splits),
            'Total Race Time': total_race_time,
            'Lap Date': lap_date,
            'SteamId': driver_id,
            'Conditions': conditions
        }

        driver_info_list.append(driver_data)

    sorted_drivers = sorted(driver_info_list, key=lambda x: x['Place'])
    return sorted_drivers

def process_race_data(input_directory_path, output_directory_path, output_types):
    # Walk through the directory recursively to find all JSON files
    json_files = []
    for root, dirs, files in os.walk(input_directory_path):
        for f in files:
            if f.endswith('.json'):
                # Store full path relative to input_directory_path or just the absolute path
                json_files.append(os.path.join(root, f))

    os.makedirs(output_directory_path, exist_ok=True)
    track_data = defaultdict(list)

    for json_file_path in sorted(json_files):
        filename = os.path.basename(json_file_path)
        json_data = load_json_from_file(json_file_path)
        if json_data is None or not json_to_csv_data(json_data, filename):
            continue

        csv_data = json_to_csv_data(json_data, filename)
        track_name = json_data.get('trackName', 'Unknown_Track')

        if 'results' in output_types:
            track_data[track_name].extend(csv_data)

    if 'results' in output_types:
        generate_race_results(track_data, output_directory_path)

def generate_race_results(track_data, output_directory_path):
    for track_name, data in track_data.items():
        csv_file_path = os.path.join(output_directory_path, f"{track_name}_results.csv")
        df = pd.DataFrame(data)
        df[COLUMN_ORDER].to_csv(csv_file_path, index=False, sep=';')
        print(f'Race results file "{csv_file_path}" has been created successfully.')

if __name__ == '__main__':
    json_directory_path = 'Files/Results_json'
    csv_directory_path = 'Files/Results_csv'
    output_types = ['results']
    process_race_data(json_directory_path, csv_directory_path, output_types)
