# Map Visualization Enhancement Plan

## Objective
Update the map in `app/app_v2.py` to display H3 hexagon heatmaps with sales-based color gradients, show total sales in cluster icons, and add layer controls.

---

## Changes Summary

**File:** `app/app_v2.py`

### 1. Add Color Gradient Function
Add JavaScript function to interpolate white → red based on sales:
```javascript
function getSalesColor(sales, minSales, maxSales) {
    const ratio = Math.max(0, Math.min(1, (sales - minSales) / (maxSales - minSales)));
    const r = 255;
    const g = Math.round(255 * (1 - ratio));
    const b = Math.round(255 * (1 - ratio));
    return `rgb(${r}, ${g}, ${b})`;
}
```
- Lowest sales → white (`rgb(255, 255, 255)`)
- Highest sales → red (`rgb(255, 0, 0)`)

### 2. Hexagon Heatmap Coloring
Modify hexagon rendering to apply sales-based gradient:
- Calculate min/max `predicted_annual_sales` from all candidates
- Apply `getSalesColor()` to each hexagon's `fillColor`
- Set `fillOpacity: 0.7` for visibility

### 3. Cluster Icon Shows Total Sales
Replace cluster count with formatted total sales:
```javascript
iconCreateFunction: function(cluster) {
    const markers = cluster.getAllChildMarkers();
    let totalSales = 0;
    markers.forEach(m => { totalSales += m.options.predicted_sales || 0; });
    const formattedSales = '$' + (totalSales / 1000000).toFixed(1) + 'M';
    return L.divIcon({
        html: '<div class="cluster-sales">' + formattedSales + '</div>',
        className: 'sales-cluster-icon',
        iconSize: [50, 50]
    });
}
```

### 4. Separate Layer Controls
Create two toggleable layers:
- **Hexagons** (default: ON) - H3 polygons with heatmap colors
- **Points** (default: OFF) - Marker pins for candidate locations

Add layer control using Leaflet's built-in control:
```javascript
const hexLayer = L.layerGroup();
const pointLayer = L.layerGroup();
L.control.layers(null, {
    'Hexagons': hexLayer,
    'Points': pointLayer
}, {collapsed: false}).addTo(map);
```

### 5. Add Legend
Add a color legend showing the sales gradient scale:
```javascript
const legend = L.control({position: 'bottomright'});
legend.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'legend');
    div.innerHTML = `
        <div class="legend-title">Predicted Sales</div>
        <div class="legend-gradient"></div>
        <div class="legend-labels">
            <span>$${minSales/1000}K</span>
            <span>$${maxSales/1000}K</span>
        </div>
    `;
    return div;
};
```

---

## Implementation Steps

1. **Add helper functions** - `getSalesColor()`, `formatSales()`
2. **Calculate sales range** - Extract min/max from candidates data
3. **Update hexagon rendering** - Apply dynamic fillColor
4. **Update cluster icon** - Sum sales and display formatted total
5. **Create separate layers** - Split hexagons and points into LayerGroups
6. **Add layer control** - Leaflet control with checkboxes
7. **Add legend** - Color gradient legend in corner
8. **Add CSS styles** - Styles for cluster icons and legend

---

## Verification Plan

1. Deploy updated app to Databricks
2. Verify hexagons display white-to-red gradient based on sales
3. Verify clusters show total sales (e.g., "$5.2M") instead of count
4. Test layer toggle - hexagons ON by default, points OFF
5. Confirm legend displays correct min/max values
6. Test zoom behavior - clusters expand/contract correctly
