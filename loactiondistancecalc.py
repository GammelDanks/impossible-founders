import streamlit as st
import pandas as pd
import numpy as np
import requests
from math import radians, sin, cos, sqrt, atan2
from scipy.optimize import minimize
import folium
from streamlit_folium import st_folium

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

# Objective function to minimize average distance to all points
def average_distance_to_all(x, points):
    lat, lon = x
    return np.mean([haversine(lat, lon, p[0], p[1]) for p in points])

# Title
st.title("Distance Calculator Between Locations")

st.write("""
You can either:
- Paste coordinates manually ("Location Name, Latitude, Longitude"), **or**
- Enter address names below and let the app find their coordinates.
""")

# Initialize session state for addresses and failed lookups
if 'addresses' not in st.session_state:
    st.session_state.addresses = []
if 'failed_addresses' not in st.session_state:
    st.session_state.failed_addresses = []

# Option to enter address-based locations
st.subheader("Enter Address Locations")
num_addresses = st.number_input("How many addresses would you like to enter?", min_value=1, max_value=100, value=3, step=1)
address_inputs = []
for i in range(num_addresses):
    addr = st.text_input(f"Address {i + 1}", key=f"addr_{i}")
    address_inputs.append(addr)

if st.button("Fetch Coordinates"):
    st.session_state.addresses = []
    st.session_state.failed_addresses = []
    new_addresses = []
    for i, addr in enumerate(address_inputs):
        if addr and len(addr.strip()) > 2:
            try:
                lat, lon = get_coordinates(addr.strip())
                if lat is not None and lon is not None:
                    new_addresses.append((addr.strip(), lat, lon))
                else:
                    st.session_state.failed_addresses.append(addr.strip())
                    st.warning(f"Could not find coordinates for: {addr}")
            except Exception as e:
                st.session_state.failed_addresses.append(addr.strip())
                st.warning(f"Error looking up '{addr}': {e}")
    st.session_state.addresses = new_addresses

# Optional bulk address input
st.subheader("Or Paste a List of Location Names (One Per Line)")
bulk_input = st.text_area("Paste locations here:", height=200)

if st.button("Fetch Coordinates from Bulk Input"):
    st.session_state.addresses = []
    st.session_state.failed_addresses = []
    new_bulk_addresses = []
    for line in bulk_input.strip().split('\n'):
        addr = line.strip()
        if addr and len(addr) > 2:
            try:
                lat, lon = get_coordinates(addr)
                if lat is not None and lon is not None:
                    new_bulk_addresses.append((addr, lat, lon))
                else:
                    st.session_state.failed_addresses.append(addr)
                    st.warning(f"Could not find coordinates for: {addr}")
            except Exception as e:
                st.session_state.failed_addresses.append(addr)
                st.warning(f"Error looking up '{addr}': {e}")
    st.session_state.addresses.extend(new_bulk_addresses)

# If there are failed lookups, ask for manual address entry
if st.session_state.failed_addresses:
    st.subheader("Retry Manually for Unresolved Locations")
    new_manual_entries = []
    for i, name in enumerate(st.session_state.failed_addresses):
        retry_address = st.text_input(f"Enter full address for '{name}'", key=f"manual_{i}")
        if retry_address:
            try:
                lat, lon = get_coordinates(retry_address)
                if lat is not None and lon is not None:
                    new_manual_entries.append((name, lat, lon))
            except:
                st.warning(f"Could not retrieve coordinates for '{name}' with manual entry.")
    if st.button("Add Manually Retrieved Coordinates"):
        st.session_state.addresses.extend(new_manual_entries)
        st.session_state.failed_addresses = []

# Text input for manual coordinates
st.subheader("Or Paste Coordinates Manually")
input_text = st.text_area("Paste coordinates here:", height=250)

locations = st.session_state.addresses[:]

if input_text:
    try:
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
    # Ensure unique names
    names_seen = {}
    unique_locations = []
    for name, lat, lon in locations:
        base_name = name.strip()
        if base_name in names_seen:
            names_seen[base_name] += 1
            base_name = f"{base_name} ({names_seen[base_name]})"
        else:
            names_seen[base_name] = 1
        unique_locations.append((base_name, lat, lon))

    df = pd.DataFrame(unique_locations, columns=['Name', 'Latitude', 'Longitude'])

    st.subheader("Confirmed Locations and Coordinates")
    st.dataframe(df)

    # Use full name as ShortName and ensure uniqueness
    short_names_seen = {}
    short_names = []
    for name in df['Name']:
        short = name
        if short in short_names_seen:
            short_names_seen[short] += 1
            short = f"{short} ({short_names_seen[short]})"
        else:
            short_names_seen[short] = 1
        short_names.append(short)
    df['ShortName'] = short_names

    n = len(df)
    distances = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                distances[i, j] = haversine(df.iloc[i]['Latitude'], df.iloc[i]['Longitude'],
                                            df.iloc[j]['Latitude'], df.iloc[j]['Longitude'])

    dist_df = pd.DataFrame(distances, columns=df['ShortName'], index=df['ShortName'])
    st.subheader("Distance Matrix (km)")
    st.dataframe(dist_df.style.format("{:.2f}"))

    upper_triangle = distances[np.triu_indices(n, k=1)]
    total_distance = upper_triangle.sum()
    avg_distance = upper_triangle.mean()
    median_distance = np.median(upper_triangle)

    st.subheader("Distance Summary")
    st.write(f"**Total distance (sum of all unique pairs):** {total_distance:.2f} km")
    st.write(f"**Average distance:** {avg_distance:.2f} km")
    st.write(f"**Median distance:** {median_distance:.2f} km")

    coords_array = df[['Latitude', 'Longitude']].values
    lat_init, lon_init = np.mean(coords_array, axis=0)
    result = minimize(average_distance_to_all, x0=[lat_init, lon_init], args=(coords_array,), method='Nelder-Mead')

    if result.success:
        optimal_lat, optimal_lon = result.x
        avg_dist_to_all = average_distance_to_all((optimal_lat, optimal_lon), coords_array)
        st.subheader("Optimal Hypothetical Central Location")
        st.write(f"**Coordinates:** {optimal_lat:.6f}, {optimal_lon:.6f}")
        st.write(f"**Minimum average distance to all others:** {avg_dist_to_all:.2f} km")

        m = folium.Map(location=[optimal_lat, optimal_lon], zoom_start=6)

        folium.Circle(
            location=[optimal_lat, optimal_lon],
            radius=avg_dist_to_all * 1000,
            color='red', fill=False,
            tooltip=f"Radius = {avg_dist_to_all:.1f} km"
        ).add_to(m)

        for _, row in df.iterrows():
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                tooltip=row['Name'],
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)
            folium.PolyLine(
                locations=[[optimal_lat, optimal_lon], [row['Latitude'], row['Longitude']]],
                color='gray', weight=1, opacity=0.6
            ).add_to(m)

        folium.Marker(
            location=[optimal_lat, optimal_lon],
            tooltip="Hypothetical Center",
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)

        st.subheader("Map Visualization")
        st_folium(m, width=700, height=500)
    else:
        st.warning("Could not compute the optimal central location.")

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
