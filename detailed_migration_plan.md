# Migration Plan: Streamlit to React + FastAPI

## Overview

Migrate the 2,418-line Streamlit geospatial app (`app_v2.py`) to a modern React (Vite) + FastAPI architecture with Service Principal authentication.

**Key Decisions:**
- Backend: FastAPI (Python) - keeps existing SQL queries, pandas, databricks-sdk
- Frontend: React + Vite + Tailwind + shadcn/ui + react-leaflet
- Auth: Service Principal (no PAT tokens)
- Map Features: ALL preserved (H3 hexagons, isochrones, clustering, optimization)
- Chat: Deferred to later phase

---

## Project Structure

```
app/
├── main.py                    # FastAPI entry point + static file serving
├── api/routes/
│   ├── stores.py              # /api/stores/* endpoints
│   ├── expansion.py           # /api/expansion/* endpoints
│   ├── optimization.py        # /api/optimization/* endpoints
│   └── health.py              # /api/health
├── core/
│   ├── config.py              # Environment configuration
│   └── database.py            # Service Principal auth + SQL connector
├── models/                    # Pydantic models
├── services/                  # Business logic
├── app.yaml                   # Updated for uvicorn
└── requirements.txt

frontend/
├── src/
│   ├── App.jsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.jsx      # Header + Sidebar + Map container
│   │   │   └── Sidebar.jsx        # Controls + Metrics
│   │   ├── map/
│   │   │   ├── GeospatialMap.jsx  # Main react-leaflet container
│   │   │   ├── H3HexagonLayer.jsx # Sales gradient hexagons
│   │   │   ├── IsochroneLayer.jsx # Trade area overlays
│   │   │   ├── StoreMarkerCluster.jsx # Sales-aggregating clusters
│   │   │   └── MapLegend.jsx
│   │   ├── panels/
│   │   │   └── DetailPanel.jsx    # Right slide-in (384px)
│   │   ├── controls/
│   │   │   ├── LayerToggles.jsx
│   │   │   ├── FilterSliders.jsx
│   │   │   └── OptimizationControls.jsx
│   │   └── ui/                    # shadcn components
│   ├── hooks/
│   │   ├── useMapState.js
│   │   ├── useStoreData.js
│   │   └── useOptimization.js
│   └── services/api.js            # /api prefix client
├── vite.config.js
├── tailwind.config.js
└── package.json
```

---

## Backend API Routes

| Endpoint | Method | Description | Source Table |
|----------|--------|-------------|--------------|
| `/api/health` | GET | Health check | - |
| `/api/stores/current` | GET | Current stores | `viz_existing_stores` |
| `/api/stores/isochrones` | GET | LCE trade areas | `isochrones_lce` |
| `/api/stores/convenience` | GET | Convenience isochrones | `viz_convenience` |
| `/api/stores/competitors` | GET | Competitor locations | `viz_competitors` |
| `/api/expansion/candidates` | GET | Expansion candidates (filterable) | `viz_expansion_candidates` |
| `/api/optimization/results` | GET | Pre-computed grid | `viz_optimization_results` |
| `/api/optimization/lookup` | POST | Lookup specific params | `viz_optimization_results` |
| `/api/metrics/network` | GET | Aggregate metrics | `viz_network_metrics` |

---

## Service Principal Authentication

Reference: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth

**app/core/database.py:**
```python
from databricks.sdk.config import Config
from databricks import sql as dbsql
import os

class DatabricksDB:
    def __init__(self):
        self.config = Config()  # Auto-detects SP in Databricks Apps
        self.host = os.getenv("DATABRICKS_SERVER_HOSTNAME", self.config.host)
        self.http_path = os.getenv("DATABRICKS_HTTP_PATH")

    def get_connection(self):
        # In Databricks Apps: uses DATABRICKS_CLIENT_ID/SECRET (injected automatically)
        if os.getenv("DATABRICKS_CLIENT_ID"):
            return dbsql.connect(
                server_hostname=self.host,
                http_path=self.http_path,
                credentials_provider=lambda: self.config.authenticate
            )
        # Dev fallback: uses PAT token
        return dbsql.connect(
            server_hostname=self.host,
            http_path=self.http_path,
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
```

**Key Points:**
- Databricks Apps automatically inject `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`
- The `databricks-sdk` `Config()` class auto-detects these environment variables
- No hardcoded tokens in app.yaml

---

## app.yaml (Updated for FastAPI)

