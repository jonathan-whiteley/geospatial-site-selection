# LCE Site Selection Platform

Geospatial analytics platform for LCE retail site selection using Databricks, Unity Catalog, and OSRM routing.

## Architecture

**Medallion pattern** with Bronze → Silver → Gold layers, orchestrated via Databricks Asset Bundles (DABs).

```
site-selection-demo/
├── databricks.yml                    # DABs bundle configuration
├── app/                              # Streamlit dashboard
│   ├── app.py                        # Main app (3 tabs)
│   ├── app.yaml                      # Databricks App config
│   └── requirements.txt
├── resources/                        # DABs job definitions
│   ├── bronze_job.yml                # Bronze ingestion job
│   ├── silver_job.yml                # Silver processing job
│   ├── gold_job.yml                  # Gold feature engineering job
│   ├── orchestration_job.yml         # End-to-end pipeline
│   ├── catalog_setup.yml             # Unity Catalog setup
│   ├── init_scripts/                 # Cluster init scripts
│   │   └── init-osrm.sh              # OSRM routing engine setup (optional)
│   └── configs/                      # Feature/variable configs
│       ├── census_variables.yml      # Census ACS variables config
│       ├── poi_config.yml            # POI extraction config
│       └── h3_features_config.yml    # CARTO features config
├── transformations/
│   ├── 01_bronze/                    # Raw data ingestion
│   │   ├── osm_download.ipynb        # Geofabrik OSM PBF download
│   │   ├── census_boundaries.ipynb   # TIGER/Line boundaries
│   │   └── extract_pois.ipynb        # POI extraction from OSM
│   ├── 02_silver/                    # Data processing
│   │   ├── clean_pois.ipynb          # POI cleaning and categorization
│   │   └── create_osrm_isochrones.ipynb  # Drive-time polygon generation
│   └── 03_gold/                      # Feature engineering
│       ├── create_h3_features_carto.ipynb    # CARTO marketplace integration
│       ├── aggregate_trade_area_features.ipynb  # Trade area metrics
│       └── predict_seed_point_sales.ipynb       # Sales prediction model
└── exploration/                      # Analysis notebooks
    ├── generate_rmc_retail_locations.ipynb
    └── sales_driver_analysis.ipynb
```

## Data Pipeline

### Bronze Layer
- **Store Locations**: LCE store locations (pre-loaded)
- **OSM Road Network**: Geofabrik PBF files for routing
- **Census Boundaries**: State boundaries (TIGER/Line)
- **POIs**: Points of interest extracted from OSM

### Silver Layer
- **Isochrones**: 5-minute drive-time polygons via OSRM
- **Cleaned POIs**: Categorized and deduplicated

### Gold Layer
- **H3 Features**: CARTO Marketplace demographics and spatial features (H3 resolution 8)
- **Trade Area Features**: Aggregated metrics per isochrone polygon
- **Sales Predictions**: Synthetic sales based on demographics and POI features
- **Expansion Candidates**: Filtered H3 cells for new store opportunities

## Streamlit Application

Three-tab dashboard for site analysis:

1. **Current Network**: View LCE store locations with sales, 5-min isochrones, and key demographics
2. **Expansion Candidates**: Map of potential new locations with cannibalization filtering and sales estimates
3. **Network Optimizer**: Greedy algorithm to select optimal N locations maximizing coverage and revenue

Features:
- Folium map visualizations with state boundary overlay
- Real-time SQL queries to Unity Catalog
- Session state persistence for optimization results
- Export to Delta table

## Data Sources

- **CARTO Marketplace**: Spatial features aggregated at H3 resolution 8 (`carto_spatial_features_usa_h3_res_8`)
- **OpenStreetMap**: POI data and road network
- **US Census**: State boundaries

## Deployment

### Prerequisites
- Databricks workspace with Unity Catalog enabled
- Census API key (free): https://api.census.gov/data/key_signup.html
- Databricks CLI installed and authenticated

### Step 1: Configure for Your Workspace

Edit `databricks.yml` and update these **REQUIRED** settings (marked with ⚠️):

1. **Workspace Host** (line 53)
   ```yaml
   host: https://your-workspace.cloud.databricks.com
   ```

2. **Catalog & Schemas** (lines 56-59)
   ```yaml
   catalog: your_catalog_name
   bronze_schema: geo_bronze
   silver_schema: geo_silver
   gold_schema: geo_gold
   ```

3. **Census API Key** (line 83)
   ```yaml
   census_api_key: "your_api_key_here"
   ```

4. **User Email** (line 122)
   ```yaml
   user_email: "your.email@company.com"
   ```

See the header comments in `databricks.yml` for full configuration details.

### Step 2: Deploy Bundle (Creates Unity Catalog Resources)

**IMPORTANT**: Deploy the bundle to create schemas, volumes, and jobs:

```bash
# Production deployment (uses exact schema names - recommended)
databricks bundle deploy

# Development deployment (adds dev_{username}_ prefix for isolation)
databricks bundle deploy -t development
```

This creates:
- Schemas: `{catalog}.geo_bronze`, `{catalog}.geo_silver`, `{catalog}.geo_gold`
- Volume: `{catalog}.geo_bronze.osm_data` (required for POI ingestion)
- Jobs: bronze_census_ingestion, silver_poi_processing, gold_feature_engineering

**Note**: Production mode (default) uses exact schema names. Development mode adds `dev_{username}_` prefix to avoid conflicts between developers.

**If schemas already exist** (from a previous deployment):
- The bundle will detect this and skip schema creation (idempotent behavior)
- If you get "Schema already exists" errors, see troubleshooting in `databricks.yml` header comments

**Verify the volume was created** (troubleshooting step):
```bash
databricks volumes list {catalog}.geo_bronze
```

Expected output should include `osm_data`. If not listed, redeploy the bundle or create the volume manually:
```bash
databricks volumes create osm_data {catalog}.geo_bronze --volume-type MANAGED
```

### Step 3: Upload RAW LCE Store Locations

Manually upload your **raw** store locations table to:
```
{catalog}.{bronze_schema}.lce_locations_raw
```

**Required columns** (raw format from source system):
- `LocationKey` - Store identifier
- `Y_Coordinate_Latitude` - Latitude
- `X_Coordinate_Longitude` - Longitude
- `Address1` - Street address
- `City` - City name
- `State` - State code
- `Zip` - ZIP code
- `StoreStatus` - Store status (e.g., "Open Store")

**Note**: The bronze job will transform this raw table into the standardized `lce_locations_mass` table with:
- Filtered to MA and open stores only
- Standardized column names (location_id, store_name, latitude, longitude, etc.)
- Added store name prefix: "Little Caesar's - {City}"

### Step 4: Run Pipeline Jobs

Run jobs in order (or use the orchestration job to run all):

```bash
# Option A: Run individual jobs (production mode - uses exact schema names)
databricks bundle run bronze_census_ingestion
databricks bundle run silver_poi_processing
databricks bundle run gold_feature_engineering

# Option B: Run full pipeline (runs all jobs in sequence)
databricks bundle run site_selection_pipeline

# For development mode (with dev_{username}_ prefix):
databricks bundle run bronze_census_ingestion -t development
```

### Step 5: Deploy Streamlit App (Optional)

```bash
databricks apps deploy lce-site-selection --source-code-path app/
```

## Configuration

All job parameters are configurable via `databricks.yml` variables:
- `catalog`: Unity Catalog name
- `state_fips`: Target state FIPS code
- `node_type`: Cluster node type (m5d.xlarge)

Spark version: `17.3.x-scala2.13` with Photon runtime (required for ST_* geospatial functions).
