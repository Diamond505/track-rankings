import os
import ftplib
from datetime import datetime
import json

# Configuration file path
CONFIG_FILE = "server_config.json"

def load_config():
    """Load server configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None

def save_config(config):
    """Save server configuration to JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def setup_servers():
    """Interactive setup for server credentials."""
    print("\n=== G-Portal Server Setup ===")
    print("You'll need your FTP credentials from G-Portal control panel.\n")
    
    servers = []
    
    for i in range(1, 3):
        print(f"\n--- Server {i} Configuration ---")
        host = input(f"FTP Host (e.g., 123.456.789.0): ").strip()
        port = input(f"FTP Port (default 21): ").strip() or "21"
        username = input(f"FTP Username: ").strip()
        password = input(f"FTP Password: ").strip()
        
        servers.append({
            "name": f"Server {i}",
            "host": host,
            "port": int(port),
            "username": username,
            "password": password,
            "remote_path": "/home/results/"
        })
    
    config = {"servers": servers}
    save_config(config)
    print("\n[OK] Server configuration saved!")
    return config

def find_results_directory(ftp):
    """Try to find the results directory on the server."""
    # First, try the most common path based on what we saw
    try:
        ftp.cwd('/')
        ftp.cwd('results')
        print("[INFO] Successfully navigated to /results/")
        
        # Try NLST first
        files = []
        try:
            ftp.retrlines('NLST', files.append)
            print(f"[DEBUG] NLST found {len(files)} items")
            if files:
                print(f"[DEBUG] First few items: {files[:5]}")
        except:
            print("[DEBUG] NLST failed, trying LIST")
            # Try LIST instead
            files = []
            ftp.retrlines('LIST', files.append)
            print(f"[DEBUG] LIST found {len(files)} items")
            if files:
                print(f"[DEBUG] First few items: {files[:3]}")
                # Extract filenames from LIST output
                files = [line.split()[-1] for line in files if not line.startswith('d')]
        
        json_files = [f for f in files if f.endswith('.json')]
        
        if json_files:
            print(f"[OK] Found {len(json_files)} JSON file(s) in /results/")
            return 'results'
        else:
            print(f"[INFO] /results/ directory has {len(files)} files but no .json files")
            print(f"[DEBUG] File extensions found: {set([f.split('.')[-1] if '.' in f else 'no-ext' for f in files[:10]])}")
            
            # Check subdirectories
            ftp.cwd('/')
            ftp.cwd('results')
            subdirs = []
            ftp.retrlines('LIST', subdirs.append)
            for line in subdirs:
                if line.startswith('d'):
                    dirname = line.split()[-1]
                    if dirname not in ['.', '..']:
                        try:
                            ftp.cwd(dirname)
                            subfiles = []
                            ftp.retrlines('NLST', subfiles.append)
                            json_in_sub = [f for f in subfiles if f.endswith('.json')]
                            if json_in_sub:
                                print(f"[OK] Found {len(json_in_sub)} JSON file(s) in results/{dirname}/")
                                return f'results/{dirname}'
                            ftp.cwd('..')
                        except:
                            pass
    except Exception as e:
        print(f"[DEBUG] Error checking /results/: {e}")
    
    # Try other common paths
    possible_paths = [
        "results-bak",
        "cfg/results",
        "server/results"
    ]
    
    for path in possible_paths:
        try:
            ftp.cwd('/')
            ftp.cwd(path)
            files = []
            ftp.retrlines('NLST', files.append)
            json_files = [f for f in files if f.endswith('.json')]
            if json_files:
                print(f"[OK] Found {len(json_files)} JSON file(s) in {path}/")
                return path
        except:
            continue
    
    return None

def download_results_from_server(server_config, local_dir):
    """Download new JSON files from a single server."""
    print(f"\n--- Connecting to {server_config['name']} ---")
    print(f"Host: {server_config['host']}")
    
    try:
        # Connect to FTP server
        ftp = ftplib.FTP()
        ftp.connect(server_config['host'], server_config['port'])
        ftp.login(server_config['username'], server_config['password'])
        
        print("[OK] Connected successfully!")
        
        # Try to find the results directory
        print("[INFO] Searching for results directory...")
        results_path = find_results_directory(ftp)
        
        if not results_path:
            print("[ERROR] Could not find results directory with JSON files")
            print("[INFO] Available directories:")
            try:
                ftp.cwd('/')
                dirs = []
                ftp.retrlines('LIST', dirs.append)
                for line in dirs[:10]:  # Show first 10 items
                    print(f"  {line}")
            except:
                pass
            ftp.quit()
            return 0
        
        # We're already in the results directory from find_results_directory()
        # Just need to get the file list
        print(f"[OK] Using directory: /{results_path}/")
        
        # Get list of JSON files using LIST since NLST failed earlier
        files = []
        try:
            ftp.retrlines('NLST', files.append)
        except:
            # NLST failed, use LIST and extract filenames
            ftp.retrlines('LIST', files.append)
            files = [line.split()[-1] for line in files if not line.startswith('d')]
        
        json_files = [f for f in files if f.endswith('.json')]
        
        if not json_files:
            print("No JSON files found.")
            ftp.quit()
            return 0
        
        # Get existing local files
        existing_files = set(os.listdir(local_dir)) if os.path.exists(local_dir) else set()
        
        # Download new files
        downloaded = 0
        for filename in json_files:
            if filename not in existing_files:
                local_path = os.path.join(local_dir, filename)
                print(f"Downloading: {filename}")
                
                with open(local_path, 'wb') as local_file:
                    ftp.retrbinary(f'RETR {filename}', local_file.write)
                
                downloaded += 1
            else:
                print(f"Skipping (already exists): {filename}")
        
        ftp.quit()
        print(f"\n[OK] Downloaded {downloaded} new file(s) from {server_config['name']}")
        return downloaded
        
    except ftplib.all_errors as e:
        print(f"[ERROR] FTP Error: {e}")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 0

def main():
    """Main download function."""
    print("\n=== G-Portal Results Downloader ===\n")
    
    # Load or create configuration
    config = load_config()
    
    if not config:
        print("No server configuration found.")
        setup_choice = input("Would you like to set up servers now? (y/n): ").strip().lower()
        if setup_choice == 'y':
            config = setup_servers()
        else:
            print("Setup cancelled.")
            return
    
    # Determine local directory
    # Check if we're in Scripts/ or root
    if os.path.basename(os.getcwd()) == "Scripts":
        local_dir = "../Files/Results_json"
    else:
        local_dir = "Files/Results_json"
    
    # Create directory if it doesn't exist
    os.makedirs(local_dir, exist_ok=True)
    
    print(f"\nLocal download directory: {os.path.abspath(local_dir)}")
    
    # Download from all servers
    total_downloaded = 0
    for server in config['servers']:
        count = download_results_from_server(server, local_dir)
        total_downloaded += count
    
    print(f"\n{'='*50}")
    print(f"Total files downloaded: {total_downloaded}")
    print(f"{'='*50}")
    
    if total_downloaded > 0:
        print("\n[!] New files downloaded! You may want to:")
        print("    1. Run 'Update Live Series Standings' to process them")
        print("    2. Run 'Convert JSONs to Track CSVs' for global rankings")

if __name__ == "__main__":
    main()
