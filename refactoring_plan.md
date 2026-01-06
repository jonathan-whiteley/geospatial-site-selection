# Refactoring Plan: Move App Logic to Pipeline Transformations

## Executive Summary

The current app_v2.py performs expensive computations at runtime (O(n²) distance calculations, point-in-polygon checks, filtering, aggregations) that should be pre-computed in the gold layer. Additionally, the existing `viz_*` tables in gold are **not being used** by the app.

This plan restructures the data flow so gold layer tables contain everything needed for visualization, with minimal computation at the app layer.

---

## Current State Analysis

### What the App Currently Does at Runtime

| Computation | Complexity | Location | Impact |
|---|---|---|---|
| **Haversine distance calculations** | O(n²) per optimization | JavaScript lines 1733-1742 | **HIGH** - runs in loop |
| **Optimization algorithm** | O(n × k) where k = max_stores | JavaScript lines 1697-1730 | **HIGH** - recalculates on every slider change |
| **Point-in-polygon (isochrone check)** | O(vertices × candidates) | JavaScript lines 1225-1298 | **MEDIUM** - runs on detail panel open |
| **Filtering (min_sales, min_pop)** | O(n) | JavaScript lines 1120-1126 | **LOW** - simple but unnecessary |
| **Metric aggregations** | O(n) | JavaScript lines 1434-1499 | **LOW** - recalculates on every render |

### Tables Currently Queried (All Silver/Bronze!)

```
App queries SILVER directly, bypassing GOLD viz_* tables:
├── geo_silver.existing_stores_h3
├── geo_silver.isochrones_lce
├── geo_silver.isochrones_convenience
├── geo_silver.pois_convenience
├── geo_silver.pois_competitors
├── geo_bronze.lce_locations_mass
├── geo_bronze.census_states
└── geo_gold.expansion_candidates_h3_enhanced  (only gold table used)
```

### Unused Gold Tables (Currently Wasted Computation)

```
These viz_* tables exist but app ignores them:
├── viz_h3_grid           (MA grid)
├── viz_expansion_candidates (normalized scores, percentile rank)
├── viz_existing_stores   (pre-joined geometry, marker_type)
├── viz_competitors       (standardized, with marker_type)
└── viz_convenience       (isochrones with drive_time)
```

---

## Recommended Architecture

### Target Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      APP LAYER (Simplified)                  │
│                                                              │
│  On Load:                                                   │
│  └─ Query viz_* tables only (no silver/bronze)             │
│                                                              │
│  At Runtime:                                                │
│  ├─ "Run Optimization" → Lookup pre-computed results       │
│  ├─ Filter changes → Filter already-loaded data (O(n))     │
│  └─ Detail panel click → Read pre-joined columns directly  │
│                                                              │
│  NO JavaScript Haversine, NO point-in-polygon, NO sorting  │
└─────────────────────────────────────────────────────────────┘
                           ↑
                           │ Simple SELECT queries
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    GOLD LAYER (Pre-computed)                 │
│                                                              │
│  NEW TABLES:                                                │
│  ├─ viz_optimization_results     (pre-computed selections)  │
│  └─ viz_network_metrics          (singleton aggregates)    │
│                                                              │
│  ENHANCED TABLES (consolidate logic into existing):        │
│  ├─ viz_expansion_candidates     (+ distance columns,      │
│  │                                 + convenience proximity) │
│  ├─ viz_convenience              (+ candidate proximity    │
│  │                                 pre-joined)             │
│  ├─ viz_existing_stores          (already good)             │
│  └─ viz_competitors              (already good)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Pipeline Transformations (New/Enhanced Tables)

### 1.1 NEW TABLE: `viz_network_metrics`

**Purpose:** Pre-computed aggregate metrics for dashboard display (singleton row)

```sql
-- gold/viz_network_metrics.sql
CREATE OR REPLACE TABLE geo_gold.viz_network_metrics AS
SELECT
  -- Existing network metrics
  COUNT(*) as total_existing_stores,
  AVG(population) as avg_store_population,
  AVG(total_poi) as avg_store_poi,
  SUM(population) as total_network_population,

  -- Candidate pool metrics
  (SELECT COUNT(*) FROM geo_gold.expansion_candidates_h3_enhanced) as total_candidates,
  (SELECT AVG(predicted_annual_sales) FROM geo_gold.expansion_candidates_h3_enhanced) as avg_candidate_sales,
  (SELECT AVG(population) FROM geo_gold.expansion_candidates_h3_enhanced) as avg_candidate_population,

  -- Percentile thresholds for quick filtering
  (SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY predicted_annual_sales)
   FROM geo_gold.expansion_candidates_h3_enhanced) as sales_p25,
  (SELECT PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY predicted_annual_sales)
   FROM geo_gold.expansion_candidates_h3_enhanced) as sales_p50,
  (SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY predicted_annual_sales)
   FROM geo_gold.expansion_candidates_h3_enhanced) as sales_p75,

  CURRENT_TIMESTAMP() as last_updated
FROM geo_silver.existing_stores_h3
```

**App Change:** Replace runtime aggregation loops with single row lookup.

