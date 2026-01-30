import streamlit as st
import pandas as pd
import os

# Set page configuration
st.set_page_config(
    page_title="BoA Rankings",
    page_icon="🏎️",
    layout="wide"
)

# Constants
# Standard F1-style point system
POINTS_SYSTEM = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}

@st.cache_data
def load_data(file_path):
    """
    Loads and processes the track data.
    Cached to improve performance.
    """
    # Try different paths locally vs deployed
    possible_paths = [
        file_path,
        "all_tracks_data.csv",
        "../Files/Results_csv/all_tracks_data.csv",
        "../Files/Results S16/all_tracks_data.csv",
        "data/all_tracks_data.csv"
    ]
    
    csv_file = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_file = path
            break
            
    if not csv_file:
        return None
    
    try:
        # Load CSV
        df = pd.read_csv(csv_file, delimiter=';')
        df.columns = df.columns.str.strip()
        
        # Filter valid laps
        valid_laps = df[df['Best lap (ms)'] < 2147483647].copy()
        
        return valid_laps
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def calculate_track_leaderboards(df):
    """
    Calculates rankings for each track and car class.
    Returns a dataframe sorted by time with ranks.
    """
    # Sort by time and keep best per player per track per class
    # We need to rank within Track AND Class
    best_times = df.sort_values('Best lap (ms)').drop_duplicates(subset=['Track', 'Car Class', 'SteamId'])
    
    # Assign ranks
    best_times['Rank'] = best_times.groupby(['Track', 'Car Class'])['Best lap (ms)'].rank(method='min').astype(int)
    
    return best_times

def calculate_championship(df):
    """
    Calculates championship points based on the new custom rules:
    1. Participation: 10 points for each entry.
    2. Track Record: 3 points for 1st, 2 points for 2nd, 1 point for 3rd (per track/class).
    3. King of the Hill: 1 final point for whoever holds the most 1st place Track Records.
    """
    if df.empty:
        return pd.DataFrame()

    # Dictionary to store scores: {steam_id: stats_dict}
    driver_stats = {}
    
    # Helper to count how many actual #1 records a driver has for the bonus
    driver_records_count = {} 

    def get_driver_entry(steam_id, last_name):
        if steam_id not in driver_stats:
            driver_stats[steam_id] = {
                'LastName': last_name,
                'Participation': 0,
                'Track Records': 0, # This will now be points, not just count
                'King Bonus': 0,
                'Total Points': 0,
                'Overall Rank': 0
            }
            driver_records_count[steam_id] = 0
        return driver_stats[steam_id]

    # Process by Car Class to ensure fair comparison
    # Ensure Car Class exists
    if 'Car Class' not in df.columns:
         df['Car Class'] = 'Unknown'

    for car_class, class_df in df.groupby('Car Class'):
        
        # 1. Participation Points
        for _, row in class_df.iterrows():
            entry = get_driver_entry(row['SteamId'], row['LastName'])
            entry['Participation'] += 10 # Updated to 10 points

        # 3. Current Track Record Points (Top 3)
        # Group by Track only
        for track_name, group in class_df.groupby('Track'):
            # Get best time per driver for this track
            best_per_driver = group.sort_values('Best lap (ms)').drop_duplicates(subset=['SteamId'])
            
            # Take top 3
            top_3 = best_per_driver.head(3)
            
            # Points assignment: 1st=3, 2nd=2, 3rd=1
            points_dist = [3, 2, 1]
            
            for i, (idx, row) in enumerate(top_3.iterrows()):
                if i < len(points_dist):
                    entry = get_driver_entry(row['SteamId'], row['LastName'])
                    entry['Track Records'] += points_dist[i]
                    
                    # Count actual records for King Bonus (only 1st place)
                    if i == 0:
                        driver_records_count[row['SteamId']] += 1

    # 4. King of the Hill Bonus
    # Who has the most 1st place records?
    max_records = 0
    for count in driver_records_count.values():
        if count > max_records:
            max_records = count
    
    if max_records > 0:
        for steam_id, count in driver_records_count.items():
            if count == max_records:
                driver_stats[steam_id]['King Bonus'] += 1

    # Calculate Total
    results = []
    for steam_id, stats in driver_stats.items():
        stats['Total Points'] = (
            stats['Participation'] + 
            stats['Track Records'] + 
            stats['King Bonus']
        )
        results.append(stats)

    # Convert to DataFrame
    championship = pd.DataFrame(results)
    
    if not championship.empty:
        championship = championship.sort_values('Total Points', ascending=False)
        championship['Overall Rank'] = range(1, len(championship) + 1)

    return championship

