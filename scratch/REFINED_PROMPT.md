# Refined Prompt: Geospatial Retail Site Selection Pipeline Refactoring

## Context

You have an existing geospatial retail site selection platform built on Databricks with a medallion architecture (Bronze/Silver/Gold). The system currently analyzes "RMC Retail" stores but needs to be refactored for **Little Caesars** stores in **Massachusetts**. The goal is to simplify the pipeline, make it self-contained, integrate marketplace data, and maintain the existing Streamlit app functionality.

## Current Architecture

**Tech Stack:**
- Databricks with Unity Catalog
- Medallion architecture: Bronze (raw) → Silver (cleaned) → Gold (features/analytics)
- Streamlit app for visualization
- **OSRM ONLY** for drive-time isochrones (5 min trade areas)
- H3 hexagonal grid (resolution 8) for spatial features
- Databricks Asset Bundles (DABs) for orchestration

**Catalog Structure:**
- Catalog: `jdub_demo_aws`
- Schemas: `geo_bronze`, `geo_silver`, `geo_gold`

**Key Files:**
- `databricks.yml` - DABs configuration
- `app/app.py` - Streamlit dashboard with 3 tabs
- `transformations/` - Notebook-based ETL (01_bronze/, 02_silver/, 03_gold/)
- `resources/configs/` - YAML configs for POI, census, H3 features, isochrones

## Required Changes

### 1. Replace H3 Feature Engineering with CARTO Marketplace Data

**Current State:**
- Custom pipeline aggregates Census demographics and OSM POIs at H3 resolution 8
- Table: `jdub_demo_aws.geo_gold.h3_features_gold`
- Config: `resources/configs/h3_features_config.yml`

**Target State:**
- Use CARTO marketplace table: `carto_spatial_features_usa_h3_res_8.carto.derived_spatialfeatures_usa_h3res8_v1_yearly_v3`
- This table already contains aggregated demographics and spatial features at H3 res 8
- Schema available in `z_scratch/CARTO_Spatial_Features__USA__H3_Res__8_.csv`

**Actions:**
- Filter CARTO table to Massachusetts only (use `h3` column to match MA boundaries)
- Create a view or table `geo_gold.h3_features_carto` that maps CARTO columns to expected schema
- Update `resources/configs/h3_features_config.yml` to reference CARTO columns
- Remove deprecated column dependencies:
  - ❌ Remove: `income_100k_125k`, `income_125k_150k`, `income_150k_200k`, `income_200k_plus`, `bachelors_degree`, `masters_degree`
  - ✅ Use CARTO equivalents or aggregate columns (e.g., `female_25_to_29`, `female_30_to_34`, `income_75000_to_99999`, `income_100000_to_124999`)
- **Keep** the POI extraction pipeline (`transformations/01_bronze/extract_pois.ipynb`, `transformations/02_silver/clean_pois.ipynb`) for creating `geo_silver.osm_pois` table

### 2. Update Store Location Tables

**Current State:**
- Current stores: `jdub_demo_aws.geo_bronze.rmc_retail_locations_grocery`
- Competitors: `jdub_demo_aws.geo_bronze.competitor_locations`

**Target State:**
- Current stores: `jdub_demo_aws.geo_bronze.lce_locations_mass` (Little Caesars in Massachusetts)
- **Remove all competitor-related features** (ValueMart, QuickShop Market, etc.)

**Actions:**
- Create new config: `resources/configs/store_config.yml`
  ```yaml
  store_locations:
    table: "jdub_demo_aws.geo_bronze.lce_locations_mass"
    required_columns:
      - store_number    # string or int
      - latitude        # double
      - longitude       # double
      - city            # string
      - state           # string
      - address         # string (optional)
      - zip_code        # string (optional)
  
  sales_data:
    # Historical sales table (placeholder structure for future use)
    historical_table: "jdub_demo_aws.geo_bronze.lce_sales_historical"
    historical_columns:
      - store_number    # string or int
      - annual_sales    # double
      - sales_date      # date (optional for historical tracking)
    
    # For now, generate synthetic sales using this formula
    synthetic_formula:
      enabled: true
      base_sales: 300000
      description: "Synthetic sales generation based on trade area features"
      factors:
        - population_density       # from CARTO h3 features
        - poi_count               # from osm_pois aggregated per isochrone
        - young_adults_count      # CARTO age demographics (18-34)
        - high_income_households  # CARTO income features ($75k+)
        - urbanicity_score        # derived from CARTO population density
  ```
- Update all references from `rmc_retail_locations_grocery` → `lce_locations_mass`
- Remove all competitor distance calculations from feature engineering
- Remove competitor references from `h3_features_config.yml` and other configs
- Update `migration_notes.md` tracking file