---

### 1.2 ENHANCED TABLE: `viz_expansion_candidates` (Consolidated)

**Purpose:** Add distance and convenience proximity columns directly to candidates table (no separate tables needed)

This consolidates what would have been `viz_candidate_distances` and `viz_convenience_proximity` into a single enhanced table.

```sql
-- gold/viz_expansion_candidates.sql
CREATE OR REPLACE TABLE geo_gold.viz_expansion_candidates AS
WITH
-- Pre-compute minimum distance to existing stores for each candidate
candidate_distances AS (
  SELECT
    c.h3_cell_id,
    MIN(
      3959 * 2 * ASIN(SQRT(
        POWER(SIN(RADIANS(s.latitude - c.latitude) / 2), 2) +
        COS(RADIANS(c.latitude)) * COS(RADIANS(s.latitude)) *
        POWER(SIN(RADIANS(s.longitude - c.longitude) / 2), 2)
      ))
    ) as min_distance_to_existing,
    -- Also get nearest store info for detail panel
    FIRST_VALUE(s.store_number) OVER (
      PARTITION BY c.h3_cell_id
      ORDER BY 3959 * 2 * ASIN(SQRT(
        POWER(SIN(RADIANS(s.latitude - c.latitude) / 2), 2) +
        COS(RADIANS(c.latitude)) * COS(RADIANS(s.latitude)) *
        POWER(SIN(RADIANS(s.longitude - c.longitude) / 2), 2)
      ))
    ) as nearest_existing_store
  FROM geo_gold.expansion_candidates_h3_enhanced c
  CROSS JOIN geo_silver.existing_stores_h3 s
  GROUP BY c.h3_cell_id
),

-- Pre-compute convenience store proximity (replaces point-in-polygon at runtime)
convenience_proximity AS (
  SELECT
    c.h3_cell_id,
    FIRST_VALUE(cv.id) as nearest_convenience_id,
    FIRST_VALUE(cv.store_type) as convenience_store_type,
    FIRST_VALUE(cv.city) as convenience_city,
    FIRST_VALUE(cv.name) as convenience_store_name,
    FIRST_VALUE(cv.drive_time_minutes) as convenience_drive_time,
    TRUE as within_convenience_isochrone
  FROM geo_gold.expansion_candidates_h3_enhanced c
  INNER JOIN geo_silver.isochrones_convenience cv
    ON ST_CONTAINS(cv.geometry, ST_POINT(c.longitude, c.latitude))
  GROUP BY c.h3_cell_id
)

SELECT
  c.*,

  -- Distance columns (replaces runtime Haversine)
  COALESCE(d.min_distance_to_existing, 999) as min_distance_to_existing,
  d.nearest_existing_store,

  -- Convenience proximity columns (replaces runtime point-in-polygon)
  COALESCE(cp.within_convenience_isochrone, FALSE) as within_convenience_isochrone,
  cp.convenience_store_type,
  cp.convenience_city,
  cp.convenience_store_name,
  cp.convenience_drive_time,

  -- Fulfillment recommendation (pre-computed!)
  CASE
    WHEN cp.within_convenience_isochrone THEN 'partner'
    ELSE 'new_store'
  END as fulfillment_strategy,

  -- Quality tier for quick filtering
  CASE
    WHEN percentile_rank >= 0.75 THEN 'top_25'
    WHEN percentile_rank >= 0.50 THEN 'top_50'
    WHEN percentile_rank >= 0.25 THEN 'top_75'
    ELSE 'bottom_25'
  END as quality_tier,

  -- GeoJSON for map rendering (avoid runtime conversion)
  ST_AsGeoJSON(geometry) as geometry_geojson,

  -- Center point for markers
  ST_Y(ST_Centroid(geometry)) as center_lat,
  ST_X(ST_Centroid(geometry)) as center_lon

FROM geo_gold.expansion_candidates_h3_enhanced c
LEFT JOIN candidate_distances d ON c.h3_cell_id = d.h3_cell_id
LEFT JOIN convenience_proximity cp ON c.h3_cell_id = cp.h3_cell_id
```

**Key columns added:**
| Column | Purpose | Replaces |
|--------|---------|----------|
| `min_distance_to_existing` | Filter candidates by distance to existing stores | Runtime Haversine in optimization loop |
| `nearest_existing_store` | Show in detail panel | Runtime distance calculation |
| `within_convenience_isochrone` | Determine fulfillment strategy | JavaScript `pointInPolygon()` |
| `convenience_store_name` | Show partner info in detail panel | Runtime isochrone lookup |
| `fulfillment_strategy` | Pre-computed recommendation | Runtime `checkConvenienceStoreProximity()` |

**App Change:** Filter by pre-computed columns instead of calculating at runtime:
```python
# Before (JavaScript): O(n²) distance checks in optimization loop
# After (SQL): Simple column filter
candidates_filtered = candidates_df[candidates_df['min_distance_to_existing'] >= min_dist_existing]
```

---

### 1.3 ENHANCED TABLE: `viz_convenience` (With Candidate Proximity)

**Purpose:** Add pre-joined candidate proximity info to convenience store isochrones