def main():
    # --- Custom CSS for Fonts and Colors ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Anton&family=Roboto:wght@300;400;700&display=swap');

        /* Apply Roboto to the whole app */
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        
        /* Apply Anton to all headers */
        h1, h2, h3, .stHeading, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 {
            font-family: 'Anton', sans-serif !important;
            text-transform: uppercase !important;
            color: #edc00d !important; 
            letter-spacing: 1px;
        }

        /* Tabs Coloring */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.2rem;
        }
        
        /* Active Tab */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            color: #edc00d !important;
            border-bottom-color: #edc00d !important;
        }
        
        /* Tab underline/highlight */
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #edc00d !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Logo & Title ---
    col1, col2, col3 = st.columns([1, 6, 1])
    
    # Try different paths for the logo
    logo_path = None
    possible_logos = [
        "../Files/assets/boa_logo.png",
        "assets/boa_logo.png",
        "boa_logo.png"
    ]
    for path in possible_logos:
        if os.path.exists(path):
            logo_path = path
            break

    with col1:
        if logo_path:
            st.image(logo_path, width=100)
            
    with col2:
        st.markdown("""
            <h1 style='text-align: center;'>
                <span style='margin-right: 10px;'>🏎️</span>
                BoA RACING LEADERBOARD
                <span style='display: inline-block; transform: scaleX(-1); margin-left: 10px;'>🏎️</span>
            </h1>
            """, unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>v2.4 - Updated Scoring & Styling</p>", unsafe_allow_html=True)

    with col3:
        if logo_path:
            st.image(logo_path, width=100)
    
    # --- Season Selection ---
    st.sidebar.header("Navigation")
    view_option = st.sidebar.radio(
        "Select View",
        ["Live Series Standings", "Global Driver Rankings"]
    )

    # File Paths
    CURRENT_FILE = "current_standings.csv" # JSON-based Series Standings
    S16_FILE = "s16_standings.csv" # S16 Archive
    TRACK_DATA_FILE = "all_tracks_data.csv" # Global Rankings Data
    
    # Helper to find file
    def find_file(filename):
        possible_paths = [
            filename,
            f"../Files/Results_csv/{filename}",
            f"Files/Results_csv/{filename}"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    current_path = find_file(CURRENT_FILE)
    s16_path = find_file(S16_FILE)
    track_data_path = find_file(TRACK_DATA_FILE)

    # --- Tabs ---
    # Tabs are context-dependent now, or we can keep them generic
    tab1, tab2 = st.tabs(["🏆 Leaderboard", "⏱️ Track Records"])

    # --- Tab 1: Leaderboard ---
    with tab1:
        if view_option == "Global Driver Rankings":
            st.header("Global Driver Rankings")
            st.caption("Based on all-time Fastest Laps & Participation")
            st.markdown("""
            **Ranking System:**
            *   **+10 Points** per Event Entry (Participation).
            *   **Track Records (per Class):** 🥇3pts, 🥈2pts, 🥉1pt.
            *   **+1 Bonus Point** for the 'King of the Hill' (Most #1 Records).
            """)
            
            # Load Data
            if track_data_path:
                try:
                    data = pd.read_csv(track_data_path, delimiter=';')
                    # Clean columns
                    data.columns = data.columns.str.strip()
                    
                    # Calculate
                    championship_data = calculate_championship(data)
                    
                    # Display Columns
                    champ_cols = ['Overall Rank', 'LastName', 'Participation', 'Track Records', 'King Bonus', 'Total Points']
                    
                    st.dataframe(
                        championship_data[champ_cols],
                        hide_index=True,
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error calculating Global Rankings: {e}")
            else:
                st.error("Global data file (all_tracks_data.csv) not found.")

        else:
            # Live Series (Current Season)
            st.header("Live Series Standings")
            st.caption("Current Season - Points per Race Position")
            st.markdown("""
            **Scoring System:**
            *   **1st**: 50, **2nd**: 45, **3rd**: 42, **4th**: 39, **5th**: 36
            *   **6th-10th**: 33, 30, 27, 24, 21
            *   **11th-20th**: 20 ↘ 11
            *   **21st-30th**: 10 ↘ 1
            """)
            
            if current_path:
                try:
                    current_df = pd.read_csv(current_path, delimiter=';')
                    # Columns: FirstName, LastName, Car Class, TotalPoints, Races, Wins, SteamId, Rank
                    
                    display_cols = ['Rank', 'LastName', 'Races', 'Wins', 'TotalPoints']
                    
                    st.dataframe(
                        current_df[display_cols],
                        hide_index=True,
                        use_container_width=True
                    )
                except Exception as e:
                     st.error(f"Error loading Current Season standings: {e}")
            else:
                st.warning("Current Season Standings file not found. Please update data.")

    # --- Tab 2: Track Leaderboards ---
    with tab2:
        if view_option == "Live Series Standings":
            st.info("Track breakdowns are best viewed in 'Global Driver Rankings' mode (uses separate track CSVs).")
            # We could technically show them if we wanted, but the logic separates them.
        elif view_option == "Season 16 (Archive)":
             st.info("Archive track details not loaded.")
        else:
            # Global Rankings Mode - Show Track Data
            st.header("Track Records")
            
            # Load Track Data (if not already loaded in Tab 1 logic, but safer to re-check path)
            data = None
            if track_data_path:
                 try:
                     data = pd.read_csv(track_data_path, delimiter=';')
                     data.columns = data.columns.str.strip()
                     data = data[data['Best lap (ms)'] < 2147483647].copy()
                 except:
                     pass
            
            if data is not None:
                # Sidebar/Top Filters for this tab
                col1, col2 = st.columns(2)
                
                with col1:
                    track_list = sorted(data['Track'].unique())
                    selected_track = st.selectbox("Select Track", track_list)
                    
                with col2:
                    track_subset = data[data['Track'] == selected_track]
                    available_classes = sorted(track_subset['Car Class'].unique()) if not track_subset.empty else []
                    selected_class = st.selectbox("Select Class", available_classes)
        
                if selected_track and selected_class:
                    track_data = data[
                        (data['Track'] == selected_track) & 
                        (data['Car Class'] == selected_class)
                    ].copy()
                    track_data = track_data.sort_values('Best lap (ms)').drop_duplicates(subset=['SteamId'])
                    track_data['Rank'] = range(1, len(track_data) + 1)
                    
                    st.subheader(f"Results: {selected_track} - {selected_class}")
                    cols = ['Rank', 'LastName', 'Car', 'Best lap']
                    st.dataframe(track_data[cols], hide_index=True, use_container_width=True)

if __name__ == "__main__":
    main()
