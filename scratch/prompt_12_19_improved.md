# Site Selection Optimized Medallion Refactoring Plan

## Phase 1: Bronze Consolidation

- **Census**: Merge `census_boundaries.ipynb` and `census_demographics.ipynb` into `01_bronze/census.ipynb`.
- **POI**: Merge `osm_download.ipynb` and `extract_pois.ipynb` into `01_bronze/poi_ingestion.ipynb`.
    -  Improve efficiency of extract pois if possible

## Phase 2: Silver Feature Engineering

- **POI Cleaning**: Update `02_silver/clean_pois.ipynb` to split POIs into `pois_convenience` and `pois_competitors`.
    - Use these queries 
    - --Convenience
SELECT * FROM `jdub_demo_aws`.`geo_silver`.`clean_pois`
WHERE `name` IN ('7-Eleven', 'Speedway')
ORDER BY `name`, 'address';

--Competitors
SELECT * FROM `jdub_demo_aws`.`geo_silver`.`clean_pois`
WHERE `name` IN ('Pizza Hut', "Domino's", "Papa John's")
ORDER BY `name`, `address`;

- **Isochrones**: Update `02_silver/create_osrm_isochrones.ipynb` to output `isochrones_lce` and `isochrones_convenience` (geo_silver schema)
    - Use pois_convenience for isochrones_convenience
    - Use lce_locations_mass for isochrones_lce
- **Existing Metrics**: Refactor `aggregate_trade_area_features.ipynb` into `02_silver/aggregate_existing_lce_features.ipynb` (outputs `existing_stores_h3`).
- **H3 Candidates**: Refactor `create_h3_features.ipynb` into `02_silver/candidate_features_h3.ipynb` ,
    - - Filter Carto table to Massachusetts, get relevant demographic, POI features
- use k-rings to aggregate by trade area, show count by urbanity
- output - h3 level , aggregate surrounding trade area's features 
- filter to top 25%
    - aggregate demographics to trade areas using **Variable K-rings** (urbanity = Rural: 8, Urban: 3, City: 2).
    - additional features
        - total_poi
        - target_demographic (Young adults 20-34 (fast, cheap pizza buyers)
    - site_trade_areas = {
'High_density_urban': 2,      # City: 0.87 mile radius
'Very_High_density_urban': 2, # City: 0.87 mile radius
'Medium_density_urban': 3,    # Urban: 1.45 mile radius
'Low_density_urban': 3,       # Urban: 1.45 mile radius
'Rural': 8                    # Rural: 4.0 mile radius
}

## Phase 3: Gold Logic & Visualization

- **Prediction**: Refactor `predict_seed_point_sales.ipynb` to `03_gold/expansion_prediction.ipynb` (implements spatial exclusion). Sales prediction with target demographic weighting as placeholder for real regression model
    - - sanity check against existing stores metrics (aggregate features at h3 level using isochrones_lce)
- Placeholder for Model, uses Heuristic formula to predict sales for now
- Apply Business Constraints on minimum Predicted sales, population, demographics
- Exclude existing store trade areas (H3 cells covered by existing stores trade areas - raw_isochrones_lce)
- Return top candidates, ranked by predicted sales
- **Viz Prep**: Create `03_gold/viz_layer_prep.ipynb`.
    - **Inputs**: Candidates, existing stores, competitors, convenience isochrones, and **census_states**.
    - **Logic**: 
        - Generate `viz_h3_grid` by covering the MA boundary with H3-8 cells.
        - Calculate normalized scores (0-1) and percentile benchmarks.
    - **Outputs**: `viz_expansion_candidates`, `viz_existing_stores`, `viz_competitors`, `viz_convenience`, `viz_h3_grid`.

## Phase 4: Orchestration

- Update Databricks Asset Bundle configs (`databricks.yml`, job YMLs) to reflect the new notebook structure and dependencies.

### Finalized Site Selection App Architecture Table

Finalized Site Selection App Architecture
Layer	Notebook	Input Table(s)	Output Table(s)	Schema
Bronze	01_bronze/census.ipynb	Census API, pygris	census_blockgroups, census_states, census_demographics	geo_bronze
Bronze	01_bronze/poi_ingestion.ipynb	OSM Geofabrik (PBF)	raw_pois	geo_bronze
Silver	02_silver/clean_pois.ipynb	raw_pois	clean_pois, pois_convenience, pois_competitors	geo_silver
Silver	02_silver/osrm_isochrones.ipynb	lce_locations_mass, pois_convenience	isochrones_lce, isochrones_convenience	geo_silver
Silver	02_silver/aggregate_existing_lce_features.ipynb	isochrones_lce, h3_features_carto	existing_stores_h3	geo_silver
Silver	02_silver/candidate_features_h3.ipynb	CARTO Marketplace, census_states, lce_locations_mass	expansion_candidates_h3	geo_silver
Gold	03_gold/expansion_prediction.ipynb	expansion_candidates_h3, isochrones_lce, existing_stores_h3	expansion_candidates_h3_enhanced	geo_gold
Gold	03_gold/viz_layer_prep.ipynb	expansion_candidates_h3_enhanced, existing_stores_h3, pois_competitors, isochrones_convenience, census_states	viz_expansion_candidates, viz_existing_stores, viz_competitors, viz_convenience, viz_h3_grid	geo_gold