```sql
-- gold/viz_convenience.sql
CREATE OR REPLACE TABLE geo_gold.viz_convenience AS
SELECT
  cv.*,

  -- Count of expansion candidates within this isochrone
  (SELECT COUNT(*)
   FROM geo_gold.expansion_candidates_h3_enhanced c
   WHERE ST_CONTAINS(cv.geometry, ST_POINT(c.longitude, c.latitude))
  ) as candidate_count_in_isochrone,

  -- Total predicted sales of candidates in isochrone
  (SELECT COALESCE(SUM(c.predicted_annual_sales), 0)
   FROM geo_gold.expansion_candidates_h3_enhanced c
   WHERE ST_CONTAINS(cv.geometry, ST_POINT(c.longitude, c.latitude))
  ) as total_candidate_sales_in_isochrone,

  -- Array of candidate H3 IDs within isochrone (for quick lookup)
  (SELECT COLLECT_LIST(c.h3_cell_id)
   FROM geo_gold.expansion_candidates_h3_enhanced c
   WHERE ST_CONTAINS(cv.geometry, ST_POINT(c.longitude, c.latitude))
  ) as candidate_h3_cells_in_isochrone,

  -- GeoJSON for map rendering
  ST_AsGeoJSON(geometry) as geometry_geojson,

  -- Marker type for styling
  'convenience' as marker_type

FROM geo_silver.isochrones_convenience cv
```

**Key columns added:**
| Column | Purpose |
|--------|---------|
| `candidate_count_in_isochrone` | Show partnership potential in convenience store popups |
| `total_candidate_sales_in_isochrone` | Prioritize convenience stores by expansion opportunity |
| `candidate_h3_cells_in_isochrone` | Quick reverse lookup from convenience store to candidates |

**App Change:** When displaying convenience store info, show partnership potential directly:
```python
# Show in convenience store popup
f"Partnership Opportunities: {store.candidate_count_in_isochrone} candidates"
f"Potential Revenue: ${store.total_candidate_sales_in_isochrone:,.0f}"
```

---

### 1.4 NEW TABLE: `viz_optimization_results`

**Purpose:** Pre-computed optimization results for discrete parameter combinations

This is the highest-impact change. Instead of running O(n²) optimization at runtime, pre-compute results for common parameter combinations.

```sql
-- gold/viz_optimization_results.sql
-- Parameters grid: max_stores [5,10,15,20,25], min_dist_new [1,2,3,5], min_dist_existing [1,2,3,5]

CREATE OR REPLACE TABLE geo_gold.viz_optimization_results (
  -- Parameter combination
  max_stores INT,
  min_distance_new DOUBLE,
  min_distance_existing DOUBLE,

  -- Result arrays
  selected_h3_cells ARRAY<STRING>,        -- Ordered list of selected candidate IDs
  selected_count INT,                       -- Number of candidates selected
  total_predicted_sales DOUBLE,            -- Sum of sales for selected

  -- Metadata
  computed_at TIMESTAMP
);
```

**Python notebook to populate:**

```python
# gold/compute_optimization_results.py
from itertools import product

# Parameter grid
max_stores_options = [5, 10, 15, 20, 25, 30]
min_dist_new_options = [1.0, 2.0, 3.0, 5.0]
min_dist_existing_options = [1.0, 2.0, 3.0, 5.0]

# Load data once
candidates_df = spark.table("geo_gold.expansion_candidates_h3_enhanced") \
    .join(spark.table("geo_gold.viz_candidate_distances"), "h3_cell_id") \
    .toPandas()

results = []
for max_stores, min_new, min_existing in product(max_stores_options, min_dist_new_options, min_dist_existing_options):
    selected = run_optimization(candidates_df, max_stores, min_new, min_existing)
    results.append({
        'max_stores': max_stores,
        'min_distance_new': min_new,
        'min_distance_existing': min_existing,
        'selected_h3_cells': selected['h3_cell_id'].tolist(),
        'selected_count': len(selected),
        'total_predicted_sales': selected['predicted_annual_sales'].sum()
    })

# Write to Delta
spark.createDataFrame(results).write.mode("overwrite").saveAsTable("geo_gold.viz_optimization_results")
```

**App Change:** Slider changes trigger lookup instead of recalculation:
```python
# Before: Run optimization in JavaScript on every slider change
# After:
@st.cache_data
def get_optimization_result(max_stores, min_dist_new, min_dist_existing):
    # Round to nearest pre-computed parameter
    return spark.sql(f"""
        SELECT * FROM geo_gold.viz_optimization_results
        WHERE max_stores = {max_stores}
          AND min_distance_new = {min_dist_new}
          AND min_distance_existing = {min_dist_existing}
    """).first()
```

---

## Phase 2: App Layer Refactoring - Detailed Behavior Changes

This section details exactly what changes in the app for each user interaction.

---

### 2.0 "Run Optimization" Button - Detailed Behavior Change

**Current Behavior (app_v2.py lines 1659-1694):**

When user clicks "▶️ Run Optimization" button:

