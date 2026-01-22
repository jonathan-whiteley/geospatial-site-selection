# Performance Optimization Plan

## Current State: 20+ Second Initial Load Time

### Root Cause Analysis

| Bottleneck | Location | Est. Impact |
|-----------|----------|-------------|
| Sequential DB queries | `data_service.py` | 3-5s |
| Connection overhead (5-6 OAuth handshakes) | `database.py` | 2-4s |
| Duplicate queries across endpoints | `/network` + `/expansion/data` | 1-2s |
| No query result caching | Service layer | 1-2s |
| Map rendering (1000+ markers) | `GeospatialMap.jsx` | 2-4s |
| Frontend range calculations | `useStoreData.js` | 300-500ms |

### Current Data Flow

```
App Load
  └── useStoreData() fires 3 parallel API calls:
      ├── /api/stores/network     → 6 sequential DB queries
      ├── /api/expansion/data     → 4 sequential DB queries (3 duplicates!)
      └── /api/optimization/results → 1 DB query
```

---

## Recommendations (Priority Order)

### 1. **CRITICAL: Consolidate to Single Initial Load Endpoint**

**Impact: -5 to -8 seconds**

Create a single `/api/init` endpoint that returns all initial data in one request.

```python
# api/routes/init.py (NEW)
@router.get("/init")
async def get_initial_data():
    """Single endpoint for all initial app data - eliminates duplicate queries."""
    return await service.load_initial_data()
```

```python
# services/data_service.py
async def load_initial_data(self):
    """Load all initial data with parallel queries and shared connection."""

    # Use a single connection for all queries
    with self.get_connection() as conn:
        # Execute queries in parallel using asyncio
        stores, candidates, partners, competitors, boundary = await asyncio.gather(
            self._query_async(conn, "SELECT * FROM viz_existing_stores"),
            self._query_async(conn, "SELECT * FROM viz_expansion_candidates"),
            self._query_async(conn, "SELECT * FROM viz_partners"),
            self._query_async(conn, "SELECT * FROM viz_competitors"),
            self._query_async(conn, "SELECT * FROM census_states WHERE state_abbr = 'MA'"),
        )

    return {
        "network": {"stores": stores, "partners": partners, "competitors": competitors},
        "expansion": {"candidates": candidates},
        "boundary": boundary,
    }
```

**Frontend change:**
```javascript
// hooks/useStoreData.js
const response = await fetch('/api/init')  // Single request instead of 3
```

---

### 2. **HIGH: Implement Connection Pooling**

**Impact: -2 to -4 seconds**

Current: Each query opens a new OAuth connection (~800ms overhead each).

```python
# core/database.py
from databricks import sql
from contextlib import contextmanager

class DatabaseManager:
    _connection_pool = None

    @classmethod
    def get_pool(cls):
        if cls._connection_pool is None:
            cls._connection_pool = sql.connect(
                server_hostname=settings.DATABRICKS_HOST,
                http_path=settings.DATABRICKS_HTTP_PATH,
                access_token=settings.DATABRICKS_TOKEN,
            )
        return cls._connection_pool

    def execute_query(self, sql_query: str) -> pd.DataFrame:
        conn = self.get_pool()  # Reuse connection
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            return cursor.fetchall_arrow().to_pandas()
```

---

### 3. **HIGH: Add Backend Caching for Static Data**

**Impact: -1 to -2 seconds (subsequent loads instant)**

Some data rarely changes and can be cached:
- MA boundary (static)
- Partner stores (changes infrequently)
- Competitors (changes infrequently)

```python
# core/cache.py
from functools import lru_cache
from datetime import datetime, timedelta

class DataCache:
    _cache = {}
    _ttl = timedelta(minutes=15)

    @classmethod
    def get(cls, key: str):
        if key in cls._cache:
            data, timestamp = cls._cache[key]
            if datetime.now() - timestamp < cls._ttl:
                return data
        return None

    @classmethod
    def set(cls, key: str, data):
        cls._cache[key] = (data, datetime.now())

# Usage in data_service.py
def load_ma_boundary(self):
    cached = DataCache.get("ma_boundary")
    if cached:
        return cached

    result = self.execute_query("SELECT * FROM census_states WHERE state_abbr = 'MA'")
    DataCache.set("ma_boundary", result)
    return result
```

---

### 4. **MEDIUM: Lazy Load Optimization Results**

**Impact: -500ms to -1s initial load**

Don't load optimization results until user clicks "Run Optimization".

