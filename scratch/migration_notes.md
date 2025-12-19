# Migration: RMC to LCE Location Table

## Overview
This document tracks the changes needed to migrate from `rmc_retail_locations_grocery` to `lce_locations_mass` as the primary store location table.

## Status
**NOT APPLIED** - Changes documented but reverted. Apply when ready.

---

## Changes Required

### 1. databricks.yml
**Line 104:**
```yaml
# Before:
isochrone_input_table:
  description: "Full table name for isochrone input"
  default: "jdub_demo_aws.geo_bronze.rmc_retail_locations_grocery"

# After:
isochrone_input_table:
  description: "Full table name for isochrone input"
  default: "jdub_demo_aws.geo_bronze.lce_locations_mass"
```

**Line 107:**
```yaml
# Before:
isochrone_output_table_name:
  description: "Output table name"
  default: "rmc_urbanicity_based_isochrones"

# After:
isochrone_output_table_name:
  description: "Output table name"
  default: "lce_urbanicity_based_isochrones"
```

---

### 2. resources/configs/isochrone_config.yml
**Line 30:**
```yaml
# Before:
input_tables:
  lce: "jdub_demo_aws.geo_bronze.rmc_retail_locations_grocery"
  competitors: "jdub_demo_aws.geo_bronze.competitor_locations"

# After:
input_tables:
  lce: "jdub_demo_aws.geo_bronze.lce_locations_mass"
  competitors: "jdub_demo_aws.geo_bronze.competitor_locations"
```

**Line 56:**
```yaml
# Before:
output_table: "rmc_urbanicity_based_isochrones"

# After:
output_table: "lce_urbanicity_based_isochrones"
```

---

### 3. resources/silver_job.yml
**Task key (Line 51):**
```yaml
# Before:
- task_key: "create_rmc_isochrones_urbanicity"

# After:
- task_key: "create_lce_isochrones_urbanicity"
```

**Parameters (Lines 59-60):**
```yaml
# Before:
input_table: "rmc_retail_locations_grocery"
output_table: "rmc_urbanicity_based_isochrones"

# After:
input_table: "lce_locations_mass"
output_table: "lce_urbanicity_based_isochrones"
```

---

### 4. resources/gold_job.yml
**Task key (Line 48):**
```yaml
# Before:
- task_key: "aggregate_rmc_trade_area_features"

# After:
- task_key: "aggregate_lce_trade_area_features"
```

**Parameters (Lines 58-59):**
```yaml
# Before:
trade_area_table: "${var.catalog}.${var.silver_schema}.rmc_urbanicity_based_isochrones"
output_table_override: "rmc_urbanicity_based_isochrones_enriched"

# After:
trade_area_table: "${var.catalog}.${var.silver_schema}.lce_urbanicity_based_isochrones"
output_table_override: "lce_urbanicity_based_isochrones_enriched"
```

---

### 5. transformations/02_silver/create_h3_features.ipynb
**Cell with distance calculations:**
```python
# Before:
rmc_df = spark.table(f"{catalog}.{bronze_schema}.rmc_retail_locations_grocery") \
    .select(
        F.col("latitude"),
        F.col("longitude"),
        F.expr("ST_Point(longitude, latitude, 4326)").alias("rmc_point")
    )

rmc_distance_features = h3_rmc_distances.groupBy("h3_cell_id") \
    .agg(F.min("distance_miles").alias("distance_to_nearest_rmc_miles"))

distance_features = rmc_distance_features.join(comp_distance_pivot, "h3_cell_id", "left")

# After:
lce_df = spark.table(f"{catalog}.{bronze_schema}.lce_locations_mass") \
    .select(
        F.col("latitude"),
        F.col("longitude"),
        F.expr("ST_Point(longitude, latitude, 4326)").alias("lce_point")
    )

lce_distance_features = h3_lce_distances.groupBy("h3_cell_id") \
    .agg(F.min("distance_miles").alias("distance_to_nearest_lce_miles"))

distance_features = lce_distance_features.join(comp_distance_pivot, "h3_cell_id", "left")
```

---

### 6. transformations/02_silver/create_osrm_isochrones.ipynb
**Cell 2 - Widget defaults:**
```python
# Before:
dbutils.widgets.text("input_table", "rmc_retail_locations_grocery", "Input Locations")
dbutils.widgets.text("output_table", "rmc_urbanicity_based_isochrones", "Output Table")

# After:
dbutils.widgets.text("input_table", "lce_locations_mass", "Input Locations")
dbutils.widgets.text("output_table", "lce_urbanicity_based_isochrones", "Output Table")
```

---

### 7. transformations/02_silver/create_mapbox_isochrones.py
**Line 26-27:**
```python
# Before:
dbutils.widgets.text("input_table", "rmc_retail_locations_grocery", "Input Locations Table")
dbutils.widgets.text("output_table", "rmc_urbanicity_based_isochrones", "Output Table")

# After:
dbutils.widgets.text("input_table", "lce_locations_mass", "Input Locations Table")
dbutils.widgets.text("output_table", "lce_urbanicity_based_isochrones", "Output Table")
```

---

### 8. transformations/02_silver/urbanicity_isochrones_valhalla.ipynb
**Cell 5 - Config fallback:**
```python
# Before:
locations_table = config.get('isochrone', {}).get('input_tables', {}).get('lce',
    f"{catalog}.{bronze_schema}.rmc_retail_locations_grocery")

# After:
locations_table = config.get('isochrone', {}).get('input_tables', {}).get('lce',
    f"{catalog}.{bronze_schema}.lce_locations_mass")
```

---

### 9. transformations/03_gold/aggregate_trade_area_features.ipynb
**Cell 1 - Default table:**
```python
# Before:
else:
    trade_area_table = f"{catalog}.{silver_schema}.rmc_urbanicity_based_isochrones"
    default_output = "rmc_urbanicity_based_isochrones_enriched"

# After:
else:
    trade_area_table = f"{catalog}.{silver_schema}.lce_urbanicity_based_isochrones"
    default_output = "lce_urbanicity_based_isochrones_enriched"
```

---

## Application Instructions

When ready to apply these changes:

1. Run a find-replace across the codebase:
   - `rmc_retail_locations_grocery` → `lce_locations_mass`
   - `rmc_urbanicity_based_isochrones` → `lce_urbanicity_based_isochrones`
   - `distance_to_nearest_rmc_miles` → `distance_to_nearest_lce_miles`
   - Task names: `aggregate_rmc_trade_area_features` → `aggregate_lce_trade_area_features`
   - Task names: `create_rmc_isochrones_urbanicity` → `create_lce_isochrones_urbanicity`

2. Update the gold schema tables accordingly
3. Test the full pipeline end-to-end

---

## Notes
- The app/app.py file also has references to RMC that may need updating
- Exploration notebooks may have hardcoded references
- Consider if historical data needs migration or if this is a clean cutover