```
1. Button click triggers runOptimization() in JavaScript
2. JS sends message to Streamlit backend via setComponentValue()
3. Backend calls run_optimization() Python function (lines 213-244)
4. Python sorts candidates by predicted_annual_sales (descending)
5. FOR EACH candidate (O(n)):
   a. FOR EACH existing store: Calculate Haversine distance (O(m))
   b. Check if distance < min_dist_existing → reject if true
   c. FOR EACH already-selected candidate: Calculate Haversine distance (O(k))
   d. Check if distance < min_dist_new → reject if true
   e. If passes all checks, add to selected list
6. Stop when max_stores reached
7. Return selected candidates to JavaScript
8. JS updates optimizationResults and re-renders map
```

**Total complexity:** O(n × m) + O(n × k) where n=candidates, m=existing stores, k=selected

**New Behavior (with pre-computed optimization):**

```
1. Button click triggers lookupOptimization() in JavaScript
2. JS reads current slider values (max_stores, min_dist_new, min_dist_existing)
3. JS snaps parameters to nearest pre-computed values
4. JS filters local optimizationResultsCache by parameter combination
5. Immediately returns pre-computed selected_h3_cells array
6. JS updates optimizationResults and re-renders map
```

**Total complexity:** O(1) lookup + O(k) to map h3_cell_ids to candidate objects

**Implementation:**

```javascript
// NEW: Load all optimization results at app startup
const optimizationResultsCache = {json.dumps(optimization_results_df.to_dict('records'))};

// NEW: Replace runOptimization() with lookup
function lookupOptimization() {{
    const params = {{
        max_stores: snapToGrid(optimizationParams.max_stores, [5,10,15,20,25,30]),
        min_dist_new: snapToGrid(optimizationParams.min_dist_new, [1,2,3,5]),
        min_dist_existing: snapToGrid(optimizationParams.min_dist_existing, [1,2,3,5])
    }};

    // O(1) lookup from pre-loaded cache
    const result = optimizationResultsCache.find(r =>
        r.max_stores === params.max_stores &&
        r.min_distance_new === params.min_dist_new &&
        r.min_distance_existing === params.min_dist_existing
    );

    if (result) {{
        // Map h3_cell_ids back to full candidate objects
        optimizationResults = result.selected_h3_cells.map(h3 =>
            expansionData.candidates.find(c => c.h3_cell_id === h3)
        ).filter(Boolean);

        renderMap();
        updateMetrics();
    }}
}}

function snapToGrid(value, grid) {{
    return grid.reduce((prev, curr) =>
        Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
    );
}}
```

**User Experience Impact:**
| Aspect | Before | After |
|--------|--------|-------|
| Button response time | 500-2000ms | <50ms |
| Spinner shown | Yes, "⏳ Running..." | No spinner needed |
| Network request | Yes (Streamlit backend) | No (local lookup) |
| Parameter flexibility | Any value | Snapped to grid |

**Trade-off:** Users can only select discrete parameter combinations. Add UI feedback showing which pre-computed combination is being used.

---

### 2.1 Right Panel Detail - Detailed Behavior Change

**Current Behavior (app_v2.py lines 1300-1430):**

When user clicks on a map marker (store or candidate):

```
1. Click triggers showDetailPanel(storeData) in JavaScript
2. JS builds HTML for basic info (population, POI count, predicted sales)
3. IF expansion mode AND candidate has predicted_annual_sales:
   a. Call checkConvenienceStoreProximity(storeData)
   b. This function iterates through ALL convenience isochrones
   c. FOR EACH isochrone:
      - Parse GeoJSON geometry
      - Run pointInPolygon() ray-casting algorithm (O(vertices))
      - If inside, return store info and exit
   d. Return null if not in any isochrone
4. Based on proximity result, show either:
   - "🤝 Partner with Convenience Store" card
   - "🏪 Open New Store" card
5. Insert HTML into detail-content div
6. Slide panel open
```

**Complexity per click:** O(isochrones × vertices_per_isochrone) ≈ O(50 × 100) = O(5000)

**New Behavior (with pre-computed columns):**

```
1. Click triggers showDetailPanel(storeData) in JavaScript
2. JS builds HTML for basic info (same as before)
3. IF expansion mode AND candidate has predicted_annual_sales:
   a. READ storeData.fulfillment_strategy (pre-computed column)
   b. READ storeData.convenience_store_name (pre-computed column)
   c. READ storeData.convenience_city (pre-computed column)
   d. READ storeData.min_distance_to_existing (pre-computed column)
4. Based on fulfillment_strategy value, show either:
   - "🤝 Partner with Convenience Store" card (if 'partner')
   - "🏪 Open New Store" card (if 'new_store')
5. Insert HTML into detail-content div
6. Slide panel open
```

**Complexity per click:** O(1) - just reading object properties

**Implementation:**

