# Remove invalid lap times (those set to 2147483647 or worse than 10 minutes)
valid_df = df[df['Best lap (ms)'] < 6000000].copy()

# Build lookup for first FirstName per SteamId
firstnames = (valid_df[valid_df['FirstName'].notna() & (valid_df['FirstName'].str.strip() != '')]
              .drop_duplicates(subset='SteamId')
              .set_index('SteamId')['FirstName']
              .to_dict())

# Create 'Driver' column: use first FirstName + LastName seen, else just LastName
def get_driver_name(row):
    if row['SteamId'] in firstnames:
        return f"{firstnames[row['SteamId']]} {row['LastName']}".strip()
    else:
        return row['LastName']

valid_df['Driver'] = valid_df.apply(get_driver_name, axis=1)

# Group by Track and Car Class, rank by lap time, assign points
def assign_points(group):
    group = group.sort_values(by='Best lap (ms)')
    group['Points'] = range(len(group), 0, -1)
    return group

ranked_df = valid_df.groupby(['Track', 'Car Class']).apply(assign_points).reset_index(drop=True)

# Sum points per driver (across all tracks and classes)
total_points = ranked_df.groupby(['Driver', 'SteamId']).agg({'Points': 'sum'}).reset_index()

# Rank overall
total_points['Position'] = total_points['Points'].rank(method='min', ascending=False).astype(int)

# Sort by position
final_ranking = total_points.sort_values(by='Position')

# Output final ranking file
output_path_final = '/mnt/data/overall_driver_ranking.csv'
final_ranking.to_csv(output_path_final, index=False, sep=';')

# Show top 15
final_ranking.head(15)