import streamlit as st
import pandas as pd
import numpy as np
import requests
from math import radians, sin, cos, sqrt, atan2

# Haversine formula to calculate distance between two lat/lon points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Get coordinates using Nominatim API (OpenStreetMap)
def get_coordinates(address):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": address, "format": "json"}
        response = requests.get(url, params=params, headers={"User-Agent": "GeoDistanceApp"})
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except:
        return None, None

# Title
st.title("Distance Calculator Between Locations")

st.write("""
You can either:
- Paste coordinates manually ("Location Name, Latitude, Longitude"), **or**
- Enter address names below and let the app find their coordinates.
""")

# Option to enter address-based locations
st.subheader("Enter Address Locations")
num_addresses = st.number_input("How many addresses would you like to enter?", min_value=1, max_value=20, value=3, step=1)
address_inputs = []
for i in range(num_addresses):
    addr = st.text_input(f"Address {i + 1}")
    address_inputs.append(addr)

addresses = []
if st.button("Fetch Coordinates"):
    for i, addr in enumerate(address_inputs):
        if addr:
            lat, lon = get_coordinates(addr)
            if lat is not None and lon is not None:
                addresses.append((addr, lat, lon))
            else:
                st.warning(f"Could not find coordinates for: {addr}")

# Text input for manual coordinates
st.subheader("Or Paste Coordinates Manually")
input_text = st.text_area("Paste coordinates here:", height=250)

locations = addresses[:]

if input_text:
    try:
        # Parse the input text
        bad_lines = []
        for line in input_text.strip().split('\n'):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) == 3:
                try:
                    name, lat, lon = parts[0], float(parts[1]), float(parts[2])
                    locations.append((name, lat, lon))
                except ValueError:
                    bad_lines.append(line)
            else:
                bad_lines.append(line)

        if bad_lines:
            st.warning(f"Skipped {len(bad_lines)} invalid line(s):\n" + '\n'.join(bad_lines))

    except Exception as e:
        st.error(f"Error processing input: {e}")

if len(locations) < 2 and not st.button("Retry with new input"):
    st.info("Please enter at least two valid locations to proceed.")
    st.stop()

try:
    # Convert to DataFrame
    df = pd.DataFrame(locations, columns=['Name', 'Latitude', 'Longitude'])

    # Display list of confirmed locations
    st.subheader("Confirmed Locations and Coordinates")
    st.dataframe(df)

    # Shorten names for distance matrix
    df['ShortName'] = df['Name'].apply(lambda x: ' '.join(x.split()[:2]))

    # Create distance matrix
    n = len(df)
    distances = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            if i != j:
                distances[i, j] = haversine(df.iloc[i]['Latitude'], df.iloc[i]['Longitude'],
                                            df.iloc[j]['Latitude'], df.iloc[j]['Longitude'])

    # Display distance matrix with shortened names
    dist_df = pd.DataFrame(distances, columns=df['ShortName'], index=df['ShortName'])
    st.subheader("Distance Matrix (km)")
    st.dataframe(dist_df.style.format("{:.2f}"))

    # Calculate statistics
    upper_triangle = distances[np.triu_indices(n, k=1)]
    total_distance = upper_triangle.sum()
    avg_distance = upper_triangle.mean()
    median_distance = np.median(upper_triangle)

    st.subheader("Distance Summary")
    st.write(f"**Total distance (sum of all unique pairs):** {total_distance:.2f} km")
    st.write(f"**Average distance:** {avg_distance:.2f} km")
    st.write(f"**Median distance:** {median_distance:.2f} km")

    # Find most central location (lowest average distance to all others)
    avg_dists = distances.mean(axis=1)
    median_dists = np.median(distances, axis=1)
    central_index = np.argmin(avg_dists)
    central_location = df.iloc[central_index]
    st.subheader("Most Central Location")
    st.write(f"**{central_location['Name']}** is the most central location ")
    st.write(f"**Coordinates:** {central_location['Latitude']}, {central_location['Longitude']}")
    st.write(f"**Average distance to all others:** {avg_dists[central_index]:.2f} km")
    st.write(f"**Median distance to all others:** {median_dists[central_index]:.2f} km")

    # Allow user to select a location to view average and median distance to others
    if len(df) >= 2:
        st.subheader("Distance Statistics from a Selected Location")
        selected_location = st.selectbox("Choose a location:", df['Name'])
        selected_index = df[df['Name'] == selected_location].index[0]
        avg_from_selected = distances[selected_index].sum() / (n - 1)
        max_from_selected = distances[selected_index].max()
        median_from_selected = np.median(distances[selected_index][distances[selected_index] > 0])

        st.write(f"**Average distance from {selected_location} to all others:** {avg_from_selected:.2f} km")
        st.write(f"**Median distance from {selected_location} to all others:** {median_from_selected:.2f} km")
        st.write(f"**Minimum radius to cover all other locations from {selected_location}:** {max_from_selected:.2f} km")

except Exception as e:
    st.error(f"Error processing locations: {e}")