```javascript
// OLD: Complex runtime calculation
function checkConvenienceStoreProximity(candidate) {
    // 75 lines of ray-casting geometry code...
}

// NEW: Simple property read
function showDetailPanel(storeData) {
    // ... basic info HTML ...

    if (storeData.predicted_annual_sales !== undefined && currentMode === 'expansion') {
        // Direct property access - no calculation!
        if (storeData.fulfillment_strategy === 'partner') {
            detailHTML += `
                <div class="recommendation-card partner">
                    <div class="recommendation-header">Fulfillment Recommendation</div>
                    <div class="recommendation-title">🤝 Partner with Convenience Store</div>
                    <div class="recommendation-details">
                        <div class="recommendation-detail-row">
                            <span class="recommendation-detail-label">Partner Store</span>
                            <span class="recommendation-detail-value">${storeData.convenience_store_name || '7-Eleven'}</span>
                        </div>
                        <div class="recommendation-detail-row">
                            <span class="recommendation-detail-label">Location</span>
                            <span class="recommendation-detail-value">${storeData.convenience_city}</span>
                        </div>
                        <div class="recommendation-detail-row">
                            <span class="recommendation-detail-label">Drive Time</span>
                            <span class="recommendation-detail-value">${storeData.convenience_drive_time} min</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            detailHTML += `
                <div class="recommendation-card">
                    <div class="recommendation-header">Fulfillment Recommendation</div>
                    <div class="recommendation-title">🏪 Open New Store</div>
                    <div class="recommendation-details">
                        <div class="recommendation-detail-row">
                            <span class="recommendation-detail-label">Nearest Existing</span>
                            <span class="recommendation-detail-value">Store #${storeData.nearest_existing_store}</span>
                        </div>
                        <div class="recommendation-detail-row">
                            <span class="recommendation-detail-label">Distance</span>
                            <span class="recommendation-detail-value">${storeData.min_distance_to_existing.toFixed(1)} miles</span>
                        </div>
                    </div>
                </div>
            `;
        }
    }
}
```

**User Experience Impact:**
| Aspect | Before | After |
|--------|--------|-------|
| Panel open time | 200-500ms | <20ms |
| First click delay | Noticeable | Instant |
| Repeated clicks | Same delay each time | Always instant |

**Removed Code:**
- `pointInPolygon()` function (~25 lines)
- `checkConvenienceStoreProximity()` function (~75 lines)
- GeoJSON parsing logic (~15 lines)

---

### 2.2 Fulfillment Recommendation Logic - Detailed Behavior Change

**Current Logic (app_v2.py lines 1355-1422):**

The fulfillment recommendation appears in the right panel detail for optimized expansion candidates:

```
IF candidate is within 5-min drive of ANY convenience store isochrone:
    → Recommend "Partner with Convenience Store" (micro-fulfillment)
    → Show partner store name, city, drive time
ELSE:
    → Recommend "Open New Store"
    → Show no additional context
```

**New Logic (pre-computed in pipeline):**

The same logic is now computed in the `viz_expansion_candidates` table:

```sql
-- In viz_expansion_candidates table
fulfillment_strategy = CASE
    WHEN within_convenience_isochrone THEN 'partner'
    ELSE 'new_store'
END
```

**Enhanced Recommendation Data:**

With pre-computation, we can provide richer recommendations:

```sql
-- Additional columns now available on each candidate:
convenience_store_name      -- Partner store name (if applicable)
convenience_city            -- Partner store city
convenience_drive_time      -- Minutes to partner store
min_distance_to_existing    -- Miles to nearest existing store
nearest_existing_store      -- Store number of nearest existing
```

**New Recommendation Card Content:**

```
FOR "Partner" recommendation:
├── Partner Store: [convenience_store_name]
├── Location: [convenience_city]
├── Drive Time: [convenience_drive_time] min
├── Strategy: Micro-fulfillment
└── Cost Savings: ~60% vs new build (estimated)

FOR "New Store" recommendation:
├── Nearest Existing Store: #[nearest_existing_store]
├── Distance: [min_distance_to_existing] miles
├── Strategy: Full build-out
└── Rationale: No convenience partners in trade area
```

**Code Removal Summary:**

| Function | Lines | Purpose | Replacement |
|----------|-------|---------|-------------|
| `pointInPolygon()` | 1208-1222 | Ray-casting geometry | Pre-computed `within_convenience_isochrone` |
| `checkConvenienceStoreProximity()` | 1225-1298 | Find convenience store | Pre-computed `convenience_*` columns |
| `haversine()` (JS) | 1733-1742 | Distance calculation | Pre-computed `min_distance_to_existing` |
| `runOptimizationJS()` | 1697-1730 | Optimization algorithm | Pre-computed `viz_optimization_results` |
| `distanceMiles()` | 1728-1732 | Distance helper | Pre-computed columns |

**Total lines removed from app_v2.py:** ~150 lines of JavaScript

---

### 2.3 Replace Data Loading Functions

**Current (queries silver):**
```python
def load_existing_stores():
    return spark.sql("SELECT * FROM geo_silver.existing_stores_h3")
```

**Recommended (query gold viz_ tables):**
```python
def load_existing_stores():
    return spark.sql("SELECT * FROM geo_gold.viz_existing_stores")

def load_expansion_candidates():
    return spark.sql("SELECT * FROM geo_gold.viz_expansion_candidates")

def load_network_metrics():
    return spark.sql("SELECT * FROM geo_gold.viz_network_metrics").first()
