# Customer Locations Map Layer

Add a new map layer displaying customer device locations around existing stores in Massachusetts.

## Data Source

- Table: `{catalog}.geo_gold.viz_ma_pins` (currently `jdub_demo.geo_gold.viz_ma_pins`)
- ~5400 rows
- Schema: `DeviceID` (string), `Latitude` (double), `Longitude` (double), `Store` (string)
- Loaded once on app init — no pagination, filtering, or clustering needed

## Backend

### Schema (`react-app/models/schemas.py`)

New `CustomerLocation` model:
- `device_id`: str
- `latitude`: float
- `longitude`: float
- `store`: str

### Data Service (`react-app/services/data_service.py`)

New `load_customers()` method:
- Query: `SELECT DeviceID, Latitude, Longitude, Store FROM {catalog}.{gold_schema}.viz_ma_pins`
- Returns list of CustomerLocation dicts
- Follows existing pattern (same as `load_competitors()`)

### API Route (`react-app/api/routes/expansion.py`)

New endpoint: `GET /stores/customers`
- Returns: `List[CustomerLocation]`
- No query parameters

## Frontend

### State (`react-app/frontend/src/hooks/useMapState.js`)

Add `showCustomerLocations: false` to initial layer visibility state.

### Map (`react-app/frontend/src/components/map/GeospatialMap.jsx`)

New CircleMarker layer for customer locations:
- Color: `#f59e0b` (amber)
- Radius: 4px
- Opacity: 0.5
- Fill opacity: 0.5
- Border: none (weight: 0)
- Pane: `markers` (z-index 450, same as other point layers)
- Popup on click: "Home Store: {store}" — no detail panel interaction
- Conditional render: only when `showCustomerLocations` is true

### Sidebar (`react-app/frontend/src/components/layout/Sidebar.jsx`)

New toggle in NETWORK section:
- Label: "Customer Locations"
- Color indicator: amber dot (`#f59e0b`)
- Position: between "Current Stores" and "Expansion Candidates"
- Default: off

### API Service (`react-app/frontend/src/services/api.js`)

New function: `getCustomerLocations()` → `GET /stores/customers`

### Data Loading (`react-app/frontend/src/App.jsx`)

Add `customerLocations` to the data loaded by `useStoreData` hook. Fetch via `getCustomerLocations()` alongside other init data.

## Visual Design

Amber haze style — small, semi-transparent dots that show customer density without visual clutter. Intentionally the most subtle layer on the map:

| Layer | Color | Radius | Opacity | Border |
|-------|-------|--------|---------|--------|
| Current Stores | `#10b981` green | 8px | 1.0 | 2px white |
| Candidates | `#ef4444` red | 8px | 1.0 | 2px white |
| Partners | `#3b82f6` blue | 6px | 1.0 | 2px white |
| Competitors | `#a855f7` purple | 6px | 1.0 | 2px white |
| **Customers** | **`#f59e0b` amber** | **4px** | **0.5** | **none** |

## Out of Scope

- No store-level filtering (Store column doesn't align with viz_existing_stores store_number)
- No clustering (5400 points renders fine)
- No detail panel integration
- No viewport culling or server-side pagination
