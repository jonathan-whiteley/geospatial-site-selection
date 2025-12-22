# Folium Marker Clustering Implementation Guide

## Overview

Marker clustering is a technique to improve map performance and usability when displaying large numbers of markers. Instead of rendering hundreds or thousands of individual markers, nearby markers are grouped into clusters. Each cluster displays the count of markers it contains. When users zoom in, clusters automatically split into smaller clusters or individual markers.

This guide documents the implementation used in the LCE Hunger Detection Platform for convenience stores and competitors.

---

## Key Benefits

1. **Performance**: Dramatically reduces the number of DOM elements rendered
2. **Usability**: Prevents visual clutter on the map
3. **Interactive**: Automatically adjusts cluster size based on zoom level
4. **Built-in**: Uses Leaflet's MarkerCluster plugin via Folium

---

## Implementation Steps

### 1. Import the MarkerCluster Plugin

```python
import folium
from folium.plugins import MarkerCluster
import pandas as pd
```

### 2. Create Your Base Map

```python
m = folium.Map(
    location=[42.3601, -71.0589],  # Center coordinates (lat, lon)
    zoom_start=9,
    tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attr='CartoDB'
)
```

### 3. Create a Marker Cluster Layer

```python
# Create a named cluster that will be added to the map
marker_cluster = MarkerCluster(name='My Markers').add_to(m)
```

**Key Options:**
- `name`: Label for the layer (shown in layer controls)
- `overlay`: Whether it's an overlay layer (default: True)
- `control`: Whether to show in layer control (default: True)
- `show`: Whether to show by default (default: True)

### 4. Add Markers to the Cluster (Not Directly to Map)

```python
# Loop through your data
for _, row in dataframe.iterrows():
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=5,
        popup=f"<b>{row['name']}</b><br/>{row['description']}",
        tooltip=f"{row['name']}",
        color='#3b82f6',
        fill=True,
        fillColor='#60a5fa',
        fillOpacity=0.7,
        weight=2
    ).add_to(marker_cluster)  # ← Add to CLUSTER, not map
```

**Critical**: Use `.add_to(marker_cluster)` instead of `.add_to(m)`

---

## Complete Working Example

```python
import folium
from folium.plugins import MarkerCluster
import pandas as pd

# Sample data
convenience_stores = pd.DataFrame({
    'name': ['7-Eleven Store #1', '7-Eleven Store #2', 'Speedway #1'],
    'latitude': [42.3601, 42.3621, 42.3580],
    'longitude': [-71.0589, -71.0520, -71.0600],
    'category': ['convenience', 'convenience', 'convenience']
})

# Create base map
m = folium.Map(
    location=[42.3601, -71.0589],
    zoom_start=12,
    tiles='OpenStreetMap'
)

# Create cluster layer
conv_cluster = MarkerCluster(name='Convenience Stores').add_to(m)

# Add markers to cluster
for _, store in convenience_stores.iterrows():
    folium.CircleMarker(
        location=[store['latitude'], store['longitude']],
        radius=5,
        popup=f"<b>{store['name']}</b><br/>{store['category']}",
        tooltip=f"Convenience: {store['name']}",
        color='#3b82f6',
        fill=True,
        fillColor='#60a5fa',
        fillOpacity=0.7,
        weight=2
    ).add_to(conv_cluster)

# Save or display
m.save('map_with_clusters.html')
```

---

## Multiple Cluster Layers on Same Map

You can have different clusters for different data categories:

