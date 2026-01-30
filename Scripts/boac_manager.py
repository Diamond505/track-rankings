import os
import sys
import subprocess
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("=========================================")
    print("   🏎️  BoA RACING LEADERBOARD MANAGER   ")
    print("=========================================")

def run_script(script_name):
    print(f"\n--- Running {script_name} ---")
    try:
        # Use python from current environment
        result = subprocess.run([sys.executable, script_name], 
                              check=True, 
                              capture_output=False) # Let output flow to console
        print(f"\n✅ {script_name} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running {script_name}: {e}")
    except FileNotFoundError:
        print(f"\n❌ Error: could not find {script_name}")
    
    input("\nPress Enter to return to menu...")

def check_git():
    # 1. Try global command
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return "git"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 2. Try default Windows paths
    possible_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Git\cmd\git.exe")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return None

def fix_safe_directory(git_cmd):
    """Fixes the 'dubious ownership' error by adding the current root to safe.directory."""
    try:
        # Determine Root Dir
        cwd = os.getcwd()
        if cwd.endswith("Scripts"):
            root_dir = os.path.dirname(cwd)
        else:
            root_dir = cwd
        
        # Normalize path for Git (forward slashes)
        safe_path = root_dir.replace('\\', '/')
        
        # Run config command
        subprocess.run([git_cmd, "config", "--global", "--add", "safe.directory", safe_path], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass

def check_git_identity(git_cmd):
    """Checks if user.name and user.email are set. If not, prompts user to set them."""
    try:
        # Check if email is configured
        subprocess.run([git_cmd, "config", "user.email"], stdout=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("\n⚠️  Git needs to know who you are for the first commit.")
        print("This is a one-time setup.")
        
        name = input("Enter your Name (e.g. John Doe): ").strip()
        if not name: name = "BoA Manager User"
        
        email = input("Enter your Email (e.g. john@example.com): ").strip()
        if not email: email = "user@boa-racing.com"
        
        print("Configuring Git Identity...")
        subprocess.run([git_cmd, "config", "--global", "user.name", name], check=True)
        subprocess.run([git_cmd, "config", "--global", "user.email", email], check=True)

def sync_to_github():
    print("\n--- ☁️ Syncing to GitHub ---")
    git_cmd = check_git()
    
    if not git_cmd:
        print("❌ Git is not installed or not found in PATH.")
        print("👉 TRY THIS: Restart your VS Code or Terminal to refresh the settings.")
        print("If that fails, verify installation from: https://git-scm.com/downloads")
        input("\nPress Enter to return...")
        return

    # ALWAYS Fix safe directory before checking status or init
    fix_safe_directory(git_cmd)

    # Check identity before proceeding
    check_git_identity(git_cmd)

    # Check if repo exists
    if not os.path.exists("../.git") and not os.path.exists(".git"):
        # We might be in Scripts/ so check parent too, but usually git init is in root.
        # Let's assume we want to init in the project root (parent of Scripts if we are in Scripts)
        
        print("❌ This folder is not linked to GitHub yet.")
        print("I can set it up for you right now.")
        
        repo_url = input("\nPaste your GitHub Repository URL here (or Press Enter to cancel): ").strip()
        
        if not repo_url:
            print("Cancelled setup.")
            input("\nPress Enter to return...")
            return

        # Fix URL if user just pasted "user/repo"
        if not repo_url.startswith("http"):
            repo_url = f"https://github.com/{repo_url}"
            
        try:
            print("\n1/3 Configuring Git Safety...")
            # Detect current root path for safe.directory
            # If in Scripts, we need the parent of Scripts
            cwd = os.getcwd()
            if cwd.endswith("Scripts"):
                root_dir = os.path.dirname(cwd) # Parent of Scripts
            else:
                root_dir = cwd
            
            # Already called fix_safe_directory but explicit init logic follows
            print("2/3 Initializing Git...")
            subprocess.run([git_cmd, "init"], cwd=root_dir, check=True)
            
            print(f"3/3 Linking to {repo_url}...")
            # Check if remote exists first to avoid error on retry
            try:
                subprocess.run([git_cmd, "remote", "add", "origin", repo_url], cwd=root_dir, check=True)
            except subprocess.CalledProcessError:
                print("Remote 'origin' already exists. Updating it...")
                subprocess.run([git_cmd, "remote", "set-url", "origin", repo_url], cwd=root_dir, check=True)
            
            print("\n✅ Setup Complete! Proceeding to sync...")
            
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error setting up Git: {e}")
            input("\nPress Enter to return...")
            return

    # Proceed with Sync
    # Determine Root Dir again for safety
    if os.getcwd().endswith("Scripts"):
        root_dir = ".."
    else:
        root_dir = "."

    # CRITICAL FIX: Ensure remote 'origin' actually exists!
    # (The previous setup might have been skipped if .git existed, but origin was missing)
    try:
        subprocess.run([git_cmd, "remote", "get-url", "origin"], cwd=root_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("\n⚠️  Git repository exists, but the link to GitHub is missing.")
        repo_url = input("Paste your GitHub Repository URL here to repair it: ").strip()
        
        if not repo_url:
             print("❌ Cannot sync without a GitHub URL.")
             input("\nPress Enter to return...")
             return
             
        if not repo_url.startswith("http"):
            repo_url = f"https://github.com/{repo_url}"
            
        try:
            print(f"Linking to {repo_url}...")
            subprocess.run([git_cmd, "remote", "add", "origin", repo_url], cwd=root_dir, check=True)
            print("✅ Link repaired!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to add remote: {e}")
            input("\nPress Enter to return...")
            return

    try:
        print("1/3 Adding files...")
        subprocess.run([git_cmd, "add", "."], cwd=root_dir, check=True)
        
        print("2/3 Committing changes...")
        subprocess.run([git_cmd, "commit", "-m", "Auto-update from BoA Manager"], cwd=root_dir, check=False) 
        
        # Renaissance the branch to 'main' to avoid 'master' vs 'main' conflicts
        subprocess.run([git_cmd, "branch", "-M", "main"], cwd=root_dir, check=True)
        
        print("3/3 Pushing to GitHub...")
        # Force push to overwrite remote if history diverged (e.g. init with README)
        subprocess.run([git_cmd, "push", "--force", "-u", "origin", "main"], cwd=root_dir, check=True)
        
        print("\n✅ Successfully synced to GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during sync: {e}")
    
    input("\nPress Enter to return to menu...")

def main():
    while True:
        clear_screen()
        print_header()
        print("\nSelect an action:")
        print("1. 📈 Update Live Series Standings (Process JSONs)")
        print("2. 🌍 Update Global Rankings (Merge Track CSVs)")
        print("3. 🔄 Convert New JSONs to Track CSVs (for Global Rankings)")
        print("4. 🔧 Launch Web App (Streamlit)")
        print("5. ☁️  Sync to GitHub (Requires Git)")
        print("0. 🚪 Exit")
        
        choice = input("\nEnter choice [0-5]: ").strip()
        
        if choice == '1':
            run_script('process_season_json.py')
        elif choice == '2':
            run_script('merge_results.py')
        elif choice == '3':
            run_script('json_to_csv_converter.py')
        elif choice == '4':
            print("\nLaunching Streamlit... (Press Ctrl+C to stop)")
            try:
                subprocess.run(["streamlit", "run", "app.py"])
            except KeyboardInterrupt:
                pass
        elif choice == '5':
            sync_to_github()
        elif choice == '0':
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")
            time.sleep(1)

if __name__ == "__main__":
    main()