```

### 2.2 Replace JavaScript Optimization with Lookup

**Current (JavaScript, ~100 lines):**
```javascript
function runOptimization() {
    candidates.sort((a, b) => b.predicted_annual_sales - a.predicted_annual_sales);
    for (let i = 0; i < candidates.length && selected.length < max_stores; i++) {
        // O(n²) distance checks
        let tooCloseToExisting = existingStores.some(store =>
            haversine(candidates[i], store) < min_dist_existing
        );
        // ... more distance checks
    }
}
```

**Recommended (Python lookup):**
```python
def get_optimized_locations(max_stores, min_dist_new, min_dist_existing):
    """Lookup pre-computed optimization result."""
    # Snap to nearest pre-computed parameters
    max_stores = min([5, 10, 15, 20, 25, 30], key=lambda x: abs(x - max_stores))
    min_dist_new = min([1.0, 2.0, 3.0, 5.0], key=lambda x: abs(x - min_dist_new))
    min_dist_existing = min([1.0, 2.0, 3.0, 5.0], key=lambda x: abs(x - min_dist_existing))

    result = spark.sql(f"""
        SELECT selected_h3_cells, selected_count, total_predicted_sales
        FROM geo_gold.viz_optimization_results
        WHERE max_stores = {max_stores}
          AND min_distance_new = {min_dist_new}
          AND min_distance_existing = {min_dist_existing}
    """).first()

    return result
```

### 2.3 Replace Point-in-Polygon with Lookup

**Current (JavaScript ray-casting, ~75 lines):**
```javascript
function pointInPolygon(point, polygon) {
    // Complex ray-casting algorithm
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        // ... 50+ lines of geometry math
    }
}
```

**Recommended (Python lookup):**
```python
def get_convenience_proximity(h3_cell_id):
    """Lookup pre-computed convenience store proximity."""
    return spark.sql(f"""
        SELECT convenience_store_type, convenience_city, drive_time_minutes
        FROM geo_gold.viz_convenience_proximity
        WHERE h3_cell_id = '{h3_cell_id}'
    """).toPandas()
```

### 2.4 Replace Runtime Aggregations

**Current (JavaScript):**
```javascript
function updateMetrics() {
    let avgPop = stores.reduce((sum, s) => sum + s.population, 0) / stores.length;
    let avgPoi = stores.reduce((sum, s) => sum + s.total_poi, 0) / stores.length;
    // Recalculated on every render
}
```

**Recommended (Pre-computed lookup):**
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_network_metrics():
    """Load pre-computed network metrics."""
    return spark.sql("SELECT * FROM geo_gold.viz_network_metrics").first()

# In app:
metrics = get_network_metrics()
st.metric("Avg Population", f"{metrics.avg_store_population:,.0f}")
st.metric("Avg POI Count", f"{metrics.avg_store_poi:,.0f}")
```

### 2.5 Simplify Filtering Logic

**Current (JavaScript filtering):**
```javascript
const filteredCandidates = candidates.filter(c =>
    c.predicted_annual_sales >= minSales &&
    c.population >= minPopulation
);
```

**Recommended (SQL predicate pushdown):**
```python
def load_filtered_candidates(min_sales=None, min_population=None, quality_tier=None):
    """Load candidates with server-side filtering."""
    query = "SELECT * FROM geo_gold.viz_expansion_candidates WHERE 1=1"

    if min_sales:
        query += f" AND predicted_annual_sales >= {min_sales}"
    if min_population:
        query += f" AND population >= {min_population}"
    if quality_tier:
        query += f" AND quality_tier = '{quality_tier}'"

    return spark.sql(query).toPandas()
```

---

## Phase 3: Performance Optimizations

### 3.1 Liquid Clustering for Gold Tables

```sql
-- Enable liquid clustering on frequently filtered columns
ALTER TABLE geo_gold.viz_expansion_candidates
CLUSTER BY (quality_tier, fulfillment_strategy, predicted_annual_sales);

ALTER TABLE geo_gold.viz_convenience
CLUSTER BY (candidate_count_in_isochrone);

ALTER TABLE geo_gold.viz_optimization_results
CLUSTER BY (max_stores, min_distance_new, min_distance_existing);
```

### 3.2 Materialized View for App Queries

```sql
-- Create materialized view for combined app data load
CREATE MATERIALIZED VIEW geo_gold.mv_app_data_load AS
SELECT
  'existing_store' as layer_type,
  store_number as id,
  latitude,
  longitude,
  population,
  total_poi,
  NULL as predicted_annual_sales,
  ST_AsGeoJSON(geometry) as geometry_geojson
FROM geo_gold.viz_existing_stores

UNION ALL

SELECT
  'candidate' as layer_type,
  h3_cell_id as id,
  center_lat as latitude,
  center_lon as longitude,
  population,
  total_poi,
  predicted_annual_sales,
  geometry_geojson
FROM geo_gold.viz_expansion_candidates

UNION ALL

SELECT
  'competitor' as layer_type,
  id,
  latitude,
  longitude,
  NULL as population,
  NULL as total_poi,
  NULL as predicted_annual_sales,
  ST_AsGeoJSON(geometry) as geometry_geojson
FROM geo_gold.viz_competitors;
```

