You are working on a **Retail Site Selection Platform** — an AI-powered geospatial analytics application built on Databricks. The app helps a retail brand (a food/restaurant chain in Massachusetts) identify, evaluate, and prioritize new store locations using machine learning, spatial analysis, and a greedy optimization algorithm.

---

## Application Architecture

The app is a full-stack Databricks App:
- **Backend:** FastAPI (Python) deployed to Databricks Apps, authenticated via Service Principal OAuth
- **Frontend:** React + Vite + Tailwind CSS + Leaflet.js for interactive maps
- **Data Pipeline:** Databricks Asset Bundles with a three-layer medallion architecture (Bronze → Silver → Gold), executed as serverless jobs

---

## Data Pipeline

### Bronze Layer (Raw Ingestion)
- **Store locations** — current brand store data with fields: `LocationKey`, `Y_Coordinate_Latitude`, `X_Coordinate_Longitude`, `Address1`, `City`, `State`, `Zip`, `StoreStatus`
- **US Census TIGER/Line** — state boundary geometries (used for filtering to Massachusetts)
- **OpenStreetMap POIs** — raw points of interest extracted via osmium from an OSM PBF file (restaurants, retail, convenience stores, competitors)

### Silver Layer (Geospatial Processing)
- **Drive-time isochrones** — 5-minute drive-time polygons computed via the Valhalla routing API for each store and each candidate location
- **POI classification** — OSM POIs categorized into: direct competitors, potential partner stores (Walmart, 7-Eleven/Speedway, Shaw's), and general POIs
- **H3 spatial features** — demographic and activity data from CARTO Marketplace joined at H3 resolution 8 (~0.74 km² hexagons), including population, urbanity index, and activity index

### Gold Layer (ML + Pre-computed Analytics)
- **Candidate feature aggregation** — for each candidate H3 cell: aggregate demographics, POI density, distance to nearest existing store, and partner store proximity within the 5-min isochrone
- **Current store features** — same aggregation for existing stores, joined with actual historical sales — used as training data
- **Sales prediction model** — XGBoost model with spatial cross-validation, trained on existing store features + actual sales; applied to all candidate locations to produce `predicted_annual_sales`
- **Visualization tables** — 7 pre-computed gold tables for sub-second API response:
  - `viz_existing_stores` — current store locations with sales and H3 features
  - `viz_expansion_candidates` — all candidate H3 cells with ML predictions and enriched attributes
  - `viz_partners` — potential partner store locations with their 5-min trade area isochrones and overlapping candidate counts
  - `viz_competitors` — competitor store locations
  - `viz_optimization_results` — pre-computed greedy optimization results across a parameter grid
  - `viz_network_metrics` — aggregate KPIs for the current store network
  - `isochrones_lce` — 5-minute drive-time polygons for current stores (in silver, joined at query time)

---

## Key Data Fields

**Expansion Candidates** (per H3 cell):
- `h3_cell_id` — H3 index at resolution 8
- `latitude`, `longitude`, `center_lat`, `center_lon`
- `city`, `state`
- `predicted_annual_sales` — XGBoost ML prediction
- `population` — within 5-min isochrone
- `total_poi_count` — all OSM POIs in isochrone
- `min_distance_to_existing` — miles to nearest current store
- `nearest_existing_store` — store number of nearest current store
- `within_partner_isochrone` — boolean: is this candidate within a partner store's 5-min trade area?
- `partner_store_name`, `partner_city`, `partner_drive_time`, `partner_brand`, `partner_type`
- `fulfillment_strategy` — `"Partner Fulfillment"` (co-locate with partner) or `"New Store"` (greenfield)
- `cannibalization_risk` — `High`, `Medium`, `Low`, or `None`
- `sales_rank`, `region`
- `geometry_geojson` — H3 cell boundary polygon

**Current Stores:**
- `store_number`, `city`, `state`, `latitude`, `longitude`
- `annual_sales` — actual reported sales
- `population`, `total_poi_count`, `h3_cell_id`
- `geometry_geojson` — H3 cell boundary polygon

**Partner Stores:**
- `name`, `latitude`, `longitude`, `poi_category`, `partner_brand`
- `isochrone_geojson` — 5-min trade area polygon
- `candidate_count_in_isochrone` — how many expansion candidates fall within this trade area
- `total_candidate_sales_in_isochrone` — total predicted revenue of those candidates

**Optimization Results:**
- Pre-computed for a grid: `max_stores` ∈ {10, 50}, `min_distance_new` ∈ {2.0, 3.0} miles, `min_distance_existing` ∈ {2.0, 3.0} miles
- Returns: list of selected H3 cells, selected count, total predicted sales

---

## Application Features

### 1. Current Network View
Displays the existing store footprint in Massachusetts:
- Store markers on a Leaflet map with click-to-detail popups
- 5-minute drive-time isochrone overlays showing trade areas
- Partner store locations and their trade area polygons
- Competitor store locations
- KPI bar showing: Total Stores, Total Annual Sales, "5-min Hunger Satisfaction" coverage %, Avg Store Sales

### 2. Expansion Candidates View
Browsable list and map of AI-scored candidate locations:
- Filterable by min predicted sales and min population (sliders)
- Filterable by fulfillment strategy: Partner Fulfillment vs. New Store
- Filterable by partner brand (Walmart, 7-Eleven/Speedway, Shaw's)
- Viewport-aware: only candidates visible in the current map extent are counted in sidebar metrics
- Metrics: candidate count, % partnership opportunity, total revenue potential, partnership revenue potential
- Partnership Recommendations section summarizing partner stores in the current viewport

### 3. Optimizer
Greedy optimization to select the best N locations while respecting spacing constraints:
- Parameters: max stores (10 or 50), min distance between new stores (2 or 3 miles), min distance from existing stores (2 or 3 miles)
- O(1) lookup against pre-computed results (snaps user inputs to nearest grid value)
- Results overlaid on map, replacing the full candidate set
- CSV export of selected or filtered candidates with all key fields

### 4. AI Expansion Agent (Chat)
Embedded conversational AI in the sidebar:
- Natural language interface backed by a Databricks Model Serving endpoint (multi-agent system)
- Proxied through FastAPI with OAuth authentication
- Quick-start questions: "What are the top 5 expansion opportunities?", "Show expansion candidates in Boston Metro with low competition", "Show existing store performance"
- Answers questions about current store performance, expansion opportunities, and partnership potential

---

## Technical Stack Summary

| Layer | Technology |
|---|---|
| Spatial indexing | H3 resolution 8 |
| Drive-time routing | Valhalla / OpenStreetMap |
| ML model | XGBoost with spatial cross-validation |
| Demographic data | CARTO Marketplace (H3 res 8) |
| POI data | OpenStreetMap (osmium extraction) |
| Map rendering | React-Leaflet |
| Backend | FastAPI on Databricks Apps |
| Data platform | Databricks Unity Catalog, Delta Lake |
| Pipeline orchestration | Databricks Asset Bundles (serverless jobs) |
| AI agent | Databricks Model Serving (multi-agent) |
