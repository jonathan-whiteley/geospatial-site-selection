# H3 Features Migration to CARTO Marketplace

## Summary

The `create_h3_features.ipynb` notebook has been **completely refactored** from a complex custom aggregation pipeline to a simple CARTO marketplace integration.

### Changes

- **Old Approach** (33 cells): Custom aggregation of Census block groups, competitor locations, urbanicity scoring, complex spatial joins
- **New Approach** (19 cells, 42% reduction): Direct query of CARTO pre-aggregated features

### What Was Removed

1. **Census Block Group Aggregation** - CARTO already has demographics at H3-8
2. **Competitor Location Tracking** - Removed per project requirements (no competitor analysis for LCE)
3. **Urbanicity Score Calculation** - CARTO provides population density and urbanicity features
4. **Custom Distance Calculations to Competitors** - Only LCE store distances needed now
5. **Folium Visualization Cells** - Removed debugging visualizations

### What Was Kept

1. **H3 Grid Generation** - Still need to identify MA H3 cells
2. **POI Aggregation** - Custom OSM POI counts still added (not in CARTO)
3. **LCE Store Distance** - Calculate distance to nearest Little Caesars location

## New Workflow

### Step 1: Generate MA H3 Grid
- Use hierarchical approach (res 5 → res 8) for memory efficiency
- Filter to Massachusetts boundary

### Step 2: Load CARTO Features
- Query: `carto_spatial_features_usa_h3_res_8.carto.derived_spatialfeatures_usa_h3res8_v1_yearly_v3`
- Filter to MA H3 cells
- **Pre-aggregated demographics included:**
  - Population by age/gender (e.g., `male_18_to_24`, `female_25_to_29`)
  - Income brackets (e.g., `income_75000_to_99999`, `income_100000_to_124999`)
  - Education levels (e.g., `edu_bachelors`, `edu_graduate_professional`)
  - Housing stats, employment, commute patterns, etc.

### Step 3: Add POI Counts
- Query `osm_pois` from silver schema
- Aggregate by H3 cell and category
- Add `total_poi_count` column

### Step 4: Add LCE Store Distances
- Load `lce_locations_mass` from bronze
- Calculate distance from each H3 cell center to nearest LCE store
- Add `distance_to_nearest_lce_miles` column

### Step 5: Write to Gold
- Output table: `geo_gold.h3_features_carto`
- Combines: CARTO demographics + POI counts + LCE distances

## Benefits

1. **Faster Execution**: No complex spatial joins with census block groups
2. **Simpler Code**: Direct table query vs. multi-stage aggregation
3. **Better Maintainability**: CARTO handles demographic updates
4. **Cleaner Data**: Professional-grade CARTO feature engineering
5. **LCE-Focused**: Removed all competitor-related logic per requirements

## Files

- **New Notebook**: `transformations/02_silver/create_h3_features.ipynb`
- **Old Backup**: `transformations/02_silver/create_h3_features_COMPLEX_OLD.ipynb`
- **Another Backup**: `transformations/02_silver/create_h3_features_OLD_BACKUP.ipynb`

## CARTO Schema Reference

See `scratch/CARTO_Spatial_Features__USA__H3_Res__8_.csv` for full column list.

Key columns used in downstream notebooks:
- `population`
- `male_18_to_24`, `female_18_to_24`, `male_25_to_29`, `female_25_to_29`, `male_30_to_34`, `female_30_to_34`
- `income_75000_to_99999`, `income_100000_to_124999`, `income_125000_to_149999`, `income_150000_to_199999`, `income_200000_or_more`
- `edu_bachelors`, `edu_graduate_professional`

## Next Steps

This simplified H3 features notebook is now ready to be integrated into the silver layer workflow. The downstream gold layer notebooks (`aggregate_trade_area_features.ipynb`, `predict_seed_point_sales.ipynb`) have already been updated to reference CARTO column names.

