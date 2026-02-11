# Pipeline Troubleshooting & EDA Notebook Plan

**Date:** 2025-02-11
**Location:** `/explorations/pipeline_troubleshooting_eda.ipynb`
**Purpose:** Standalone notebook to step through the Gold layer transformation pipeline, verify aggregation logic, and explore alternative modeling approaches.

## Problem Statement

The model/aggregation steps may have issues. This notebook reproduces the Gold layer logic step-by-step with full visibility into intermediate DataFrames to pinpoint where things go wrong. It also explores alternative modeling approaches (normalization, no log transform, multiple model types).

## Notebook Sections

### Section 0: Setup & Parameters
- All `dbutils.widgets` with sensible defaults (catalog=`ioc_sandbox`, schemas=`geo_bronze`/`geo_silver`/`geo_gold`)
- All package imports (pyspark, pandas, numpy, matplotlib, seaborn, xgboost, sklearn, mlflow, folium, h3)
- No dependency on the pipeline job — fully self-contained

### Section 1: Load Raw Stores & Sales
- Read `{catalog}.{bronze_schema}.current_stores_raw`
- Display store count by state, sales distribution (histogram), summary stats
- Verify `annual_sales` column has real values (not generated)
- Flag any nulls or outliers

### Section 2: Load Pre-Computed Trade Areas
- Read `{catalog}.{silver_schema}.isochrones_lce` (existing store isochrones)
- Read `{catalog}.{silver_schema}.candidate_isochrones` (candidate isochrones)
- Display counts, area_sqkm distribution, sample geometries
- No recomputation — these are expensive Valhalla API calls

### Section 3: Load H3 Features
- Read `{catalog}.{silver_schema}.h3_features_clean` (CARTO H3 data)
- Display cell count by state, feature distributions
- Show available columns and sample data

### Section 4: Enrich Trade Areas (KEY TROUBLESHOOTING SECTION)

**4a. H3 Polyfill**
- Use `h3_polyfillash3string(ST_AsBinary(geometry), 8)` + `explode` to index trade areas
- Display: H3 cell counts per store (min/max/avg)
- Verify: Are polyfill counts reasonable? (urban ~50-200 cells, rural ~500+ cells)

**4b. Inner Join with H3 Features**
- Join polyfilled H3 cells with `h3_features_clean` on `h3_cell_id`
- Display: Match rate (how many polyfill cells actually have CARTO data?)
- Flag: Any stores with 0 matched cells = data gap

**4c. Aggregate by Store**
- Apply aggregation rules:
  - **SUM**: population, target_demographic_total, all 8 POI categories, total_poi_count
  - **AVG**: human_activity_index
  - **COUNT**: h3_cell_count
  - **FIRST**: urbanity, geometry
- Display: Full aggregated DataFrame with all features per store
- Separate step: Show aggregated values alongside sales for visual inspection

**4d. Folium Map Visualization**
- For 3-5 sample stores, render:
  - Isochrone polygon (orange)
  - H3 cells within polyfill (blue hexagons)
  - Store marker (red)
- Purpose: Visual verification that polyfill is working correctly

**4e. Additional Features**
- `area_sqkm` — already on isochrone table, verify it's carried through
- `competitor_count`, `partner_count` — from POI tables via H3 spatial join
- Show how these are computed and display distribution

### Section 5: Verify Current Pipeline Output
- Compare our step-by-step aggregation against `current_stores_features_agg`
- Side-by-side comparison for a few stores
- Flag any discrepancies

### Section 6: Prediction Model Exploration

**6a. Feature Correlations**
- Correlation matrix heatmap for all features vs annual_sales
- Identify multicollinearity issues

**6b. Normalize Features by Population**
- Create per-capita versions: `retail_per_capita = retail / population`, etc.
- Re-run correlations to see if normalized features correlate better with sales

**6c. Model Comparison (No Log Transform)**
- Explore whether raw sales (not log-transformed) works better for some models
- For XGBoost: try `objective='reg:squarederror'` on raw sales (XGBoost doesn't need 0-1 normalization — it's tree-based)
- Consider MinMax scaling discussion but note trees don't need it

**6d. Multiple Models**
- **Linear Regression**: Baseline, interpretable coefficients
- **XGBoost**: Current pipeline model, with and without log transform
- **Random Forest**: Alternative ensemble, compare with XGBoost
- All with stratified 5-fold CV (stratified by state)

**6e. MLflow Logging**
- Use a SEPARATE experiment: `geospatial-retail-standalone`
- Log each model variant as a nested run
- Log metrics: RMSE, MAE, R², MAPE
- Log feature importance plots
- Easy comparison in MLflow UI

### Section 7: Candidate Predictions (MA)
- Apply best model to `candidates_features_agg`
- Show prediction distribution
- Compare with pipeline's `candidates_finalized` output

## Key Tables Referenced

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `current_stores_raw` | Store locations + annual_sales |
| Silver | `isochrones_lce` | 5-min drive-time polygons (existing stores) |
| Silver | `candidate_isochrones` | 5-min drive-time polygons (MA candidates) |
| Silver | `h3_features_clean` | CARTO H3 res-8 features (7 states) |
| Silver | `pois_competitors` | Pizza competitor locations |
| Silver | `pois_partners` | Partner store locations |
| Gold | `current_stores_features_agg` | Pipeline output (for comparison) |
| Gold | `candidates_features_agg` | Pipeline output (for comparison) |
| Gold | `candidates_finalized` | Pipeline predictions (for comparison) |

## What This Notebook Does NOT Include
- Partner/competitor POI details for app frontend (viz_* tables)
- Genie space creation
- Optimization grid computation
- Isochrone generation (uses pre-computed)
- H3 feature engineering from CARTO (uses pre-computed)