```javascript
// hooks/useStoreData.js - REMOVE from initial load
const [networkResponse, expansionResponse] = await Promise.all([
    getFullNetwork(),
    getExpansionData(),
    // REMOVED: getOptimizationResults()
])

// hooks/useOptimization.js - Load on demand
const runOptimization = async (params) => {
    const results = await getOptimizationResults(params)  // Only when needed
    setOptimizationResults(results)
}
```

---

### 5. **MEDIUM: Pre-compute Sales/Population Ranges in Backend**

**Impact: -300ms**

Move range calculations to SQL (instant) instead of JavaScript iteration.

```python
# In load_expansion_candidates query:
SELECT
    *,
    MIN(predicted_annual_sales) OVER () as sales_min,
    MAX(predicted_annual_sales) OVER () as sales_max,
    MIN(population) OVER () as population_min,
    MAX(population) OVER () as population_max
FROM viz_expansion_candidates
LIMIT 1  -- Window functions compute across all rows
```

Or use a dedicated aggregation:
```python
def load_expansion_data(self):
    candidates = self.execute_query("SELECT * FROM viz_expansion_candidates")

    # Compute ranges in SQL
    ranges = self.execute_query("""
        SELECT
            MIN(predicted_annual_sales) as sales_min,
            MAX(predicted_annual_sales) as sales_max,
            MIN(population) as pop_min,
            MAX(population) as pop_max
        FROM viz_expansion_candidates
    """)

    return {"candidates": candidates, "ranges": ranges}
```

---

### 6. **MEDIUM: Implement Viewport-Based Loading**

**Impact: -2 to -3 seconds (perceived)**

Only load candidates visible in the current map viewport initially.

```python
# api/routes/expansion.py
@router.get("/candidates")
async def get_candidates(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    limit: int = 500
):
    """Load candidates within viewport bounds."""
    return await service.load_candidates_in_bounds(
        min_lat, max_lat, min_lon, max_lon, limit
    )
```

```javascript
// Load initial viewport, then fetch more on pan/zoom
const onBoundsChange = debounce(async (bounds) => {
    const newCandidates = await fetchCandidatesInBounds(bounds)
    setCandidates(prev => mergeUnique(prev, newCandidates))
}, 300)
```

---

### 7. **LOW: Virtualize Map Markers**

**Impact: -1 to -2 seconds (for large datasets)**

React-Leaflet renders all markers to DOM. Use canvas rendering for large datasets.

```javascript
// Use Leaflet.Canvas for markers instead of SVG
import 'leaflet-canvas-markers'

// Or limit initial markers, load more on zoom
const visibleCandidates = useMemo(() => {
    if (zoomLevel < 10) {
        // Show only top 100 by sales when zoomed out
        return candidates
            .sort((a, b) => b.predicted_annual_sales - a.predicted_annual_sales)
            .slice(0, 100)
    }
    return filterByBounds(candidates, mapBounds)
}, [candidates, zoomLevel, mapBounds])
```

---

## Implementation Phases

### Phase 1: Quick Wins (1-2 days)
- [ ] Consolidate to single `/api/init` endpoint
- [ ] Add connection pooling
- [ ] Remove optimization results from initial load

**Expected improvement: 6-10 seconds**

### Phase 2: Caching & Optimization (2-3 days)
- [ ] Add backend caching for static data
- [ ] Pre-compute ranges in SQL
- [ ] Memoize frontend calculations

**Expected improvement: 2-3 seconds**

### Phase 3: Progressive Loading (3-5 days)
- [ ] Implement viewport-based candidate loading
- [ ] Add loading skeleton for deferred data
- [ ] Virtualize large marker sets

**Expected improvement: 2-4 seconds (perceived)**

---

## Target State

| Metric | Current | Target |
|--------|---------|--------|
| Initial load | 20+ seconds | 3-5 seconds |
| API calls on init | 3 parallel | 1 |
| DB connections per request | 5-6 | 1 (pooled) |
| Candidates loaded initially | All (~50K) | Viewport (~500) |

---

## Monitoring Recommendations

Add performance logging to track improvements:

```python
# api/middleware/timing.py
import time
from fastapi import Request

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    logger.info(f"{request.url.path} completed in {duration:.3f}s")
    return response
```

```javascript
// Frontend timing
console.time('initialLoad')
await loadInitialData()
console.timeEnd('initialLoad')  // Logs: "initialLoad: 4523ms"
```