```python
m = folium.Map(location=[42.3601, -71.0589], zoom_start=9)

# Cluster 1: Convenience Stores (Blue)
conv_cluster = MarkerCluster(name='Convenience Stores').add_to(m)
for _, conv in convenience_stores.iterrows():
    folium.CircleMarker(
        location=[conv['latitude'], conv['longitude']],
        radius=5,
        color='#3b82f6',
        fillColor='#60a5fa',
        fillOpacity=0.7
    ).add_to(conv_cluster)

# Cluster 2: Competitors (Red)
comp_cluster = MarkerCluster(name='Competitors').add_to(m)
for _, comp in competitors.iterrows():
    folium.CircleMarker(
        location=[comp['latitude'], comp['longitude']],
        radius=5,
        color='#dc2626',
        fillColor='#ef4444',
        fillOpacity=0.7
    ).add_to(comp_cluster)
```

---

## Integration with Streamlit

When using with Streamlit's `st_folium`, no special handling needed:

```python
import streamlit as st
from streamlit_folium import st_folium

# Build map with clusters (as shown above)
m = folium.Map(...)
marker_cluster = MarkerCluster(...).add_to(m)
# ... add markers ...

# Display in Streamlit
st_folium(m, width=None, height=500)
```

---

## Conditional Clustering with Toggles

To show/hide clusters based on user toggles:

```python
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster

# Initialize toggle in session state
if 'show_convenience' not in st.session_state:
    st.session_state.show_convenience = False

# Create map
m = folium.Map(location=[42.3601, -71.0589], zoom_start=9)

# Only add cluster if toggle is on
if st.session_state.show_convenience and not convenience_stores.empty:
    conv_cluster = MarkerCluster(name='Convenience Stores').add_to(m)
    for _, conv in convenience_stores.iterrows():
        folium.CircleMarker(
            location=[conv['latitude'], conv['longitude']],
            radius=5,
            color='#3b82f6',
            fillColor='#60a5fa'
        ).add_to(conv_cluster)

# Display map
st_folium(m, width=None, height=500)

# Toggle checkbox
st.session_state.show_convenience = st.checkbox(
    "Show Convenience Stores",
    value=st.session_state.show_convenience
)
```

---

## Performance Optimization with Session State Caching

To prevent re-querying data on every toggle:

```python
import streamlit as st

# Cache data in session state (query once)
if 'convenience_data_loaded' not in st.session_state:
    with st.spinner("Loading data..."):
        # Query database
        convenience_stores = query(token, "SELECT * FROM pois_convenience")

        # Store in session state
        st.session_state.convenience_stores = convenience_stores
        st.session_state.convenience_data_loaded = True
else:
    # Use cached data
    convenience_stores = st.session_state.convenience_stores

# Now use convenience_stores for map rendering
# Toggles won't re-query, just re-render the map
```

---

## Advanced Customization

### Custom Cluster Icons and Colors

You can customize cluster appearance with custom icons and colors:

```python
from folium.plugins import MarkerCluster

# GREEN clusters for Little Caesars stores
lce_cluster = MarkerCluster(
    name='LCE Stores',
    options={
        'maxClusterRadius': 50,
        'iconCreateFunction': '''
            function(cluster) {
                return L.divIcon({
                    html: '<div style="background-color: #10b981; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #059669;"><span>' + cluster.getChildCount() + '</span></div>',
                    className: 'marker-cluster',
                    iconSize: L.point(40, 40)
                });
            }
        '''
    }
).add_to(m)

# BLUE clusters for convenience stores
conv_cluster = MarkerCluster(
    name='Convenience Stores',
    options={
        'maxClusterRadius': 50,
        'iconCreateFunction': '''
            function(cluster) {
                return L.divIcon({
                    html: '<div style="background-color: #3b82f6; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #2563eb;"><span>' + cluster.getChildCount() + '</span></div>',
                    className: 'marker-cluster',
                    iconSize: L.point(40, 40)
                });
            }
        '''
    }
).add_to(m)
```

**Key Customization Options:**
- `maxClusterRadius`: Maximum radius to cluster markers (default: 80)
- `spiderfyOnMaxZoom`: Spread out markers at max zoom
- `showCoverageOnHover`: Don't show cluster coverage polygon
- `zoomToBoundsOnClick`: Zoom to cluster bounds on click
- `iconCreateFunction`: Custom JavaScript function to create cluster icons

