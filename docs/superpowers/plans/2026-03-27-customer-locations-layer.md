# Customer Locations Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Customer Locations" map layer showing ~5400 device-level customer positions as subtle amber dots, with a sidebar toggle in the NETWORK section.

**Architecture:** New backend endpoint loads customer data from `viz_ma_pins` gold table, included in the consolidated `/init` response. Frontend adds a new CircleMarker layer and sidebar toggle following existing patterns exactly.

**Tech Stack:** Python/FastAPI (backend), React/Leaflet (frontend), Databricks SQL (data source)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `react-app/models/schemas.py:53-59` | Add `CustomerLocation` model after `Competitor` |
| Modify | `react-app/services/data_service.py:155-171` | Add `load_customers()` method after `load_competitors()` |
| Modify | `react-app/api/routes/stores.py:100-115` | Add `/stores/customers` endpoint after `/stores/competitors` |
| Modify | `react-app/api/routes/init.py:46-53` | Add `load_customers` to parallel executor |
| Modify | `react-app/api/routes/init.py:93-120` | Include `customer_locations` in response |
| Modify | `react-app/frontend/src/services/api.js:61-64` | Add `getCustomerLocations()` function |
| Modify | `react-app/frontend/src/hooks/useStoreData.js:13-23` | Add `customerLocations` to networkData state |
| Modify | `react-app/frontend/src/hooks/useStoreData.js:57-71` | Extract customer_locations from init response |
| Modify | `react-app/frontend/src/hooks/useMapState.js:6-14` | Add `customerLocations: false` to DEFAULT_LAYERS |
| Modify | `react-app/frontend/src/hooks/useMapState.js:28-45` | Add `customerLocations: false` to MODE_LAYERS |
| Modify | `react-app/frontend/src/components/map/GeospatialMap.jsx:316-344` | Add `CustomerLocationMarkers` component |
| Modify | `react-app/frontend/src/components/map/GeospatialMap.jsx:349-452` | Wire new layer into `GeospatialMap` |
| Modify | `react-app/frontend/src/components/layout/Sidebar.jsx:329-410` | Add toggle in NETWORK section |
| Modify | `react-app/frontend/src/App.jsx:320-328` | Pass `customerLocations` to `GeospatialMap` |

---

### Task 1: Backend — Schema and Data Service

**Files:**
- Modify: `react-app/models/schemas.py:53-59`
- Modify: `react-app/services/data_service.py:155-171`

- [ ] **Step 1: Add CustomerLocation schema**

In `react-app/models/schemas.py`, add after the `Competitor` class (line 59):

```python
class CustomerLocation(BaseModel):
    """Customer device location."""
    device_id: str
    latitude: float
    longitude: float
    store: str
```

- [ ] **Step 2: Add load_customers() to DataService**

In `react-app/services/data_service.py`, add after the `load_competitors` method (after line 171):

```python
    def load_customers(self) -> List[Dict[str, Any]]:
        """Load customer device locations."""
        gold = self.settings.gold_table_prefix
        try:
            start = time.time()
            print(f"Loading viz_ma_pins...")
            customers_df = self.db.execute_query(f"""
                SELECT DeviceID as device_id, Latitude as latitude,
                       Longitude as longitude, Store as store
                FROM {gold}.viz_ma_pins
            """)
            result = customers_df.to_dict('records') if not customers_df.empty else []
            elapsed = time.time() - start
            print(f"Loaded {len(result)} customer locations in {elapsed:.2f}s")
            return sanitize_for_json(result)
        except Exception as e:
            print(f"ERROR loading viz_ma_pins: {str(e)}")
            return []
```

- [ ] **Step 3: Commit**

```bash
git add react-app/models/schemas.py react-app/services/data_service.py
git commit -m "feat: add CustomerLocation schema and data loader"
```

---

### Task 2: Backend — API Endpoint and Init Integration

**Files:**
- Modify: `react-app/api/routes/stores.py:100-115`
- Modify: `react-app/api/routes/init.py:46-53`
- Modify: `react-app/api/routes/init.py:93-120`

- [ ] **Step 1: Add /stores/customers endpoint**

In `react-app/api/routes/stores.py`, add after the `/stores/competitors` endpoint (after line 115):