### 3.3 Leverage viz_h3_grid for Massachusetts Boundary Filtering

**Current Problem:**

The app uses lat/long bounding box checks for Massachusetts filtering, which is:
1. **Inaccurate** - Bounding boxes include areas outside MA (corners of rectangle)
2. **Redundant** - The `viz_h3_grid` table already defines valid MA H3 cells
3. **Inconsistent** - Different queries use different methods (census_states geometry vs lat/long bounds)

**Current approach (app_v2.py):**
```sql
-- Bounding box filter (imprecise - includes areas outside MA)
WHERE latitude BETWEEN 41.2 AND 42.9 AND longitude BETWEEN -73.5 AND -69.9
```

**Current approach (census_states query):**
```sql
-- GeoJSON boundary lookup (expensive, sent to JavaScript)
SELECT ST_AsGeoJSON(geometry) FROM geo_bronze.census_states WHERE state_abbr = 'MA'
```

**New Approach: H3 Cell Membership**

The `viz_h3_grid` table contains all H3 cells (resolution 8) that fall within Massachusetts. This can be used as the **authoritative boundary filter** instead of lat/long checks.

**Pipeline Changes:**

1. **Use viz_h3_grid as a filter in all gold table creation:**

```sql
-- In viz_expansion_candidates creation
CREATE OR REPLACE TABLE geo_gold.viz_expansion_candidates AS
SELECT c.*,
  -- ... other columns ...
FROM geo_gold.expansion_candidates_h3_enhanced c
INNER JOIN geo_gold.viz_h3_grid g ON c.h3_cell_id = g.h3_cell
-- No lat/long filter needed - H3 join enforces MA boundary
```

2. **Add h3_cell_id to all viz_* tables for consistent filtering:**

```sql
-- Ensure all location-based tables have H3 cell ID
ALTER TABLE geo_gold.viz_existing_stores
ADD COLUMN h3_cell_id STRING AS h3_latlng_to_cell(latitude, longitude, 8);

ALTER TABLE geo_gold.viz_competitors
ADD COLUMN h3_cell_id STRING AS h3_latlng_to_cell(latitude, longitude, 8);
```

3. **Create convenience view for valid MA cells lookup:**

```sql
-- Useful for quick validation
CREATE OR REPLACE VIEW geo_gold.v_valid_ma_h3_cells AS
SELECT DISTINCT h3_cell
FROM geo_gold.viz_h3_grid;
```

**App Changes:**

1. **Remove lat/long bounding box filters:**

```python
# BEFORE: Bounding box filter (imprecise)
candidates_df = spark.sql("""
    SELECT * FROM geo_gold.expansion_candidates_h3_enhanced
    WHERE latitude BETWEEN 41.2 AND 42.9
      AND longitude BETWEEN -73.5 AND -69.9
""")

# AFTER: H3 membership filter (precise)
candidates_df = spark.sql("""
    SELECT c.* FROM geo_gold.viz_expansion_candidates c
    -- Already filtered to MA via viz_h3_grid join in table creation
""")
```

2. **Remove census_states GeoJSON query:**

```javascript
// BEFORE: Load MA boundary GeoJSON for JavaScript
const maBoundary = await fetch('/api/census_states?state=MA').then(r => r.json());

// AFTER: No boundary needed - data already filtered to MA
// If outline needed for map, use simplified polygon stored in viz_h3_grid metadata
```

3. **Optional: Add MA boundary outline from H3 grid:**

```sql
-- Create simplified MA boundary from H3 grid (for map outline only)
CREATE OR REPLACE TABLE geo_gold.viz_ma_boundary AS
SELECT
  ST_ConvexHull(ST_Union_Agg(h3_cell_to_boundary(h3_cell))) as simplified_geometry,
  ST_AsGeoJSON(ST_ConvexHull(ST_Union_Agg(h3_cell_to_boundary(h3_cell)))) as boundary_geojson
FROM geo_gold.viz_h3_grid;
```

**Benefits:**

| Aspect | Before (Lat/Long) | After (H3 Membership) |
|--------|-------------------|----------------------|
| **Accuracy** | Includes non-MA areas in bounding box | Exact MA boundary from H3 cells |
| **Performance** | O(n) lat/long comparisons | O(1) H3 hash join |
| **Consistency** | Different methods across queries | Single source of truth |
| **Simplicity** | Multiple boundary checks | Pre-filtered at table creation |

**Implementation Priority:** This should be done during the viz_expansion_candidates table enhancement, as the H3 join can replace lat/long filters in the same refactoring step.

---

### 3.4 Delta Caching Strategy