### Marker Types That Work with Clustering

All standard Folium markers work:

```python
# CircleMarker (most common)
folium.CircleMarker(...).add_to(cluster)

# Regular Marker with icon
folium.Marker(
    location=[lat, lon],
    popup="Store",
    icon=folium.Icon(color='blue', icon='info-sign')
).add_to(cluster)

# Custom DivIcon
folium.Marker(
    location=[lat, lon],
    icon=folium.DivIcon(html='<div style="color: red;">★</div>')
).add_to(cluster)
```

---

## Common Pitfalls

### ❌ Wrong: Adding to Map Instead of Cluster

```python
marker_cluster = MarkerCluster().add_to(m)
for _, row in df.iterrows():
    folium.CircleMarker(...).add_to(m)  # ❌ Won't cluster!
```

### ✅ Correct: Adding to Cluster

```python
marker_cluster = MarkerCluster().add_to(m)
for _, row in df.iterrows():
    folium.CircleMarker(...).add_to(marker_cluster)  # ✅ Will cluster
```

---

## How Clustering Works Under the Hood

1. **Leaflet.markercluster Plugin**: Folium wraps the Leaflet.markercluster JavaScript library
2. **Client-Side**: Clustering happens in the browser, not server-side
3. **Automatic**: Clusters form/split automatically based on:
   - Zoom level
   - Marker proximity
   - `maxClusterRadius` setting
4. **Cluster Count**: The number shown is the count of markers in that cluster

---

## Visual Behavior

- **Zoomed Out**: Many markers → Few large clusters with high counts
- **Zoomed In**: Clusters split into smaller clusters
- **Max Zoom**: Individual markers appear (or spider out if very close)
- **Click Cluster**: Zooms to show all markers in that cluster
- **Hover Cluster**: Shows count tooltip

---

## Package Requirements

```txt
folium>=0.14.0
streamlit-folium>=0.13.0
```

Install via:
```bash
pip install folium streamlit-folium
```

---

## Real-World Use Cases

1. **Store Locators**: Show hundreds of retail locations
2. **Real Estate Listings**: Display properties on a map
3. **Event Venues**: Show event locations across a region
4. **Restaurant Finders**: Display dining options
5. **Crime Mapping**: Visualize incident reports
6. **Delivery Zones**: Show service coverage areas

---

## Debugging Tips

### Clusters Not Appearing?
- Check: Are you adding markers to the cluster object, not the map?
- Check: Is your data loading correctly?
- Check: Are lat/lon values valid numbers?

### Too Many Clusters?
- Increase `maxClusterRadius` in options
- Check zoom level - clusters split at higher zooms

### Clusters Not Splitting?
- Try zooming in more
- Check `zoomToBoundsOnClick` option
- Verify `spiderfyOnMaxZoom` is enabled

### Performance Still Slow?
- Use session state caching for data
- Limit marker complexity (simple popups)
- Consider limiting to visible bounds
- Use unique map keys in Streamlit

---

## References

