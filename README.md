# Little Caesars Site Selection - Massachusetts

Geospatial analytics platform for Little Caesars retail site selection using Databricks, Unity Catalog, and OSRM routing.

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
│       ├── store_config.yml          # Store & sales config
│       ├── poi_config.yml            # POI extraction config
│       ├── h3_features_config.yml    # CARTO features config
│       └── isochrone_config.yml      # OSRM isochrone config
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
- **Store Locations**: Little Caesars stores in Massachusetts (pre-loaded)
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

1. **Current Network**: View Little Caesars stores in MA with sales, 5-min isochrones, and key demographics
2. **Expansion Candidates**: Map of potential new locations with cannibalization filtering and sales estimates
3. **Network Optimizer**: Greedy algorithm to select optimal N locations maximizing coverage and revenue

Features:
- Folium map visualizations with MA state boundary
- Real-time SQL queries to Unity Catalog
- Session state persistence for optimization results
- Export to Delta table

## Data Sources

- **CARTO Marketplace**: Spatial features aggregated at H3 resolution 8 (`carto_spatial_features_usa_h3_res_8`)
- **OpenStreetMap**: POI data and road network
- **US Census**: State boundaries

## Deployment

### Prerequisites
- Databricks workspace with Unity Catalog
- Catalog: `jdub_demo_aws`
- Schemas: `geo_bronze`, `geo_silver`, `geo_gold`
- Environment variable: `DATABRICKS_TOKEN`

### Deploy Bundle
```bash
source .env
databricks bundle deploy --target development
```

### Run Jobs
```bash
databricks bundle run bronze_census_ingestion --target development
databricks bundle run silver_poi_processing --target development
databricks bundle run gold_feature_engineering --target development
```

### Deploy App
```bash
databricks apps deploy lce-site-selection --source-code-path app/
```

## Configuration

All job parameters are configurable via `databricks.yml` variables:
- `catalog`: Unity Catalog name
- `state_fips`: Target state (25 = Massachusetts)
- `node_type`: Cluster node type (m5d.xlarge)

Spark version: `17.3.x-scala2.13` with Photon runtime (required for ST_* geospatial functions).
