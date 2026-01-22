# Retail Site Selection Platform

AI-powered geospatial analytics for retail expansion planning. Built on Databricks with Unity Catalog, H3 spatial indexing, and real-time optimization.

---

## What It Does

Transform raw location data into actionable expansion insights through a three-layer medallion pipeline:

| Layer | Purpose | Output |
|-------|---------|--------|
| **Bronze** | Raw data ingestion | Store locations, census data, OSM POIs, road networks |
| **Silver** | Geospatial processing | Drive-time isochrones, demographic enrichment, spatial features |
| **Gold** | ML predictions & analytics | Scored candidates, optimization results, pre-computed viz tables |

**End Result:** Interactive dashboard with ML-predicted sales forecasts, greedy optimization algorithm for multi-site selection, and partnership opportunity detection.

---

## Interactive Dashboard

### 📍 Existing Network
View current store footprint with 5-minute drive-time coverage areas. Analyze network-wide KPIs: market reach, demographics, nearby competitors.

### 🎯 Expansion Candidates
Browse AI-scored opportunities ranked by predicted revenue. Filter by quality tier, population density, and urbanity. Identify partnership vs. greenfield opportunities based on convenience store proximity.

### 🧮 Optimizer
Run greedy optimization to select N best locations with configurable spacing constraints. Maximize total revenue while preventing cannibalization. Export selections to Delta tables.

> **Performance:** Sub-second queries via pre-computed gold tables. Optimization results cached for 27 parameter combinations (10/50/100 stores × 1-3 mile spacing).

---

## Architecture

```
geospatial-retail-site-selection/
├── databricks.yml              # Asset Bundle config
├── react-app/                  # Modern React + FastAPI dashboard
│   ├── main.py                 # FastAPI entry point
│   ├── app.yaml                # Databricks Apps config
│   ├── api/routes/             # API endpoints (init, stores, expansion, optimization)
│   ├── core/                   # Config and database connection
│   ├── services/               # Data service layer
│   └── frontend/               # React + Vite + Tailwind + Leaflet
├── resources/                  # DABs job definitions (serverless)
│   ├── bronze_job.yml
│   ├── silver_job.yml
│   ├── gold_job.yml
│   └── orchestration_job.yml   # End-to-end pipeline
└── transformations/
    ├── 01_bronze/              # Raw ingestion notebooks
    ├── 02_silver/              # Geospatial processing
    └── 03_gold/                # Feature engineering & ML
```

**Key Technologies:**
- **H3 Resolution 8** (~0.74 km² hexagons) for spatial aggregation
- **Valhalla API** for drive-time isochrones
- **XGBoost** for sales prediction with spatial cross-validation
- **CARTO Marketplace** for demographic features
- **React + FastAPI** for interactive dashboard with Leaflet maps

---

## Pipeline Flow

### 🟤 Bronze: Ingestion

| Notebook | Input | Output | Process |
|----------|-------|--------|---------|
| `store_locations.ipynb` | Raw store table | Standardized locations | Filter open stores, geocode |
| `census_boundaries.ipynb` | TIGER/Line API | State geometries | Download MA + training states |
| `extract_pois.ipynb` | OSM PBF file | Raw POIs | Extract via osmium |

### ⚪ Silver: Processing

| Notebook | Input | Output | Process |
|----------|-------|--------|---------|
| `clean_pois.ipynb` | Raw POIs | Categorized POIs | Classify competitors, convenience stores |
| `create_isochrones.ipynb` | Locations + road network | 5-min drive polygons | Valhalla API calls |
| `candidate_features_h3.ipynb` | CARTO H3 data | Enriched features | Join demographics, POI density |

### 🟡 Gold: Analytics

