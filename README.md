# LCE Site Selection Platform

Geospatial analytics platform for LCE retail site selection using Databricks, Unity Catalog, and Valhalla routing.

## Overview

### The Pipeline

The platform processes geospatial data through a three-stage medallion architecture to identify optimal retail expansion locations:

**Bronze (Raw Data Ingestion)**
- Ingests store locations, census boundaries, and OpenStreetMap points of interest
- Downloads and processes road network data for routing analysis

**Silver (Data Processing)**
- Generates 5-minute drive-time isochrones around existing stores and competitor locations
- Cleans and categorizes points of interest (restaurants, retail, services)
- Enriches locations with demographic features from CARTO spatial marketplace

**Gold (Analytics & Predictions)**
- Aggregates demographic and POI features at H3 hexagon resolution (avg 0.74 km² cells)
- Generates synthetic sales predictions for expansion candidates based on population, income, and local amenities
- Creates visualization-ready tables with pre-computed metrics for instant app performance
- Identifies partnership opportunities where candidates are near convenience stores

### The App

Interactive dashboard for retail site analysis and expansion planning:

**Existing Network Tab**
- Visualize current store locations with coverage areas (5-min drive-time isochrones)
- View network-wide metrics: total stores, market reach, average demographics per store
- Explore nearby convenience stores and competitors

**Expansion Candidates Tab**
- Browse AI-scored expansion opportunities across Massachusetts
- Filter by predicted revenue, population, and quality tier
- Identify partnership vs. new store opportunities based on convenience store proximity
- View revenue potential and demographic profiles for each location

**Optimizer Tab**
- Run greedy optimization algorithm to select N best locations
- Configure parameters: number of stores, minimum spacing, population/revenue thresholds
- Maximize total revenue while avoiding cannibalization of existing stores
- Export optimized selections to Delta tables for further analysis

All data queries run in real-time against Unity Catalog using pre-computed gold layer tables for sub-second response times.

## Architecture

**Medallion pattern** with Bronze → Silver → Gold layers, orchestrated via Databricks Asset Bundles (DABs).

```
geospatial-retail-site-selection/
├── databricks.yml                    # DABs bundle configuration
├── app/                              # Streamlit dashboard
│   ├── app_v2.py                     # Main app (3 tabs: Existing, Expansion, Optimizer)
│   ├── app.yaml                      # Databricks App config
│   └── requirements.txt
├── resources/                        # DABs job definitions (serverless)
│   ├── bronze_job.yml                # Bronze ingestion job
│   ├── silver_job.yml                # Silver processing job
│   ├── gold_job.yml                  # Gold feature engineering job
│   ├── orchestration_job.yml         # End-to-end pipeline
│   ├── catalog_setup.yml             # Unity Catalog setup
│   └── configs/                      # Feature/variable configs
│       ├── census_variables.yml      # Census ACS variables config
│       ├── poi_config.yml            # POI extraction config
│       └── h3_features_config.yml    # CARTO features config
├── transformations/
│   ├── 01_bronze/                    # Raw data ingestion
│   │   ├── lce_locations.ipynb       # Transform raw store locations
│   │   ├── census_boundaries.ipynb   # TIGER/Line boundaries
│   │   └── extract_pois.ipynb        # POI extraction from OSM
│   ├── 02_silver/                    # Data processing
│   │   ├── clean_pois.ipynb          # POI cleaning and categorization
│   │   ├── create_isochrones.ipynb   # Drive-time polygons (Valhalla API)
│   │   ├── candidate_features_h3.ipynb          # H3 candidate features
│   │   └── aggregate_existing_lce_features.ipynb # Existing store metrics
│   └── 03_gold/                      # Feature engineering & viz prep
│       ├── expansion_prediction.ipynb    # Sales predictions & scoring
│       └── viz_layer_prep.ipynb          # Pre-computed viz tables
└── exploration/                      # Analysis notebooks
    └── ...
```

## Data Pipeline

### Bronze Layer
- **Store Locations**: LCE store locations transformed from raw upload
- **Census Boundaries**: State boundaries (TIGER/Line shapefiles)
- **POIs**: Points of interest extracted from OpenStreetMap

### Silver Layer
- **Isochrones**: 5-minute drive-time polygons via Valhalla routing API (free public server)
- **Cleaned POIs**: Categorized convenience stores and competitors with deduplication
- **H3 Candidate Features**: CARTO spatial features joined to H3 grid cells
- **Existing Store Metrics**: Aggregated features for current LCE locations

### Gold Layer
- **Expansion Predictions**: Sales predictions, quality scoring, and partnership recommendations
- **Viz Tables**: Pre-computed visualization layers with instant query performance
  - `viz_existing_stores`: Current stores with demographics
  - `viz_expansion_candidates`: Scored candidates with partnership flags
  - `viz_convenience`: Convenience store isochrones with candidate proximity
  - `viz_competitors`: Competitor locations
  - `viz_h3_grid`: State-filtered H3 cells for map overlays
  - `viz_network_metrics`: Pre-aggregated KPIs (singleton table)
  - `viz_optimization_results`: Cached optimization runs (96 parameter combinations)

## Data Sources

- **CARTO Marketplace**: Demographics and spatial features at H3 resolution 8
- **Valhalla API**: Drive-time isochrone generation via public routing server (OSM-based)
- **OpenStreetMap**: Points of interest (restaurants, retail, services)
- **US Census**: State boundary geometries (TIGER/Line)

## Deployment

### Prerequisites
- Databricks workspace with Unity Catalog enabled
- Census API key (free): https://api.census.gov/data/key_signup.html
- Databricks CLI installed and authenticated

### Step 1: Configure for Your Workspace

Edit `databricks.yml` and update these **REQUIRED** settings (all marked with ⚠️ in the file):

1. **Workspace Host** (under `targets.production.workspace`)
   ```yaml
   host: https://your-workspace.cloud.databricks.com
   ```

2. **Catalog & Schemas** (under `targets.production.variables`)
   ```yaml
   catalog: your_catalog_name
   bronze_schema: geo_bronze
   silver_schema: geo_silver
   gold_schema: geo_gold
   ```

3. **Census API Key** (under `variables.census_api_key`)
   ```yaml
   census_api_key: "your_api_key_here"
   ```

4. **User Email** (under `variables.user_email`)
   ```yaml
   user_email: "your.email@company.com"
   ```

The `databricks.yml` file has detailed header comments that guide you to each required setting.

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
databricks apps deploy geospatial-site-selection --source-code-path app/
```

## Configuration

All pipeline jobs run on **serverless compute** with Databricks Runtime 17.x (Photon-enabled for geospatial functions).

Key parameters in `databricks.yml`:

**Required:**
- `catalog`: Unity Catalog name
- `census_api_key`: US Census Bureau API key (free at https://api.census.gov/data/key_signup.html)
- `user_email`: Email for job failure notifications

**Geographic Scope:**
- `state_fips`: Target state FIPS code (default: "25" for Massachusetts)
- `state_filter`: State abbreviation for POI filtering (default: "MA")
- `osm_url`: Geofabrik OSM download URL for road network data
- `osm_region`: OSM region name (default: "massachusetts")

**Data Sources:**
- `carto_table`: CARTO Marketplace H3 features table (default: USA H3 res 8)
- `acs_year`: American Community Survey year (default: "2023")

See `databricks.yml` header comments for full configuration details and deployment instructions.
