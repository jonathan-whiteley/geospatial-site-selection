# Pipeline Dependencies & Execution Order

This document outlines the table dependencies and execution order for the geospatial retail site selection pipeline.

---

## Prerequisites - Manual Data Upload Required ⚠️

Before running any jobs, ensure these tables exist in the **bronze schema** (`geo_bronze`):

| Table Name | Description | Required Columns |
|------------|-------------|------------------|
| `competitor_locations` | Competitor store locations | `latitude`, `longitude`, `store_type` |
| `rmc_retail_locations_grocery` | RMC retail store locations | `latitude`, `longitude`, `store_number` (optional) |

These tables are typically manually uploaded from CSV files or created via separate ingestion processes.

---

## Job Execution Order

### ✅ Manual Execution (Recommended for Development)

```bash
# 1. Bronze: Ingest census and OSM data
databricks bundle run bronze_census_ingestion

# 2. Silver: Clean, transform, create features and isochrones
databricks bundle run silver_poi_processing

# 3. Gold: Aggregate trade area features
databricks bundle run gold_feature_engineering
```

### ✅ Orchestrated Execution (Recommended for Production)

```bash
# Runs all jobs in sequence
databricks bundle run site_selection_pipeline
```

---

## Table Dependencies by Layer

### Bronze Layer

**Job:** `bronze_census_ingestion`

**Creates:**
- `census_demographics` - ACS 5-year demographic data at block group level
- `census_blockgroups` - Census block group boundaries
- `census_states` - State boundaries
- `osm_downloads` - Downloaded OSM PBF files metadata
- `osm_pois_raw` - Raw POIs extracted from OSM

**Requires:**
- External APIs: Census Bureau API, Geofabrik OSM downloads

---

### Silver Layer

**Job:** `silver_poi_processing`

**Creates:**
- `osm_pois` - Cleaned and categorized POIs
- `h3_features_gold` - H3 grid cells with aggregated features (demographics, POIs, distances, urbanicity)
- `rmc_urbanicity_based_isochrones` - Drive-time isochrones for RMC locations

**Requires from Bronze:**
- ✅ `census_states`
- ✅ `census_blockgroups`
- ✅ `census_demographics`
- ✅ `osm_pois_raw`
- ⚠️ `competitor_locations` (manual upload)
- ⚠️ `rmc_retail_locations_grocery` (manual upload)

**Tasks:**
1. `clean_pois` - Cleans raw OSM POIs
2. `create_h3_features` - Creates H3 grid with aggregated features
3. `create_osrm_isochrones` - Generates drive-time isochrones

---

### Gold Layer

**Job:** `gold_feature_engineering`

**Creates:**
- `rmc_urbanicity_based_isochrones_enriched` - Trade area features aggregated by store
- `seed_points_expansion_top_25` - Predicted sales for expansion locations

**Requires from Silver:**
- ✅ `h3_features_gold`
- ✅ `rmc_urbanicity_based_isochrones`
- ✅ `osm_pois`

**Tasks:**
1. `aggregate_trade_area_features` - Aggregates H3 features to trade area level
2. `predict_seed_point_sales` - Predicts sales for potential new locations

---

## Troubleshooting

### Error: Table Not Found

If you see errors like:
```
[TABLE_OR_VIEW_NOT_FOUND] The table or view `jdub_demo_aws`.`geo_bronze`.`competitor_locations` cannot be found
```

**Solution:** Ensure the prerequisite tables are uploaded to the bronze schema.

### Error: h3_features_gold Not Found (Gold Job)

If the gold job fails looking for `h3_features_gold`:

**Solution:** Run the silver job first: `databricks bundle run silver_poi_processing`

---

## Data Flow Diagram

```
Bronze Schema (geo_bronze)
├── Census API → census_demographics
├── Census API → census_blockgroups
├── Census API → census_states
├── Geofabrik → osm_downloads
├── OSM Extract → osm_pois_raw
├── [MANUAL] → competitor_locations ⚠️
└── [MANUAL] → rmc_retail_locations_grocery ⚠️

Silver Schema (geo_silver)
├── osm_pois_raw → clean_pois → osm_pois
├── census_* + osm_pois + competitors + rmc → create_h3_features → h3_features_gold
└── rmc_retail_locations_grocery + h3_features_gold → create_osrm_isochrones → rmc_urbanicity_based_isochrones

Gold Schema (geo_gold)
├── rmc_urbanicity_based_isochrones + h3_features_gold → aggregate_trade_area_features → rmc_urbanicity_based_isochrones_enriched
└── h3_features_gold → predict_seed_point_sales → seed_points_expansion_top_25
```

---

## Table Schemas

### competitor_locations (Bronze - Manual Upload)

```sql
CREATE TABLE jdub_demo_aws.geo_bronze.competitor_locations (
  latitude DOUBLE,
  longitude DOUBLE,
  store_type STRING,
  -- Optional additional columns
  store_name STRING,
  address STRING,
  city STRING,
  state STRING
)
```

### rmc_retail_locations_grocery (Bronze - Manual Upload)

```sql
CREATE TABLE jdub_demo_aws.geo_bronze.rmc_retail_locations_grocery (
  latitude DOUBLE,
  longitude DOUBLE,
  store_number STRING,
  -- Optional additional columns
  store_type STRING,
  city STRING,
  state STRING
)
```

---

## Notes

- The `create_h3_features` notebook is technically in the `02_silver` folder but writes to the **gold schema** (`h3_features_gold`) because it's considered a foundational feature table used by both silver and gold layers.
- All jobs use **Databricks Serverless** compute for cost optimization.
- Job timeouts: Bronze (2 hours), Silver (3 hours), Gold (3 hours).