| Notebook | Input | Output | Process |
|----------|-------|--------|---------|
| `agg_h3_features_candidates.ipynb` | Candidate isochrones + H3 | Aggregated features | Polyfill, aggregate, exclude overlaps |
| `agg_h3_features_current_stores.ipynb` | Store isochrones + H3 + sales | Store baseline features | Training data for ML model |
| `predict_candidate_sales.ipynb` | Features + sales history | Scored candidates + MLflow model | XGBoost with spatial CV |
| `viz_layer_prep.ipynb` | All gold tables | 7 viz tables | Pre-compute distances, optimization, KPIs |

> 💡 **Optimization Details:** See `docs/gold_layer_inefficiency_plan.md` for performance tuning (reduced optimization grid from 96→27 combinations, ~70% storage savings).

---

## Data Sources

| Source | Purpose | Resolution |
|--------|---------|------------|
| **CARTO Marketplace** | Demographics, urbanity, activity index | H3 resolution 8 |
| **Valhalla (OSM)** | Drive-time routing | 5-minute isochrones |
| **OpenStreetMap** | POIs (restaurants, retail, services) | Point-level |
| **US Census TIGER/Line** | State boundaries | Polygon |

---

## Quick Start

### 1️⃣ Prerequisites

- Databricks workspace with Unity Catalog
- [Census API key](https://api.census.gov/data/key_signup.html) (free)
- Databricks CLI installed

### 2️⃣ Configure

Edit `databricks.yml` and set:

```yaml
# Workspace
host: https://your-workspace.cloud.databricks.com

# Catalog
catalog: your_catalog_name
bronze_schema: geo_bronze
silver_schema: geo_silver
gold_schema: geo_gold

# Keys
census_api_key: "your_key_here"
user_email: "you@company.com"
```

### 3️⃣ Deploy Bundle

```bash
# Production (recommended)
databricks bundle deploy

# Development (adds dev_{username}_ prefix)
databricks bundle deploy -t development
```

**Creates:**
- 3 schemas: `geo_bronze`, `geo_silver`, `geo_gold`
- 1 volume: `osm_data` (for POI extraction)
- 4 jobs: bronze, silver, gold, orchestration

### 4️⃣ Upload Store Data

Manually upload your raw store table to:
```
{catalog}.{bronze_schema}.store_locations_raw
```

**Required columns:**
```
LocationKey, Y_Coordinate_Latitude, X_Coordinate_Longitude,
Address1, City, State, Zip, StoreStatus
```

### 5️⃣ Run Pipeline

```bash
# Option A: Full orchestration
databricks bundle run site_selection_pipeline

# Option B: Individual layers
databricks bundle run bronze_census_ingestion
databricks bundle run silver_poi_processing
databricks bundle run gold_feature_engineering
```

### 6️⃣ Deploy App (Optional)

```bash
# Build frontend first
cd react-app/frontend
npm install && npm run build
cd ../..

# Deploy to Databricks Apps
databricks apps deploy geospatial-site-selection --source-code-path react-app/
```

---

## Configuration

**Compute:** All jobs use serverless with Databricks Runtime 17.x (Photon-enabled for geospatial functions).

**Key Parameters:**

| Parameter | Purpose | Default |
|-----------|---------|---------|
| `state_fips` | Target state FIPS code | `"25"` (MA) |
| `state_filter` | State abbreviation filter | `"MA"` |
| `osm_url` | Geofabrik download URL | Massachusetts extract |
| `carto_table` | CARTO H3 features | USA H3 res 8 |
| `acs_year` | Census ACS year | `"2023"` |

See `databricks.yml` header comments for full configuration options.

---

## Troubleshooting

**Schema already exists?** Bundle deployment is idempotent. If schemas exist, they'll be skipped.

**Volume not created?**
```bash
# Check volumes
databricks volumes list {catalog}.geo_bronze

# Manually create if missing
databricks volumes create osm_data {catalog}.geo_bronze --volume-type MANAGED
```

**Development isolation:** Use `-t development` flag to add `dev_{username}_` prefix to all resources.

---

**Built with:** Databricks • Unity Catalog • H3 • XGBoost • React • FastAPI • Leaflet • Valhalla • CARTO