### 3. Standardize on OSRM for Isochrones (Remove Valhalla/Mapbox)

**Current State:**
- Multiple isochrone methods: OSRM, Mapbox, Valhalla
- Config: `resources/configs/isochrone_config.yml`, `valhalla_config.json`
- Notebooks: `create_osrm_isochrones.ipynb`, `urbanicity_isochrones_valhalla.ipynb`, `create_mapbox_isochrones.py`
- Init scripts: `init-valhalla.sh`, `init-valhalla-simple.sh`
- Debug: `notebooks/debug_valhalla_install.py`

**Target State:**
- **OSRM ONLY** for 5-minute drive time isochrones
- Single output table: `geo_silver.lce_isochrones_5min`
- Clean removal of all Valhalla/Mapbox dependencies

**Actions:**
- Update `resources/configs/isochrone_config.yml`:
  - Set `drive_time_buckets: [5]`
  - Update `input_tables.lce` to `"jdub_demo_aws.geo_bronze.lce_locations_mass"`
  - Remove competitor isochrone generation sections
  - Remove any `urbanicity_routing` configuration (Valhalla-specific)
  - Keep only OSRM endpoint configuration
- **Delete obsolete files:**
  - `transformations/02_silver/urbanicity_isochrones_valhalla.ipynb`
  - `transformations/02_silver/create_mapbox_isochrones.py`
  - `resources/configs/valhalla_config.json`
  - `resources/init_scripts/init-valhalla.sh`
  - `resources/init_scripts/init-valhalla-simple.sh`
  - `notebooks/debug_valhalla_install.py`
- Update `databricks.yml`:
  - Remove `valhalla_cluster_id` variable
  - Remove `mapbox_token` variable
  - Remove references to Valhalla init scripts
- Update `resources/silver_job.yml`:
  - Remove Valhalla/Mapbox isochrone tasks
  - Keep only OSRM isochrone task: `create_lce_isochrones_osrm`
- Update README to remove Valhalla setup instructions
- Verify OSRM endpoint configuration: `http://localhost:5000`
- Test `create_osrm_isochrones.ipynb` generates valid polygons
- Output schema: `store_number`, `geometry` (WKT polygon), `drive_time_minutes` (always 5), `area_sqkm`

### 4. Clean Up Pipeline Dependencies

**Current Issues:**
- Tables created outside pipeline in `exploration/` folder referenced by app
- Examples: `generate_rmc_retail_locations.ipynb`, `sales_driver_analysis.ipynb`

**Target State:**
- All tables used by app must be created within Bronze/Silver/Gold pipeline
- Exploration notebooks for analysis only, not production data generation

**Actions:**
- Audit `app/app.py` for all table references
- Move any production table creation logic from `exploration/` into appropriate medallion layer
- Update job orchestration (`resources/orchestration_job.yml`) to ensure correct dependency order:
  1. Bronze: Census boundaries, OSM download, POI extraction, LCE locations (pre-loaded)
  2. Silver: POI cleaning, OSRM isochrones
  3. Gold: CARTO filtering, trade area aggregation, sales synthesis, expansion candidates

### 5. Update Streamlit App

**Current Functionality (3 tabs):**

**Tab 1: Current Network**
- Interactive map of Massachusetts with state boundary
- Plot Little Caesars stores with current sales (synthetic formula)
- 5-min drive time isochrones as blue polygons around stores
- Metrics: Total stores, total sales, avg sales per store, avg population per trade area
- Sales driver cards showing key demographics (**remove competitor cards**)

**Tab 2: Expansion Candidates**
- Map showing current stores (green) + expansion candidates (blue)
- Candidates identified via:
  - H3 cells NOT within existing 5-min isochrones (avoid cannibalization)
  - Minimum distance from existing stores (configurable slider)
  - Predicted sales > threshold (based on CARTO features)
- Filters: Minimum predicted sales, minimum population
- Button to select filtered candidates for optimization

**Tab 3: Network Optimizer**
- Configurable sliders:
  - Max number of new stores (default: 5)
  - Min distance between new stores (default: 3 miles)
  - Min distance from existing stores (default: 2 miles)
  - Revenue weight vs Population weight (optional enhancement)
- Optimization algorithm: Greedy selection maximizing weighted score
- Output: Map with recommended locations (gold markers), predicted revenue table
- Save results to `geo_gold.lce_expansion_final`