```python
@router.get("/customers")
async def get_customer_locations():
    """
    Get customer device locations.

    Returns:
        List of customer locations with device ID and home store
    """
    try:
        service = get_data_service()
        return service.load_customers()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Add load_customers to init parallel executor**

In `react-app/api/routes/init.py`, add to the `futures` dict inside the `ThreadPoolExecutor` block (around line 52):

```python
                executor.submit(service.load_customers): 'customer_locations',
```

- [ ] **Step 3: Extract customer_locations from results**

In `react-app/api/routes/init.py`, after the line `ma_boundary = results.get('ma_boundary')` (around line 70), add:

```python
        customer_locations = results.get('customer_locations', [])
```

- [ ] **Step 4: Include customer_locations in response**

In `react-app/api/routes/init.py`, add `customer_locations` to the `network` dict in the return statement. After the `'ma_boundary': ma_boundary,` line:

```python
                'customer_locations': customer_locations,
```

Also update the print statement (around line 89) to include customers:

```python
        print(f"Loaded: {len(stores)} stores, {len(candidates)} candidates, "
              f"{len(partner_data.get('stores', []))} partners, {len(competitors)} competitors, "
              f"{len(customer_locations)} customer locations")
```

- [ ] **Step 5: Commit**

```bash
git add react-app/api/routes/stores.py react-app/api/routes/init.py
git commit -m "feat: add /stores/customers endpoint and include in init"
```

---

### Task 3: Frontend — API Service and Data Hook

**Files:**
- Modify: `react-app/frontend/src/services/api.js:61-64`
- Modify: `react-app/frontend/src/hooks/useStoreData.js:13-23`
- Modify: `react-app/frontend/src/hooks/useStoreData.js:57-71`
- Modify: `react-app/frontend/src/hooks/useStoreData.js:117-126`

- [ ] **Step 1: Add getCustomerLocations API function**

In `react-app/frontend/src/services/api.js`, add after the `getCompetitors` function (after line 64):

```javascript
export async function getCustomerLocations() {
  const response = await api.get('/stores/customers')
  return response.data
}
```

- [ ] **Step 2: Add customerLocations to networkData initial state**

In `react-app/frontend/src/hooks/useStoreData.js`, add `customerLocations: [],` to the initial `networkData` state. Insert after `competitors: [],` (line 19):

```javascript
    customerLocations: [],
```

- [ ] **Step 3: Extract customer_locations from init response**

In `react-app/frontend/src/hooks/useStoreData.js`, in the `loadData` function, add extraction after the competitors line. In the `setNetworkData` call (around line 61-71), add after `competitors: network.competitors || [],`:

```javascript
          customerLocations: network.customer_locations || [],
```

- [ ] **Step 4: Also update the refresh function**

In `react-app/frontend/src/hooks/useStoreData.js`, in the `refresh` callback's `setNetworkData` call (around line 117-126), add after `competitors: network.competitors || [],`:

```javascript
          customerLocations: network.customer_locations || [],
```

- [ ] **Step 5: Commit**

```bash
git add react-app/frontend/src/services/api.js react-app/frontend/src/hooks/useStoreData.js
git commit -m "feat: add customer locations to API service and data hook"
```

---

### Task 4: Frontend — Layer State

**Files:**
- Modify: `react-app/frontend/src/hooks/useMapState.js:6-14`
- Modify: `react-app/frontend/src/hooks/useMapState.js:28-45`

- [ ] **Step 1: Add customerLocations to DEFAULT_LAYERS**

In `react-app/frontend/src/hooks/useMapState.js`, add `customerLocations: false,` to `DEFAULT_LAYERS`. Insert after `currentStores: true,` (line 7):

```javascript
  customerLocations: false,
```

- [ ] **Step 2: Add customerLocations to MODE_LAYERS**

In the same file, add `customerLocations: false,` to both `current` and `expansion` objects in `MODE_LAYERS`. In each object, insert after `currentStores: true,`:

```javascript
    customerLocations: false,
```

- [ ] **Step 3: Commit**

```bash
git add react-app/frontend/src/hooks/useMapState.js
git commit -m "feat: add customerLocations layer toggle state"
```

---

### Task 5: Frontend — Map Markers

**Files:**
- Modify: `react-app/frontend/src/components/map/GeospatialMap.jsx:316-344`
- Modify: `react-app/frontend/src/components/map/GeospatialMap.jsx:349-452`

- [ ] **Step 1: Add CustomerLocationMarkers component**

In `react-app/frontend/src/components/map/GeospatialMap.jsx`, add after the `CompetitorMarkers` component (after line 344):

```jsx
/**
 * Customer location markers (amber haze)
 */
