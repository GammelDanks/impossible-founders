import streamlit as st
import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2

# Haversine formula to calculate distance between two lat/lon points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Title
st.title("Distance Calculator Between Locations")

st.write("""
Paste your coordinates below in this format:

**Location Name, Latitude, Longitude**

Example:
Location A, 48.137154, 11.576124 Location B, 48.208174, 16.373819 Location C, 47.497913, 19.040236
""")

input_text = st.text_area("Paste coordinates here:", height=250)

if input_text:
    try:
        # Parse the input text
        locations = []
              bad_lines = []
        for idx, line in enumerate(input_text.strip().split('\n')):
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
            st.warning(f"Skipped {len(bad_lines)} invalid line(s):\\n" + '\\n'.join(bad_lines))

        if len(locations) < 2:
            st.error(\"Please provide at least two valid locations.\")
            st.stop()


        # Convert to DataFrame
        df = pd.DataFrame(locations, columns=['Name', 'Latitude', 'Longitude'])

        # Create distance matrix
        n = len(df)
        distances = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i, j] = haversine(df.iloc[i]['Latitude'], df.iloc[i]['Longitude'],
                                                df.iloc[j]['Latitude'], df.iloc[j]['Longitude'])

        # Display distance matrix
        dist_df = pd.DataFrame(distances, columns=df['Name'], index=df['Name'])
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
        central_index = np.argmin(avg_dists)
        central_location = df.iloc[central_index]['Name']
        st.subheader("Most Central Location")
        st.write(f"**{central_location}** is the most central location (lowest average distance to others: {avg_dists[central_index]:.2f} km)")

    except Exception as e:
        st.error(f"Error parsing input: {e}")