**Required Updates:**
- Replace all `rmc_` table references with `lce_` equivalents:
  - `gold_rmc_retail_location_sales` → `geo_gold.lce_stores_with_sales`
  - `gold_rmc_retail_locations_grocery_isochrones_features` → `geo_gold.lce_trade_area_features`
  - `rmc_retail_locations_grocery` → `geo_bronze.lce_locations_mass`
- Remove competitor-related queries and visualizations (ValueMart, QuickShop cards)
- Update sales driver cards to use CARTO features instead of deprecated columns:
  - Young Adults: Sum of CARTO `female_18_to_24`, `female_25_to_29`, `male_18_to_24`, `male_25_to_29`
  - High Income HH: Sum of CARTO income columns ≥ $100k
  - Higher Education: Use CARTO education columns if available
  - POI Count: From `geo_silver.osm_pois` aggregated per isochrone
- Fix MA state boundary query: `SELECT ST_AsGeoJSON(geometry) FROM geo_bronze.census_states WHERE state_abbr = 'MA'` (note: `census_states`, not `bronze_census_states`)

## Expected Deliverables

### Pipeline Tables (All Self-Contained)

**Bronze Layer:**
```
geo_bronze.lce_locations_mass              # Input: Little Caesars stores (pre-loaded)
geo_bronze.lce_sales_historical            # Input: Historical sales (empty/placeholder for now)
geo_bronze.osm_massachusetts_pbf           # OSM road network for OSRM
geo_bronze.osm_pois_raw                    # Raw POIs from OSM
geo_bronze.census_states                   # State boundaries (MA focus)
```

**Silver Layer:**
```
geo_silver.osm_pois                        # Cleaned/categorized POIs
geo_silver.lce_isochrones_5min             # 5-min drive time polygons (OSRM)
```

**Gold Layer:**
```
geo_gold.h3_features_carto                 # CARTO features filtered to MA H3 cells
geo_gold.lce_trade_area_features           # Aggregated features per isochrone
geo_gold.lce_stores_with_sales             # Stores + synthetic sales
geo_gold.lce_expansion_candidates          # Top expansion H3 cells (non-cannibalized)
geo_gold.lce_expansion_final               # User-selected expansion locations from optimizer
```

### Updated/New Configs

1. `resources/configs/store_config.yml` - **NEW** file for store/sales configuration
2. `resources/configs/h3_features_config.yml` - Updated for CARTO columns
3. `resources/configs/isochrone_config.yml` - Simplified for LCE + OSRM only (remove Valhalla/Mapbox sections)
4. `resources/configs/poi_config.yml` - Keep as-is (still needed for POI extraction)

### Updated Notebooks

**Bronze:**
- `transformations/01_bronze/extract_pois.ipynb` - Minor updates for MA focus
- `transformations/01_bronze/census_boundaries.ipynb` - Ensure creates `geo_bronze.census_states`

**Silver:**
- `transformations/02_silver/clean_pois.ipynb` - Keep as-is
- `transformations/02_silver/create_osrm_isochrones.ipynb` - Update for LCE table, 5 min only

**Gold:**
- `transformations/03_gold/create_h3_features.ipynb` - **REFACTOR** to use CARTO table
- `transformations/03_gold/aggregate_trade_area_features.ipynb` - Update for LCE isochrones + CARTO features
- `transformations/03_gold/predict_seed_point_sales.ipynb` - Update for synthetic sales formula using CARTO

### Updated App

- `app/app.py` - All 3 tabs working against new LCE tables, no competitor logic
- Queries optimized for performance with `@st.cache_data`
- Visualizations updated for single-brand analysis (Little Caesars only)

### Files to Delete

- `transformations/02_silver/urbanicity_isochrones_valhalla.ipynb`
- `transformations/02_silver/create_mapbox_isochrones.py`
- `resources/configs/valhalla_config.json`
- `resources/init_scripts/init-valhalla.sh`
- `resources/init_scripts/init-valhalla-simple.sh`
- `notebooks/debug_valhalla_install.py`

## Key Constraints

1. **Medallion Architecture**: Maintain strict Bronze → Silver → Gold flow
2. **State-Specific**: Massachusetts only for now (but keep state filter configurable in `databricks.yml` for future expansion)
3. **Self-Contained**: No external table dependencies; all data created within pipeline (except pre-loaded LCE stores)
4. **Backward Compatible**: Design `store_config.yml` to easily swap in real sales table when available
5. **OSRM Only**: Single routing engine, 5-minute drive time standard
6. **No Competitors**: Remove all competitor-related features, tables, and visualizations
7. **App Performance**: Cache queries in Streamlit (`@st.cache_data`) for fast UX
8. **Table Naming**: Use `census_states` not `bronze_census_states`

## Success Criteria