```yaml
command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  - name: DATABRICKS_SERVER_HOSTNAME
    value: fe-vm-jdub-vm-serverless.cloud.databricks.com
  - name: DATABRICKS_HTTP_PATH
    value: /sql/1.0/warehouses/0168e23e24e6ae10
  - name: DATABRICKS_CATALOG
    value: jdub_demo
  - name: DATABRICKS_GOLD_SCHEMA
    value: geo_gold
  - name: DATABRICKS_SILVER_SCHEMA
    value: geo_silver
  - name: DATABRICKS_BRONZE_SCHEMA
    value: geo_bronze
```

**Note:** Remove `DATABRICKS_TOKEN` - Service Principal credentials are auto-injected.

---

## FastAPI Static File Serving

**app/main.py:**
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Geospatial Retail Site Selection API")

# API routes (MUST be registered BEFORE static file catch-all)
app.include_router(health_router, prefix="/api")
app.include_router(stores_router, prefix="/api/stores")
app.include_router(expansion_router, prefix="/api/expansion")
app.include_router(optimization_router, prefix="/api/optimization")
app.include_router(metrics_router, prefix="/api/metrics")

# Serve React build from frontend/dist/
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React SPA for all non-API routes"""
        return FileResponse(frontend_path / "index.html")
```

---

## Key Frontend Components

### GeospatialMap.jsx (react-leaflet)

```jsx
import { MapContainer, TileLayer, GeoJSON, Pane } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-markercluster';

export function GeospatialMap({
  stores, candidates, layers, salesRange,
  onStoreClick, onCandidateClick
}) {
  return (
    <MapContainer center={[42.4072, -71.3824]} zoom={9}>
      {/* CartoDB dark tile layer (matching current app) */}
      <TileLayer
        url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap &copy; CARTO'
      />

      {/* Custom panes for z-index control */}
      <Pane name="isochrones" style={{ zIndex: 400 }}>
        {layers.h3_hexagons && (
          <H3HexagonLayer candidates={candidates} salesRange={salesRange} onClick={onCandidateClick} />
        )}
        <IsochroneLayer isochrones={lceIsochrones} color="#10b981" />
        {layers.convenience && (
          <IsochroneLayer isochrones={convenienceIsochrones} color="#3b82f6" />
        )}
      </Pane>

      <Pane name="markers" style={{ zIndex: 450 }}>
        {layers.current_stores && (
          <StoreMarkers stores={stores} onClick={onStoreClick} />
        )}
        {layers.candidates && (
          <MarkerClusterGroup iconCreateFunction={createSalesClusterIcon}>
            <CandidateMarkers candidates={candidates} onClick={onCandidateClick} />
          </MarkerClusterGroup>
        )}
      </Pane>

      <MapLegend />
      {(layers.candidates || layers.h3_hexagons) && (
        <SalesGradientLegend salesRange={salesRange} />
      )}
    </MapContainer>
  );
}
```

### H3HexagonLayer.jsx (Sales Gradient)

```jsx
export function H3HexagonLayer({ candidates, salesRange, onClick }) {
  // Sales-based color gradient: white → red
  const getSalesColor = (sales) => {
    const ratio = (sales - salesRange.min) / (salesRange.max - salesRange.min || 1);
    const g = Math.round(255 * (1 - ratio));
    const b = Math.round(255 * (1 - ratio));
    return `rgb(255, ${g}, ${b})`;
  };

  return (
    <>
      {candidates.map(candidate => (
        <GeoJSON
          key={candidate.store_number}
          data={JSON.parse(candidate.geometry_geojson)}
          style={{
            color: '#dc2626',
            weight: 1.5,
            fillColor: getSalesColor(candidate.predicted_annual_sales),
            fillOpacity: 0.7
          }}
          eventHandlers={{ click: () => onClick(candidate) }}
        />
      ))}
    </>
  );
}
```

### StoreMarkerCluster.jsx (Sales Aggregation)

```jsx
// Custom cluster icon showing TOTAL SALES (not count)
const createSalesClusterIcon = (cluster) => {
  const markers = cluster.getAllChildMarkers();
  const totalSales = markers.reduce((sum, m) => sum + (m.options.predicted_sales || 0), 0);
  const formattedSales = formatSales(totalSales);
  const count = cluster.getChildCount();
  const size = count < 10 ? 40 : count < 50 ? 50 : 60;

  return L.divIcon({
    html: `<div class="cluster-sales">${formattedSales}</div>`,
    className: 'sales-cluster-icon',
    iconSize: L.point(size, size)
  });
};

// formatSales helper
function formatSales(sales) {
  if (sales >= 1000000) return '$' + (sales / 1000000).toFixed(1) + 'M';
  if (sales >= 1000) return '$' + (sales / 1000).toFixed(0) + 'K';
  return '$' + Math.round(sales);
}
```

### DetailPanel.jsx (Right Slide-in)

```jsx
export function DetailPanel({ store, isOpen, onClose }) {
  if (!store || !isOpen) return null;

  const isPartnerStrategy = store.within_convenience_isochrone === true;

  return (
    <div className={cn(
      "fixed right-0 top-16 w-96 h-[calc(100vh-64px)] bg-white border-l shadow-xl",
      "transform transition-transform duration-300",
      isOpen ? "translate-x-0" : "translate-x-full"
    )}>
      <div className="p-4 border-b">
        <div className="text-xs text-gray-500 uppercase">Store Details</div>
        <div className="text-xl font-semibold text-orange-500">
          {store.store_number}
        </div>
        <button onClick={onClose} className="absolute top-4 right-4">×</button>
      </div>

      <div className="p-4">
        {/* Location Stats */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <StatCard label="City" value={store.city} />
          <StatCard label="State" value={store.state} />
          <StatCard label="Population" value={store.population?.toLocaleString()} />
          <StatCard label="POI Count" value={store.total_poi_count} />
        </div>

        {/* Fulfillment Recommendation */}
        {store.fulfillment_strategy && (
          <FulfillmentRecommendation
            strategy={store.fulfillment_strategy}
            partnerName={store.convenience_store_name}
            partnerCity={store.convenience_city}
            driveTime={store.convenience_drive_time}
            nearestStore={store.nearest_existing_store}
            distance={store.min_distance_to_existing}
          />
        )}
      </div>
    </div>
  );
}
```

---

## State Management (Custom Hooks)

### useMapState.js

```js
export function useMapState() {
  const [mode, setMode] = useState('current'); // 'current' | 'expansion'
  const [layers, setLayers] = useState({
    current_stores: true,
    h3_hexagons: true,
    candidates: false,
    candidate_isochrones: false,
    convenience: false,
    competitors: false
  });
  const [filters, setFilters] = useState({
    min_sales: 500000,
    min_population: 5000
  });
  const [optimizationParams, setOptimizationParams] = useState({
    max_stores: 50,
    min_dist_new: 2.0,
    min_dist_existing: 2.0
  });
  const [optimizationResults, setOptimizationResults] = useState(null);
  const [selectedStore, setSelectedStore] = useState(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);

  // Mode change resets layers to defaults
  useEffect(() => {
    if (mode === 'current') {
      setLayers(prev => ({ ...prev, candidates: false, h3_hexagons: true, convenience: false }));
    } else if (mode === 'expansion') {
      setLayers(prev => ({ ...prev, candidates: true, h3_hexagons: true, convenience: true }));
    }
  }, [mode]);

  return {
    mode, setMode,
    layers, setLayers,
    filters, setFilters,
    optimizationParams, setOptimizationParams,
    optimizationResults, setOptimizationResults,
    selectedStore, setSelectedStore,
    detailPanelOpen, setDetailPanelOpen
  };
}
```

### useStoreData.js

```js
export function useStoreData() {
  const [stores, setStores] = useState([]);
  const [isochrones, setIsochrones] = useState([]);
  const [convenience, setConvenience] = useState({ stores: [], isochrones: [] });
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      const [storesRes, isoRes] = await Promise.all([
        api.get('/api/stores/current'),
        api.get('/api/stores/isochrones')
      ]);
      setStores(storesRes.data);
      setIsochrones(isoRes.data);
      setLoading(false);
    }
    fetchData();
  }, []);

  // Lazy load convenience and competitors
  const loadConvenience = async () => { ... };
  const loadCompetitors = async () => { ... };

  return { stores, isochrones, convenience, competitors, loading, loadConvenience, loadCompetitors };
}
```

---

## Implementation Phases

### Phase 1: Project Setup (1 day)
- [ ] Create directory structure
- [ ] Initialize Vite + React: `npm create vite@latest frontend -- --template react`
- [ ] Install Tailwind: `npm install -D tailwindcss postcss autoprefixer`
- [ ] Set up shadcn/ui: `npx shadcn-ui@latest init`
- [ ] Set up FastAPI project structure
- [ ] Copy logo asset

### Phase 2: Backend Core (2 days)
- [ ] Implement Service Principal auth module (`app/core/database.py`)
- [ ] Create database connection class with connection pooling
- [ ] Implement health check endpoint (`/api/health`)
- [ ] Test connection to Databricks SQL warehouse

### Phase 3: Backend API Routes (3 days)
- [ ] Extract SQL queries from app_v2.py lines 91-335
- [ ] Implement `/api/stores/current` (from `load_current_network_data()`)
- [ ] Implement `/api/stores/isochrones`
- [ ] Implement `/api/stores/convenience`
- [ ] Implement `/api/stores/competitors`
- [ ] Implement `/api/expansion/candidates` with filter params
- [ ] Implement `/api/optimization/results`
- [ ] Implement `/api/optimization/lookup` with parameter snapping
- [ ] Implement `/api/metrics/network`

### Phase 4: Frontend Foundation (2 days)
- [ ] Create AppLayout with Header + Sidebar
- [ ] Implement ModeTabs (Overview | Detail)
- [ ] Create MetricsPanel component
- [ ] Set up API client with /api prefix
- [ ] Implement useMapState hook

### Phase 5: Map Components (4 days)
- [ ] GeospatialMap base with CartoDB dark tiles
- [ ] Custom Leaflet panes for z-index control
- [ ] H3HexagonLayer with sales gradient (white→red)
- [ ] IsochroneLayer (LCE green, convenience blue)
- [ ] StoreMarkerCluster with sales aggregation icon
- [ ] MapLegend component
- [ ] SalesGradientLegend component
- [ ] Store/Candidate/Convenience/Competitor markers

### Phase 6: Controls + Panel (2 days)
- [ ] LayerToggles (checkboxes)
- [ ] FilterSliders (min_sales, min_population)
- [ ] OptimizationControls (max_stores, distances, run button)
- [ ] DetailPanel with slide animation
- [ ] FulfillmentRecommendation cards (partner blue, new_store yellow)

### Phase 7: Integration (2 days)
- [ ] Wire up all state hooks to components
- [ ] Mode switching logic with layer resets
- [ ] CSV export functionality (matching current 15 columns)

### Phase 8: Build + Deploy (2 days)
- [ ] Build frontend: `npm run build`
- [ ] Configure FastAPI to serve dist/
- [ ] Update app.yaml for uvicorn
- [ ] Deploy to Databricks Apps
- [ ] Test Service Principal auth end-to-end

---

## Verification Checklist

### Backend
- [ ] `/api/health` returns 200
- [ ] All 7 gold tables queryable via respective endpoints
- [ ] Service Principal auth works in Databricks Apps (no PAT token)
- [ ] Filter parameters work on `/api/expansion/candidates?min_sales=X&min_pop=Y`

### Map Features
- [ ] H3 hexagons render with sales gradient (white→red)
- [ ] LCE isochrones display in green (#10b981)
- [ ] Convenience isochrones toggle works (blue #3b82f6)
- [ ] Marker clustering shows total sales (not count)
- [ ] Custom pane z-index: isochrones below markers
- [ ] CartoDB dark tile layer loads correctly

### Controls
- [ ] Mode switching (Overview ↔ Detail) updates layer visibility
- [ ] Layer toggles update map immediately
- [ ] Filter sliders update candidate display
- [ ] Optimization lookup returns correct pre-computed results

### Detail Panel
- [ ] Slides in from right on store/candidate click
- [ ] Shows location stats (city, state, population, POI count)
- [ ] Shows correct fulfillment recommendation:
  - Partner strategy (blue) when `within_convenience_isochrone=true`
  - New store strategy (yellow) when false
- [ ] Close button works

### Export
- [ ] CSV export includes all 15 columns
- [ ] Filename includes timestamp
- [ ] Numbers formatted appropriately

---

## Dependencies

### Backend (requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
databricks-sql-connector>=3.0.0
databricks-sdk>=0.17.0
pandas>=2.0.0
python-dotenv>=1.0.0
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "leaflet.markercluster": "^1.5.3",
    "react-leaflet-markercluster": "^3.0.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-slider": "^1.2.0",
    "@radix-ui/react-checkbox": "^1.0.4",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.0",
    "lucide-react": "^0.294.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.1.1",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.31",
    "tailwindcss": "^3.3.5",
    "vite": "^4.5.0"
  }
}
```

---

## Reference Files

### Source (current app)
- `app/app_v2.py` - SQL queries (lines 91-335), JS map logic (lines 530-2400)

### Architecture Patterns (bc_nrf_app)
- `src/components/layout/ImprovedResponsiveLayout.jsx` - Layout structure
- `src/components/StoreDetailPanelRefactored.jsx` - Detail panel pattern
- `src/components/ProfessionalZoomableMap.jsx` - react-leaflet usage
- `tailwind.config.js` - Color palette and typography

### Databricks Docs
- Auth: https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth
- FastAPI: https://apps-cookbook.dev/docs/fastapi/getting_started/create