function CustomerLocationMarkers({ customers, visible }) {
  if (!visible || !customers || customers.length === 0) return null

  return (
    <>
      {customers.map((customer, idx) => (
        <CircleMarker
          key={`cust-${idx}`}
          center={[customer.latitude, customer.longitude]}
          pane="markers"
          radius={4}
          pathOptions={{
            fillColor: '#f59e0b',
            color: '#f59e0b',
            weight: 0,
            fillOpacity: 0.5,
          }}
        >
          <Popup className="modern-popup" autoPan={false}>
            <div className="min-w-[120px]">
              <div className="font-semibold text-gray-900">Home Store: {customer.store}</div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}
```

- [ ] **Step 2: Add customerLocations prop to GeospatialMap**

In the `GeospatialMap` function signature (line 349-357), add `customerLocations` to the destructured props:

```jsx
export function GeospatialMap({
  networkData,
  candidates,
  layers,
  salesRange,
  onStoreClick,
  onBoundsChange,
  partnerBrandFilters,
  customerLocations,
}) {
```

- [ ] **Step 3: Render CustomerLocationMarkers in the map**

In the JSX return, add after the `CurrentStoreMarkers` block and before `CandidateMarkers` (after line 421):

```jsx
        {/* Customer locations */}
        <CustomerLocationMarkers
          customers={customerLocations}
          visible={layers.customerLocations}
        />
```

- [ ] **Step 4: Commit**

```bash
git add react-app/frontend/src/components/map/GeospatialMap.jsx
git commit -m "feat: add CustomerLocationMarkers amber haze layer"
```

---

### Task 6: Frontend — Sidebar Toggle

**Files:**
- Modify: `react-app/frontend/src/components/layout/Sidebar.jsx:1-6`
- Modify: `react-app/frontend/src/components/layout/Sidebar.jsx:342-365`

- [ ] **Step 1: Add Users icon import (if not already present)**

In `react-app/frontend/src/components/layout/Sidebar.jsx`, verify that `Users` is already imported from lucide-react on line 5. It is — no change needed. Instead, we need a suitable icon. `Users` is already used for Partnership Recommendations. Use `MapPin` with amber color (already imported). Actually, let's check — we can use the `Circle` icon that's already imported, or just use a small colored dot via a custom element. The simplest approach: use the existing pattern with a custom amber dot, similar to how other layers use their colored icons.

Add the toggle in the NETWORK section of `MapLayersSection`. In `react-app/frontend/src/components/layout/Sidebar.jsx`, insert after the "Current Stores" `LayerToggle` (after line 352) and before the "Expansion Candidates" `LayerToggle`:

```jsx
            <LayerToggle
              icon={<Circle className="w-4 h-4 text-amber-500" style={{ fill: '#f59e0b', strokeWidth: 0 }} />}
              label="Customer Locations"
              checked={layers.customerLocations}
              onChange={() => onToggle('customerLocations')}
            />
```

- [ ] **Step 2: Commit**

```bash
git add react-app/frontend/src/components/layout/Sidebar.jsx
git commit -m "feat: add Customer Locations toggle in sidebar NETWORK section"
```

---

### Task 7: Frontend — Wire Props Through App.jsx

**Files:**
- Modify: `react-app/frontend/src/App.jsx:320-328`

- [ ] **Step 1: Pass customerLocations to GeospatialMap**

In `react-app/frontend/src/App.jsx`, add `customerLocations` prop to the `GeospatialMap` component (around line 320-328):

```jsx
      <GeospatialMap
        networkData={networkData}
        candidates={visibleCandidates}
        layers={layers}
        salesRange={salesRange}
        onStoreClick={selectStore}
        onBoundsChange={updateMapBounds}
        partnerBrandFilters={partnerBrandFilters}
        customerLocations={networkData.customerLocations}
      />
```

- [ ] **Step 2: Commit**

```bash
git add react-app/frontend/src/App.jsx
git commit -m "feat: pass customerLocations data to GeospatialMap"
```

---

### Task 8: Build and Verify

**Files:**
- None (build/test only)

- [ ] **Step 1: Build frontend**

```bash
cd react-app/frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Verify build output**

```bash
ls -la react-app/frontend/dist/assets/
```

Expected: New JS/CSS bundles generated.

- [ ] **Step 3: Commit build artifacts**

```bash
git add react-app/frontend/dist/
git commit -m "build: rebuild frontend with customer locations layer"
```