✅ Pipeline runs end-to-end via `databricks bundle run orchestration_job`  
✅ Streamlit app loads all 3 tabs without errors  
✅ Map shows MA boundary + LCE stores + 5-min isochrones  
✅ Expansion candidates avoid cannibalization (no overlap with existing isochrones)  
✅ Network optimizer produces valid recommendations with configurable constraints  
✅ All tables use CARTO features (no custom census aggregation except POI)  
✅ No Valhalla, Mapbox, or competitor-related code remains  
✅ Sales data uses synthetic formula; config references `lce_sales_historical` for future use  

## Implementation Approach

### Phase 1: Config & Cleanup (Files & Variables)
- Create `resources/configs/store_config.yml` with sales placeholder structure
- Update `h3_features_config.yml` to reference CARTO columns
- Update `isochrone_config.yml` to remove Valhalla/Mapbox sections
- Update `databricks.yml` to remove `valhalla_cluster_id`, `mapbox_token`
- **Delete** Valhalla/Mapbox files listed above
- Update `resources/silver_job.yml` and `resources/gold_job.yml` to remove obsolete tasks

### Phase 2: Bronze Layer (Minimal Changes)
- Verify `transformations/01_bronze/census_boundaries.ipynb` creates `geo_bronze.census_states`
- Keep POI extraction pipeline as-is
- Ensure `geo_bronze.lce_locations_mass` is pre-loaded (manual upload documented)

### Phase 3: Silver Layer (OSRM Isochrones)
- Update `transformations/02_silver/create_osrm_isochrones.ipynb`:
  - Input: `geo_bronze.lce_locations_mass`
  - Output: `geo_silver.lce_isochrones_5min`
  - Drive time: 5 minutes only
- Test OSRM endpoint connectivity
- Validate polygon output quality

### Phase 4: Gold Layer (CARTO Integration)
- Create new notebook or update `create_h3_features.ipynb`:
  - Query CARTO table: `carto_spatial_features_usa_h3_res_8.carto.derived_spatialfeatures_usa_h3res8_v1_yearly_v3`
  - Filter to MA H3 cells (join with MA boundary or state filter)
  - Create `geo_gold.h3_features_carto` with mapped column names
- Update `aggregate_trade_area_features.ipynb`:
  - Input: `geo_silver.lce_isochrones_5min` + `geo_gold.h3_features_carto` + `geo_silver.osm_pois`
  - Output: `geo_gold.lce_trade_area_features`
  - Remove competitor joins
- Update `predict_seed_point_sales.ipynb`:
  - Generate synthetic sales using formula from `store_config.yml`
  - Output: `geo_gold.lce_stores_with_sales`
  - Create expansion candidates with cannibalization filtering

### Phase 5: App Refactor
- Update all SQL queries in `app/app.py`:
  - Tab 1: Query `lce_stores_with_sales`, `lce_trade_area_features`, `census_states`
  - Tab 2: Query `lce_expansion_candidates`, show current + candidates
  - Tab 3: Implement optimizer, save to `lce_expansion_final`
- Remove competitor visualizations (ValueMart, QuickShop cards)
- Update sales driver cards with CARTO-compatible features
- Test each tab independently

### Phase 6: End-to-End Testing
- Run full orchestration job: `databricks bundle run orchestration_job`
- Verify all tables created successfully
- Open Streamlit app, test all interactions
- Validate map displays correctly (MA boundary, stores, isochrones)
- Test expansion filtering and optimization
- Document any issues and iterate

### Phase 7: Documentation
- Update `README.md` with new architecture (remove Valhalla references)
- Document CARTO table integration
- Document synthetic sales formula and how to swap in real table
- Update `migration_notes.md` as complete

---

## Additional Notes

**CARTO Column Mapping Reference:**
Based on `z_scratch/CARTO_Spatial_Features__USA__H3_Res__8_.csv` schema:
- Population: `population`, `male`, `female`, age breakdowns (`female_25_to_29`, etc.)
- Income: `income_75000_to_99999`, `income_100000_to_124999`, `income_125000_to_149999`, etc.
- Education: Check for education columns in actual CARTO table
- Use `h3` column as join key with H3 cell IDs

**Synthetic Sales Formula Example:**
```python
# Pseudo-code for sales synthesis
annual_sales = (
    300000 +  # Base
    (population_density * 50) +
    (poi_count * 100) +
    (young_adults_25_34 * 30) +
    (high_income_households * 5)
)
```

**Next Steps:**
Review this comprehensive plan, confirm approach, then proceed with phased implementation. Prioritize getting the pipeline working end-to-end before perfecting the app UI.