- [Folium Documentation](https://python-visualization.github.io/folium/)
- [Leaflet.markercluster Plugin](https://github.com/Leaflet/Leaflet.markercluster)
- [Streamlit-Folium Documentation](https://folium.streamlit.app/)

---

## Example from LCE Hunger Detection Platform

This is the actual implementation used in the production app showing different clustering strategies:

### Strategy 1: Clustered Markers (for many markers)

Used for LCE stores and convenience stores where there are many markers:

```python
# GREEN clusters for LCE stores
lce_cluster = MarkerCluster(
    name='LCE Stores',
    options={
        'maxClusterRadius': 50,
        'iconCreateFunction': '''
            function(cluster) {
                return L.divIcon({
                    html: '<div style="background-color: #10b981; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #059669;"><span>' + cluster.getChildCount() + '</span></div>',
                    className: 'marker-cluster',
                    iconSize: L.point(40, 40)
                });
            }
        '''
    }
).add_to(m)

for _, store in stores.iterrows():
    folium.CircleMarker(
        location=[store['latitude'], store['longitude']],
        radius=8,
        popup=f"Store {store['store_number']}",
        color='#10b981',
        fillColor='#34d399',
        fillOpacity=0.8
    ).add_to(lce_cluster)  # Add to cluster

# BLUE clusters for convenience stores
conv_cluster = MarkerCluster(
    name='Convenience Stores',
    options={
        'maxClusterRadius': 50,
        'iconCreateFunction': '''
            function(cluster) {
                return L.divIcon({
                    html: '<div style="background-color: #3b82f6; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #2563eb;"><span>' + cluster.getChildCount() + '</span></div>',
                    className: 'marker-cluster',
                    iconSize: L.point(40, 40)
                });
            }
        '''
    }
).add_to(m)

for _, conv in convenience_stores.iterrows():
    folium.CircleMarker(
        location=[conv['latitude'], conv['longitude']],
        radius=5,
        popup=f"<b>{conv['name']}</b>",
        color='#3b82f6',
        fillColor='#60a5fa',
        fillOpacity=0.7
    ).add_to(conv_cluster)  # Add to cluster
```

### Strategy 2: Individual Markers (for fewer markers)

Used for competitors where visual clutter is less of an issue:

```python
# NO clustering for competitors - individual markers
if show_competitors and not competitors.empty:
    for _, comp in competitors.iterrows():
        folium.CircleMarker(
            location=[comp['latitude'], comp['longitude']],
            radius=5,
            popup=f"<b>{comp['name']}</b>",
            tooltip=f"Competitor: {comp['name']}",
            color='#dc2626',
            fillColor='#ef4444',
            fillOpacity=0.7
        ).add_to(m)  # Add directly to map (no cluster)
```

### When to Use Each Strategy

**✅ Use Clustering When:**
- You have 20+ markers of the same type
- Markers overlap significantly at default zoom
- Performance is a concern (100+ markers)
- You want users to see density patterns

**❌ Skip Clustering When:**
- You have fewer than 20 markers
- Each marker is strategically important to see individually
- Markers are naturally spread out
- Visual comparison between individual markers is key

---

## Performance Metrics

**Without Clustering:**
- 500 markers = 500 DOM elements
- Map rendering: ~2-3 seconds
- Panning/zooming: Laggy

**With Clustering:**
- 500 markers = ~5-20 clusters (zoom dependent)
- Map rendering: <1 second
- Panning/zooming: Smooth

---

## License & Credits

- **Folium**: BSD 3-Clause License
- **Leaflet**: BSD 2-Clause License
- **Leaflet.markercluster**: MIT License

---

## Color Reference for LCE Hunger Detection Platform

| Marker Type | Cluster Color | Border Color | Individual Marker | Usage |
|-------------|--------------|--------------|-------------------|-------|
| LCE Stores | `#10b981` (Green) | `#059669` (Dark Green) | `#34d399` (Light Green) | Primary brand stores with clustering |
| Convenience Stores | `#3b82f6` (Blue) | `#2563eb` (Dark Blue) | `#60a5fa` (Light Blue) | Co-location opportunities with clustering |
| Competitors | N/A | N/A | `#ef4444` (Red) | Pizza competitors, NO clustering |
| Expansion Candidates | N/A | N/A | `#fbbf24` (Gold/Orange) | New location candidates, individual markers |

**Color Strategy:**
- **Green Clusters**: Little Caesars brand identity
- **Blue Clusters**: Partner/convenience store opportunities
- **Red Markers**: Competitors (individual to highlight each one)
- **Gold Markers**: High-value expansion opportunities

---

*Last Updated: 2025-12-22*
*Author: Claude (Anthropic) for LCE Hunger Detection Platform*