```python
# app_v2.py - Optimized caching
@st.cache_data(ttl=3600)  # 1 hour for static reference data
def load_static_layers():
    """Load existing stores, competitors, convenience - rarely change."""
    return {
        'existing': spark.table("geo_gold.viz_existing_stores").toPandas(),
        'competitors': spark.table("geo_gold.viz_competitors").toPandas(),
        'convenience': spark.table("geo_gold.viz_convenience").toPandas(),
    }

@st.cache_data(ttl=600)  # 10 min for candidates (may update more frequently)
def load_candidates():
    """Load expansion candidates."""
    return spark.table("geo_gold.viz_expansion_candidates").toPandas()

@st.cache_data(ttl=3600)  # 1 hour for optimization results
def load_optimization_results():
    """Load all pre-computed optimization results."""
    return spark.table("geo_gold.viz_optimization_results").toPandas()
```

---

## Implementation Checklist

### Pipeline Changes (Notebooks/SQL)

- [ ] **Leverage viz_h3_grid for MA boundary filtering**
  - [ ] Use INNER JOIN to viz_h3_grid in viz_expansion_candidates creation
  - [ ] Add h3_cell_id column to viz_existing_stores
  - [ ] Add h3_cell_id column to viz_competitors
  - [ ] Create v_valid_ma_h3_cells view for quick validation
  - [ ] (Optional) Create viz_ma_boundary table from H3 grid union
- [ ] Create `geo_gold.viz_network_metrics` table (singleton aggregates)
- [ ] Enhance `geo_gold.viz_expansion_candidates` with:
  - [ ] `min_distance_to_existing` (Haversine pre-computed)
  - [ ] `nearest_existing_store` (store number)
  - [ ] `within_convenience_isochrone` (boolean)
  - [ ] `convenience_store_name`, `convenience_city`, `convenience_drive_time`
  - [ ] `fulfillment_strategy` ('partner' or 'new_store')
  - [ ] `quality_tier` ('top_25', 'top_50', etc.)
  - [ ] `geometry_geojson`, `center_lat`, `center_lon`
- [ ] Enhance `geo_gold.viz_convenience` with:
  - [ ] `candidate_count_in_isochrone`
  - [ ] `total_candidate_sales_in_isochrone`
  - [ ] `candidate_h3_cells_in_isochrone` (array)
- [ ] Create `geo_gold.viz_optimization_results` table
- [ ] Populate optimization results for parameter grid (6×4×4 = 96 combinations)
- [ ] Add liquid clustering to gold tables
- [ ] Create scheduled workflow to refresh gold tables
- [ ] Validate row counts and data quality

### App Changes

- [ ] **Remove lat/long boundary filters (use pre-filtered viz_* tables)**
  - [ ] Remove `WHERE latitude BETWEEN ... AND longitude BETWEEN ...` filters
  - [ ] Remove `census_states` query for MA boundary GeoJSON
  - [ ] (Optional) Load simplified MA boundary from viz_ma_boundary for map outline
- [ ] Update data loading to query `viz_*` tables instead of silver/bronze
- [ ] Load `viz_optimization_results` at startup into JavaScript cache
- [ ] Replace `runOptimization()` with `lookupOptimization()` (table lookup)
- [ ] Replace `checkConvenienceStoreProximity()` with column read
- [ ] Remove `pointInPolygon()` function
- [ ] Remove `haversine()` / `distanceMiles()` functions
- [ ] Remove `runOptimizationJS()` function
- [ ] Update `showDetailPanel()` to read pre-computed columns
- [ ] Add parameter snapping UI feedback (show which grid values are used)
- [ ] Update caching strategy (increase TTL for static data)

### Validation

- [ ] Compare optimization results: runtime algorithm vs pre-computed table
- [ ] Verify distance calculations match (Haversine in SQL vs JavaScript)
- [ ] Verify fulfillment recommendations match for sample candidates
- [ ] Load test app with new architecture
- [ ] Measure latency improvement (target: 10-40x faster optimization)

---

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Optimization latency** | 500-2000ms | <50ms | 10-40x faster |
| **Detail panel load** | 200-500ms | <20ms | 10-25x faster |
| **Initial page load** | 3-5s | 1-2s | 2-3x faster |
| **JavaScript bundle size** | ~150 lines optimization | ~20 lines lookup | 85% reduction |
| **Server compute per request** | High (SQL + JS) | Low (lookup only) | 70% reduction |

---

## Migration Strategy

### Option A: Big Bang (Simpler, Riskier)
1. Create all new gold tables
2. Refactor app to use new tables
3. Deploy together
4. Remove old code paths

### Option B: Gradual Migration (Recommended)
1. Create new gold tables alongside existing
2. Add feature flag to app: `USE_PRECOMPUTED_OPTIMIZATION`
3. Deploy app with flag disabled
4. Enable flag for testing users
5. Monitor and validate
6. Enable flag for all users
7. Remove old code paths and flag

---

## Open Questions

1. **Parameter granularity**: Should optimization be pre-computed for every integer `max_stores` value (1-30) or just [5, 10, 15, 20, 25, 30]?

2. **Refresh frequency**: How often should gold tables be refreshed? Daily? Hourly? On-demand?

3. **Interpolation**: Should the app interpolate between pre-computed optimization results for non-exact parameter matches, or snap to nearest?

4. **Historical tracking**: Should we keep history of optimization results, or just latest?

5. **Custom constraints**: Users may want custom distance constraints (e.g., 2.5 miles). Support continuous parameters or force discrete?
