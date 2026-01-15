# App Enhancement Implementation Plan

## Objective

Enhance the geospatial retail site selection app with unified map display, improved metrics, clustering, and dynamic filtering.

---

## User Review Required

> [!IMPORTANT] > **Data Schema Investigation**: The `viz_existing_stores` table currently does not include `annual_sales` column. This needs to be added to the gold layer pipeline or sourced from another table. Please confirm where actual sales data should come from.

> [!WARNING] > **13 vs 12 MA Stores**: Need to investigate why only 12 MA stores are displaying instead of 13. This may be a data issue in the source table or a filtering issue in the isochrones query.

---

## Proposed Changes

### Data Layer

#### [MODIFY] [viz_layer_prep.ipynb](file:///Users/jonathan.whiteley/Desktop/Databricks_Apps/projects/geospatial/geospatial-retail-site-selection/transformations/03_gold/viz_layer_prep.ipynb)

- Add `annual_sales` column to `viz_existing_stores` table (source TBD)
- Investigate store count discrepancy (13 vs 12)

---

### App Backend

#### [MODIFY] [app_v2.py](file:///Users/jonathan.whiteley/Desktop/Databricks_Apps/projects/geospatial/geospatial-retail-site-selection/app/app_v2.py)

**1. Update Data Loading (lines 105-111, 249-254)**

- Add `annual_sales` to SELECT for `viz_existing_stores`
- Filter isochrones to MA stores only by adding `WHERE state = 'MA'` or join condition

**2. Update Current Stores Metrics (lines 1940-1965)**
Replace current metrics with:
| Card | Value |
|------|-------|
| Current Stores | Count of existing stores |
| Total Annual Sales | Sum of `annual_sales` for all current stores |
| Convenience Stores | Count from convenience stores data |
| Competitor Stores | Count from competitors data |

**3. Unify Map Display - Both Tabs Show Same Map (lines 1382-1756)**

- Current Network mode (`renderCurrentNetworkMap`) should render:
  - H3 hexagons with sales heatmap
  - Expansion candidates (with clustering)
  - Current stores (with clustering showing total sales)
  - Convenience stores, competitors
- Remove duplicate rendering logic; call same render function for both modes
- Keep Refine/Optimize sections only visible in Expansion tab

**4. Unified Layer Controls (lines 2019-2057)**
Replace Current Network layer controls with Expansion-style controls:

```javascript
// Unified layer controls for both modes:
- Expansion Candidates
- H3 Heatmap (Sales)
- Current Stores
- Candidate Isochrones (NEW - lighter red, off by default)
- Convenience Stores
- Competitors
```

**5. Add Expansion Metrics Below Current Metrics (lines 1967-2011)**
Both tabs show:

1. **Current Stores Metrics** (4 cards: stores, total sales, convenience, competitors)
2. **Expansion Metrics** (4 cards: candidates, partnership %, revenue potential, median revenue)

**6. Decouple H3 Hexagons from Candidates Layer (lines 1590-1657)**
When `layers.candidates` is unchecked:

- Keep H3 hexagons visible on map
- Hide only the markers and clustering
- Modify condition from `if (layers.candidates && data.candidates)` to separate hexagon and marker rendering

**7. Add Current Stores Clustering (lines 1572-1587)**
Create a `currentStoreClusterGroup` similar to `candidateClusterGroup`:

- Cluster icon shows total actual sales (e.g., "$12.5M")
- Use green color scheme for clusters

**8. Dynamic Sales Gradient (lines 1500-1503)**
Update `salesRange` calculation to use filtered candidates:

```javascript
const filteredCandidates = applyFilters(data.candidates);
const salesValues = filteredCandidates.map((c) => c.predicted_annual_sales);
salesRange.min = Math.min(...salesValues);
salesRange.max = Math.max(...salesValues);
```

Also update legend labels dynamically.

**9. Add Candidate Isochrones Layer (NEW)**

- Add layer toggle: `layers.candidate_isochrones = false` (default off)
- Create isochrones around each expansion candidate
- Use lighter red color: `rgba(239, 68, 68, 0.15)` fill, `#fca5a5` stroke

**10. Update Detail Panel for Current Stores (lines 1766-1817)**
When clicking current store, show `annual_sales` in detail panel:

```javascript
if (storeData.annual_sales !== undefined) {
  detailHTML += `
        <div class="metric-row">
            <div class="metric-row-label">Annual Sales</div>
            <div class="metric-row-value">$${storeData.annual_sales.toLocaleString()}</div>
        </div>
    `;
}
```

**11. Filter Isochrones to MA Only (lines 120-129)**
Update isochrones query:

```sql
SELECT iso.location_id as store_number, ST_AsGeoJSON(iso.geometry) as isochrone_geojson
FROM {silver_schema}.isochrones_lce iso
INNER JOIN {gold_schema}.viz_existing_stores stores
  ON iso.location_id = stores.store_number
WHERE stores.state = 'MA'
```

---

## Summary of UI Changes

### Existing Tab (Current Network Mode)

- **Metrics**: 4 Current Store cards + 4 Expansion Metrics cards
- **Map**: Same as Expansion (hexagons, candidates, current stores clustered)
- **Controls**: Layer toggles only (no Refine/Optimize)

### Expansion Tab

- **Metrics**: Same as Existing tab
- **Map**: Same as Existing tab
- **Controls**: Layer toggles + Refine sliders + Optimize section

---

## Verification Plan

### Automated Tests

```bash
# Run Streamlit app locally
cd app && streamlit run app_v2.py
```

### Manual Verification

1. Verify both tabs show identical map with all layers
2. Confirm 13 MA stores display (after data fix)
3. Test layer toggles - unchecking Candidates keeps hexagons visible
4. Verify current store clusters show total sales
5. Test gradient adapts when filters applied
6. Confirm candidate isochrones render in light red when enabled
7. Click current store → detail panel shows annual sales
