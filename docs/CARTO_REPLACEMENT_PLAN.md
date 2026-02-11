# CARTO Replacement Plan: Census + OSM H3 Feature Engineering

## Objective

Remove the CARTO Marketplace dependency (`carto_spatial_features_usa_h3_res_8`) by building H3-level demographic and POI features from first-party sources (US Census API + OpenStreetMap PBF extracts). The pipeline remains serverless, the `silver.h3_features_clean` output contract is preserved, and downstream gold/app layers require minimal changes.

---

## Current State: Where CARTO Lives

**Single point of dependency:** `transformations/02_silver/clean_h3_features.ipynb`

This notebook reads the CARTO Marketplace table and extracts:

| Column Group | CARTO Columns | Used By |
|---|---|---|
| Demographics | `population`, `male_20_to_24`, `female_20_to_24`, `male_25_to_29`, `female_25_to_29`, `male_30_to_34`, `female_30_to_34` | Gold agg (SUM), whitespace filtering, ML model |
| POI counts | `retail`, `food_drink`, `leisure`, `education`, `healthcare`, `financial`, `tourism`, `transportation` | Gold agg (SUM), ML model |
| Activity | `human_activity_index` (0-100 CARTO proprietary score) | Gold agg (AVG), ML model |
| Urbanity | `urbanity` (CARTO categorical: Very_High_density_urban, etc.) | Gold agg (FIRST), whitespace filtering, viz |

**Derived columns** (computed in the silver notebook, not from CARTO directly):
- `target_demographic_total` = sum of 20-34 age bins
- `total_poi_count` = sum of 8 POI categories
- `urbanity_category` = mapped from CARTO `urbanity` to urban/suburban/rural

---

## Design Principles

1. **Preserve the `h3_features_clean` contract** - same column names, same semantics, same H3 resolution 8. Gold and app layers should not need schema changes.
2. **Use Databricks spatial SQL natively** - `h3_polyfillash3string`, `ST_Intersects`, `ST_Contains`, `ST_Area`, `ST_Intersection` for efficient serverless execution.
3. **Area-weighted aggregation for demographics** - properly apportion Census block group counts to H3 cells based on geometric overlap (not just point-in-polygon).
4. **Single PBF parse, two outputs** — combine branded POI extraction (partners/competitors) and general POI categorization (retail, food_drink, etc.) into one notebook. Each PBF is downloaded once and parsed with a single handler that captures both brand matches and tag-based categories. Outputs two tables: `raw_pois` (branded) and `osm_pois_raw` (general categories).
5. **Deterministic replacements for CARTO-proprietary metrics** - `human_activity_index` and `urbanity` get reproducible, open-source derivations.

---

## High-Level Flow (Post-Refactor)

```
Bronze Layer (new/modified):
  ingest_census.ipynb ─── census_blockgroups (multi-state) + census_demographics (multi-state)
  ingest_pois.ipynb ────── raw_pois (branded) + osm_pois_raw (general categories) [REFACTORED]
    Single PBF download+parse per state, two output tables

Silver Layer (refactored):
  create_h3_features.ipynb ── h3_features_clean (same output schema) [REPLACES clean_h3_features.ipynb]
    Reads: census_blockgroups + census_demographics + osm_pois_raw + census_states
    Writes: h3_features_clean (same columns, same H3 res 8)

Gold/App Layers: [UNCHANGED - consume h3_features_clean as before]
```

---

## Phase 1: Bronze — Multi-State Census Ingestion

**File:** `transformations/01_bronze/ingest_census.ipynb`
**Status:** Modify existing

### Current Limitation
Census ingestion takes a single `state_fips` parameter and downloads block groups + demographics for that one state only. The pipeline trains on 7 states (MA, MI, VA, NY, WA, MD, NJ) but currently relies on CARTO for H3 features across all of them.

### Changes Required

1. **Accept `state_filter` instead of `state_fips`** — parse the comma-separated list (e.g., "MA,MI,VA,NY,WA,MD,NJ") and loop over all states.

2. **Download block groups for all training states** — pygris `block_groups(state=fips)` called per state, concatenated into a single `census_blockgroups` table. Use `MERGE INTO` or `overwrite` with partition by state to make re-runs idempotent.

3. **Fetch demographics for all training states** — Census API call per state FIPS. Concatenate results into `census_demographics`.

4. **Add missing age bins to `census_variables.yml`** — the current config has `male_18_to_24` / `female_18_to_24` but the CARTO replacement needs the 20-24, 25-29, 30-34 bins specifically. Add:
   ```yaml
   target_demographic:
     B01001_008E: male_20_to_24
     B01001_009E: male_25_to_29
     B01001_010E: male_30_to_34
     B01001_032E: female_20_to_24
     B01001_033E: female_25_to_29
     B01001_034E: female_30_to_34
   ```

5. **FIPS lookup helper** — add a mapping dict (`{"MA": "25", "MI": "26", ...}`) so the notebook can iterate over `state_filter` abbreviations without requiring separate FIPS inputs.

### Config Changes
- `databricks.yml`: Remove `state_fips` variable (or keep as deprecated). Pass `state_filter` to bronze census task.
- `resources/bronze_job.yml`: Update `ingest_census` task params to pass `state_filter` instead of `state_fips`.
- `resources/configs/census_variables.yml`: Add 20-34 age bin variables.

### Output Tables (unchanged names)
- `bronze.census_blockgroups` — block group geometries for all training states
- `bronze.census_states` — all US states (already present, no change)
- `bronze.census_demographics` — ACS demographics for all training states

---

## Phase 2: Bronze — Combined POI Ingestion (Branded + General Categories)

**File:** `transformations/01_bronze/ingest_pois.ipynb` **[REFACTORED]**

### Current State
The existing notebook downloads a single-state PBF (expansion_state) and parses only branded POIs by name matching. We refactor it to also extract general POI categories across all training states — one PBF download+parse per state, two output tables.

### Combined Handler Design

A single osmium handler captures both outputs in one pass per PBF:

```python
class CombinedPOIHandler(osmium.SimpleHandler):
    def __init__(self, brand_patterns, category_mappings):
        super().__init__()
        self.branded_pois = []      # → raw_pois (partners/competitors)
        self.general_pois = []      # → osm_pois_raw (category counts)
        self.brand_patterns = [b.lower() for b in brand_patterns]
        self.category_mappings = category_mappings  # tag→category dict

    def node(self, n):
        if not n.location.valid():
            return
        tags = dict(n.tags)
        coords = {"lat": n.location.lat, "lon": n.location.lon}

        # General category classification (by OSM tag)
        category = self._classify_category(tags)
        if category:
            self.general_pois.append({
                "osm_id": str(n.id), "osm_type": "node",
                "latitude": coords["lat"], "longitude": coords["lon"],
                "poi_category": category
            })

        # Branded name match (same as current handler)
        if self._matches_brand(tags):
            self.branded_pois.append({
                "osm_id": str(n.id), "osm_type": "node",
                "latitude": coords["lat"], "longitude": coords["lon"],
                "tags": tags
            })
```

### General POI Category Mappings

Defined in `resources/configs/osm_poi_categories.yml`:

| Category | OSM Tags |
|---|---|
| `retail` | shop=* (supermarket, convenience, clothes, etc.) |
| `food_drink` | amenity=restaurant, cafe, fast_food, bar, pub, food_court |
| `leisure` | leisure=park, playground, sports_centre, fitness_centre; amenity=cinema, theatre |
| `education` | amenity=school, university, college, library, kindergarten |
| `healthcare` | amenity=hospital, clinic, pharmacy, dentist, doctors |
| `financial` | amenity=bank, atm; shop=money_lender |
| `tourism` | tourism=hotel, museum, attraction, viewpoint, gallery |
| `transportation` | amenity=bus_station, fuel; railway=station; public_transport=* |

### Multi-State Iteration

The notebook now accepts `state_filter` (all training states) in addition to `expansion_state`:

```
For each state in state_filter:
  1. Download PBF from Geofabrik to UC Volume (skip if cached)
  2. Parse with CombinedPOIHandler
  3. Accumulate general_pois (all states) and branded_pois (all states)

Write general_pois → bronze.osm_pois_raw
Write branded_pois (filtered to expansion_state) → bronze.raw_pois
```

Branded POIs are captured from all states (essentially free since we're parsing anyway), but `raw_pois` is still filtered to `expansion_state` since downstream `clean_pois` only needs expansion-state brands for candidate mapping. The general POIs for all states are needed for H3 feature engineering.

### Output Tables

**`bronze.osm_pois_raw`** (NEW — general categories for all training states):
```
osm_id STRING
osm_type STRING           -- node | way
latitude DOUBLE
longitude DOUBLE
poi_category STRING       -- retail | food_drink | leisure | ...
state STRING              -- state abbreviation
ingestion_timestamp TIMESTAMP
```

**`bronze.raw_pois`** (EXISTING — branded partners/competitors, expansion_state only):
Same schema as current. No change to downstream `clean_pois.ipynb`.

### Scale Note
The 7-state PBF downloads total ~3-5 GB. Parsing with osmium is CPU-bound but fast (~30s per state). This fits comfortably in a serverless task with a 30-min timeout. Each state is parsed sequentially in the same notebook run.

### Config Changes
- `resources/configs/osm_poi_categories.yml` — new file defining OSM tag → category mappings
- `resources/bronze_job.yml` — update `ingest_pois` task to also pass `state_filter`
- `databricks.yml` — no new variables needed (reuses `state_filter` and existing volume)

---

## Phase 3: Silver — H3 Feature Engineering (Core Refactor)

**File:** `transformations/02_silver/create_h3_features.ipynb` **[NEW — replaces `clean_h3_features.ipynb`]**

This is the heart of the refactor. It replaces the CARTO read with first-party feature engineering.

### Algorithm: Three-Step H3 Enrichment

#### Step 1: Generate H3 Grid for Target States

```sql
-- Generate H3 cells covering all target states at resolution 8
-- Uses hierarchical approach: coarse cover (res 5) → explode to res 8
SELECT DISTINCT h3_cell_id, state_abbr
FROM (
  SELECT state_abbr,
         EXPLODE(h3_tochildren(coarse_h3, 8)) AS h3_cell_id
  FROM (
    SELECT state_abbr,
           EXPLODE(h3_coverash3string(ST_AsBinary(geometry), 5)) AS coarse_h3
    FROM {bronze}.census_states
    WHERE state_abbr IN ('MA', 'MI', 'VA', 'NY', 'WA', 'MD', 'NJ')
  )
)
```

This produces the base H3 grid (~15-20M cells for 7 states at res 8). Cache this as it's joined twice.

#### Step 2: Area-Weighted Demographic Aggregation

For each H3 cell, intersect with Census block groups and apportion counts by overlap area:

```sql
-- 1. Spatial intersection: H3 cells × block groups
WITH h3_bg_intersect AS (
  SELECT
    h3.h3_cell_id,
    bg.geoid,
    -- Ratio of intersection area to total block group area
    ST_Area(ST_Intersection(h3.h3_geometry, bg.geometry))
      / ST_Area(bg.geometry) AS intersection_ratio
  FROM h3_base h3
  JOIN {bronze}.census_blockgroups bg
    ON ST_Intersects(h3.h3_geometry, bg.geometry)
),

-- 2. Join with demographics and weight by intersection ratio
weighted_demo AS (
  SELECT
    i.h3_cell_id,
    d.total_population * i.intersection_ratio AS weighted_population,
    d.male_20_to_24 * i.intersection_ratio AS weighted_male_20_to_24,
    d.female_20_to_24 * i.intersection_ratio AS weighted_female_20_to_24,
    -- ... all demographic columns ...
  FROM h3_bg_intersect i
  JOIN {bronze}.census_demographics d
    ON i.geoid = CONCAT(d.state, d.county, d.tract, d.block_group)
)

-- 3. Aggregate to H3 cell level
SELECT
  h3_cell_id,
  CAST(SUM(weighted_population) AS LONG) AS population,
  CAST(SUM(weighted_male_20_to_24) AS LONG) AS male_20_to_24,
  CAST(SUM(weighted_female_20_to_24) AS LONG) AS female_20_to_24,
  -- ... etc ...
FROM weighted_demo
GROUP BY h3_cell_id
```

**Why area-weighted?** Census block groups don't align with H3 hexagons. A simple point-in-polygon (assigning a block group to one H3 cell) would lose population at boundaries. Area-weighting distributes counts proportionally to geometric overlap. This is the standard approach used by the reference implementation.

**Performance note:** `ST_Intersection` is expensive. To make this efficient on serverless:
- Join only block groups that actually intersect H3 cells (`ST_Intersects` predicate)
- Process state-by-state if memory is a concern (7 independent jobs)
- Cache the H3 base grid with geometry (`h3_boundaryaswkt`)

#### Step 3: POI Count Aggregation

Spatial containment join between H3 cells and individual POIs:

```sql
SELECT
  h3.h3_cell_id,
  COALESCE(SUM(CASE WHEN p.poi_category = 'retail' THEN 1 ELSE 0 END), 0) AS retail,
  COALESCE(SUM(CASE WHEN p.poi_category = 'food_drink' THEN 1 ELSE 0 END), 0) AS food_drink,
  COALESCE(SUM(CASE WHEN p.poi_category = 'leisure' THEN 1 ELSE 0 END), 0) AS leisure,
  COALESCE(SUM(CASE WHEN p.poi_category = 'education' THEN 1 ELSE 0 END), 0) AS education,
  COALESCE(SUM(CASE WHEN p.poi_category = 'healthcare' THEN 1 ELSE 0 END), 0) AS healthcare,
  COALESCE(SUM(CASE WHEN p.poi_category = 'financial' THEN 1 ELSE 0 END), 0) AS financial,
  COALESCE(SUM(CASE WHEN p.poi_category = 'tourism' THEN 1 ELSE 0 END), 0) AS tourism,
  COALESCE(SUM(CASE WHEN p.poi_category = 'transportation' THEN 1 ELSE 0 END), 0) AS transportation
FROM h3_base h3
LEFT JOIN {bronze}.osm_pois_raw p
  ON ST_Contains(h3.h3_geometry, ST_Point(p.longitude, p.latitude))
GROUP BY h3.h3_cell_id
```

**Optimization:** Instead of expensive `ST_Contains` with geometry, use H3 indexing for POI-to-cell assignment:

```sql
-- Much faster: convert POI lat/lon directly to H3 cell
SELECT
  h3_longlatash3string(longitude, latitude, 8) AS h3_cell_id,
  poi_category,
  COUNT(*) AS poi_count
FROM {bronze}.osm_pois_raw
GROUP BY 1, 2
```

Then pivot to get one column per category. This avoids the expensive geometry join entirely.

### Derived Features (same as current)

```python
# target_demographic_total: sum of 20-34 age bins
h3_features = h3_features.withColumn(
    "target_demographic_total",
    coalesce(col("male_20_to_24"), lit(0)) + coalesce(col("female_20_to_24"), lit(0)) +
    coalesce(col("male_25_to_29"), lit(0)) + coalesce(col("female_25_to_29"), lit(0)) +
    coalesce(col("male_30_to_34"), lit(0)) + coalesce(col("female_30_to_34"), lit(0))
)

# total_poi_count: sum of all 8 categories
h3_features = h3_features.withColumn(
    "total_poi_count",
    col("retail") + col("food_drink") + col("leisure") + col("education") +
    col("healthcare") + col("financial") + col("tourism") + col("transportation")
)
```

### Replacing CARTO-Proprietary Metrics

#### `urbanity` → POI-density-based urbanity scoring

CARTO's `urbanity` field uses proprietary classification. We replace it with a deterministic, reproducible approach based on POI density per H3 cell:

```python
# Compute POI density score using min-max normalization + decile ranking
urbanity_base = h3_features.withColumn(
    "poi_density_norm",
    (col("total_poi_count") - F.min("total_poi_count").over(Window.partitionBy())) /
    (F.max("total_poi_count").over(Window.partitionBy()) - F.min("total_poi_count").over(Window.partitionBy()))
)

# Decile-based urbanity (ntile across all cells)
urbanity_scored = urbanity_base.withColumn(
    "urbanity_decile", F.ntile(10).over(Window.orderBy("poi_density_norm"))
).withColumn(
    "urbanity",
    F.when(col("urbanity_decile") >= 8, "High_density_urban")
     .when(col("urbanity_decile") >= 5, "Medium_density_urban")
     .when(col("urbanity_decile") >= 3, "Low_density_urban")
     .otherwise("rural")
).withColumn(
    "urbanity_category",
    F.when(col("urbanity").isin("High_density_urban"), "urban")
     .when(col("urbanity").isin("Medium_density_urban", "Low_density_urban"), "suburban")
     .otherwise("rural")
)
```

This preserves the same `urbanity` column values that downstream code maps to `urbanity_category`. The exact thresholds can be tuned, but the decile-based approach matches the reference implementation.

#### `human_activity_index` → Composite activity score

CARTO's `human_activity_index` is a proprietary 0-100 normalized metric capturing "human activity" from cell phone mobility data. We cannot replicate cell-phone data, but we can create a deterministic proxy:

```python
# Composite score: weighted combination of POI density + population density
# Normalized to 0-100 range to match CARTO's scale
pop_norm = (col("population") - F.min("population").over(w)) / (F.max("population").over(w) - F.min("population").over(w))
poi_norm = (col("total_poi_count") - F.min("total_poi_count").over(w)) / (F.max("total_poi_count").over(w) - F.min("total_poi_count").over(w))

h3_features = h3_features.withColumn(
    "human_activity_index",
    F.round((0.5 * poi_norm + 0.5 * pop_norm) * 100, 2)
)
```

This gives a 0-100 score that correlates with the intuition behind CARTO's index (more people + more POIs = more activity). The exact weights (50/50) can be adjusted.

**ML model impact:** Since `human_activity_index` is derived from `population` and POI counts (which are already features), it adds some collinearity. XGBoost's regularization handles this, but we should monitor feature importance after the switch. If it becomes redundant, it can be dropped from the model without affecting the gold/viz layers (which only display it).

### Output Table: `silver.h3_features_clean`

**Schema (preserved from current):**
```
h3_cell_id STRING         -- H3 resolution 8 index
state_abbr STRING         -- State abbreviation
population LONG           -- Area-weighted population count
male_20_to_24 LONG        -- Area-weighted age bin
female_20_to_24 LONG
male_25_to_29 LONG
female_25_to_29 LONG
male_30_to_34 LONG
female_30_to_34 LONG
retail LONG               -- POI count in H3 cell
food_drink LONG
leisure LONG
education LONG
healthcare LONG
financial LONG
tourism LONG
transportation LONG
urbanity STRING           -- Derived urbanity label
human_activity_index DOUBLE -- Derived activity score (0-100)
target_demographic_total LONG -- Sum of 20-34 age bins
total_poi_count LONG      -- Sum of 8 POI categories
urbanity_category STRING  -- urban | suburban | rural
kring_size INT            -- K-ring size for trade area enrichment
processing_timestamp TIMESTAMP
```

**Column-by-column CARTO parity:**

| Column | CARTO Source | Census+OSM Replacement | Semantic Change? |
|---|---|---|---|
| `population` | CARTO pre-aggregated | Census area-weighted to H3 | No (same metric, different source) |
| `male/female_20-34` | CARTO pre-aggregated | Census area-weighted to H3 | No |
| 8 POI categories | CARTO pre-aggregated | OSM tag-based counts | Minor: OSM may differ in absolute counts from CARTO's proprietary POI DB; relative ranking and distribution should be comparable |
| `urbanity` | CARTO proprietary classification | Decile-based on POI density | Yes: labels stay the same, but classification logic changes from proprietary to deterministic. Distribution may shift slightly |
| `human_activity_index` | CARTO cell-phone mobility-based | Composite of population + POI density (0-100) | Yes: metric fundamentally changes from mobility to density proxy. Still directionally correct |

### Config Changes
- `resources/silver_job.yml`: Replace `clean_h3_features` task with `create_h3_features` task; remove `carto_table` parameter; add dependency on new bronze OSM task
- `databricks.yml`: Remove `carto_table` variable

---

## Phase 4: Job DAG Updates

### Bronze Job (`resources/bronze_job.yml`)

```yaml
tasks:
  - task_key: "ingest_current_stores"     # [UNCHANGED]
  - task_key: "ingest_census"             # [MODIFIED: state_filter instead of state_fips]
      base_parameters:
        state_filter: "${var.state_filter}"   # was: state_fips
  - task_key: "ingest_pois"               # [MODIFIED: now also produces osm_pois_raw]
      base_parameters:
        catalog: "${var.catalog}"
        bronze_schema: "${var.bronze_schema}"
        config_path: "${workspace.file_path}/resources/configs/poi_config.yml"
        expansion_state: "${var.expansion_state}"
        state_filter: "${var.state_filter}"    # NEW param for general POI categories
        osm_categories_config: "${workspace.file_path}/resources/configs/osm_poi_categories.yml"
```

All three bronze tasks run in parallel (no inter-dependencies).

### Silver Job (`resources/silver_job.yml`)

```yaml
tasks:
  - task_key: "clean_pois"                   # [UNCHANGED]
  - task_key: "create_h3_features"           # [REPLACES clean_h3_features]
      notebook_task:
        notebook_path: ../transformations/02_silver/create_h3_features.ipynb
        base_parameters:
          catalog: "${var.catalog}"
          bronze_schema: "${var.bronze_schema}"
          silver_schema: "${var.silver_schema}"
          state_filter: "${var.state_filter}"
          # No more carto_table parameter
      environment_key: "Serverless"
      timeout_seconds: 3600                  # Increased: area-weighted agg is heavier than CARTO read
  - task_key: "create_isochrones_lce"        # [UNCHANGED]
  - task_key: "create_isochrones_partners"   # [UNCHANGED]
  - task_key: "create_whitespace_locations"  # [UNCHANGED: still depends on create_h3_features]
      depends_on:
        - task_key: "create_h3_features"
  - task_key: "create_isochrones_candidate"  # [UNCHANGED]
```

### Gold Job (`resources/gold_job.yml`)
**No changes.** Gold notebooks read `silver.h3_features_clean` which retains its schema.

### Orchestration Job
**No changes.** It triggers bronze → silver → gold in sequence.

---

## Phase 5: `databricks.yml` Variable Cleanup

### Remove
```yaml
# carto_table:
#   description: "CARTO Marketplace H3 features table"
#   default: "carto_spatial_features_usa_h3_res_8.carto...."
```

### Deprecate (optional, keep for backward compat)
```yaml
# state_fips: kept but no longer used by census ingestion (state_filter replaces it)
```

### No New Variables Needed
- `state_filter` already exists and covers all training states
- `expansion_state` already exists for branded POI/candidate targeting
- OSM volume path uses existing `catalog`/`bronze_schema` for `osm_data/` volume

---

## Phase 6: Downstream Impact Assessment

### Gold Aggregation Notebooks — NO CHANGES NEEDED
- `agg_h3_features_current_stores.ipynb`: Reads `h3_features_clean` columns by name. Schema is preserved. Works as-is.
- `agg_h3_features_candidates.ipynb`: Same as above. Works as-is.

### ML Model (`predict_candidate_sales.ipynb`) — MONITORING REQUIRED
- **Feature columns are identical**: `population`, `target_demographic_total`, 8 POI categories, `human_activity_index`, `h3_cell_count`, `area_sqkm`, `competitor_count`, `partner_count`.
- **Risk:** Absolute values may shift (Census area-weighted population vs CARTO's aggregation; OSM POI counts vs CARTO's proprietary POI DB). This could change model coefficients and prediction distributions.
- **Action:** After running the Census+OSM pipeline, compare:
  1. Feature distributions (histograms, quantiles) between CARTO-era and Census+OSM-era `h3_features_clean`
  2. Model CV metrics (RMSE, R2) — expect minor shifts but similar overall performance
  3. Top-N candidate ranking stability (Kendall's tau or rank correlation)
- If R2 or ranking stability degrade significantly, retune hyperparameters.

### Whitespace Locations (`create_whitespace_locations.ipynb`) — NO CHANGES NEEDED
- Reads `h3_features_clean` columns: `total_poi_count`, `population`, `urbanity`, `state_abbr`, `h3_cell_id`
- All preserved in new schema. Works as-is.

### Viz Layer (`viz_layer_prep.ipynb`) — NO CHANGES NEEDED
- Reads gold `current_stores_features_agg` and `candidates_finalized`
- These tables are populated by gold notebooks that read from `h3_features_clean`
- Chain of preserved schemas means no viz changes needed

### React App (`data_service.py`) — NO CHANGES NEEDED
- Queries gold `viz_*` tables
- Column names consumed: `population`, `poi_count`/`total_poi_count`, `predicted_annual_sales`, `fulfillment_strategy`, etc.
- All originate from gold tables whose schemas are unchanged

### Genie Space — NO CHANGES NEEDED
- Reads `genie_existing_stores` and `genie_expansion_candidates`
- Both derive from gold viz tables — unchanged

---

## Implementation Order

### Step 1: Config updates
1. Add 20-34 age bin variables to `census_variables.yml`
2. Create `resources/configs/osm_poi_categories.yml`
3. Update `databricks.yml` (remove `carto_table`, optionally deprecate `state_fips`)

### Step 2: Bronze — Census multi-state
1. Refactor `ingest_census.ipynb` to accept `state_filter` and loop over states
2. Update `bronze_job.yml` task params
3. Deploy and validate: confirm block groups + demographics for all 7 states

### Step 3: Bronze — Combined POI ingestion
1. Refactor `ingest_pois.ipynb` to accept `state_filter`, download all training-state PBFs, and parse with combined handler (branded + general categories)
2. Update `bronze_job.yml` task params
3. Deploy and validate: confirm `raw_pois` unchanged for expansion_state; confirm `osm_pois_raw` has POI counts by category by state

### Step 4: Silver — H3 feature engineering
1. Create `create_h3_features.ipynb` with area-weighted demographics + H3 POI counts + derived metrics
2. Replace `clean_h3_features` in `silver_job.yml`
3. Deploy and validate: compare `h3_features_clean` schema and distributions to CARTO baseline

### Step 5: Validation gate
1. Run full pipeline (bronze → silver → gold)
2. Compare gold `current_stores_features_agg` and `candidates_features_agg` distributions
3. Check ML model CV metrics
4. Verify app loads correctly with new data

### Step 6: Cleanup
1. Delete `clean_h3_features.ipynb` (replaced by `create_h3_features.ipynb`)
2. Remove CARTO references from comments/docs
3. Remove `carto_table` from `databricks.yml`

---

## Risk Mitigations

| Risk | Mitigation |
|---|---|
| Census area-weighted population differs from CARTO | Compare distributions before committing. CARTO likely used similar Census data internally, so correlation should be high |
| OSM POI counts differ from CARTO's proprietary POI DB | CARTO's POI data likely includes non-OSM sources. OSM undercounts in rural areas. Monitor retail/food_drink specifically since those have highest feature importance |
| `human_activity_index` replacement loses signal | Current model R2 is already negative — this feature's marginal contribution is limited. If needed, drop it and rely on raw POI + population features |
| `urbanity` distribution shift affects whitespace candidate generation | Whitespace uses percentile-based filtering (top 25%), so absolute values don't matter — only relative ranking. Should be stable |
| Multi-state PBF download adds 10+ min to bronze job | PBF files are cached in UC Volume. First run is slow; subsequent runs skip download. Acceptable tradeoff |
| `ST_Intersection` for area-weighted agg is slow on serverless | Process state-by-state (7 independent spatial joins, each manageable). Use `h3_polyfillash3string` for H3 grid generation and H3 functions for POI assignment to avoid geometry joins where possible |

---

## Estimated Effort

| Phase | Effort | Notes |
|---|---|---|
| Config updates | 1 hour | YAML edits |
| Bronze census multi-state | 2-3 hours | Loop logic, FIPS mapping, test all 7 states |
| Bronze combined POI ingestion | 3-4 hours | Refactor handler, tag classification, multi-state loop, test |
| Silver H3 feature engineering | 4-6 hours | Core refactor, area-weighted agg, derived metrics, validation |
| Integration testing | 2-3 hours | Full pipeline run, distribution comparison, app smoke test |
| Cleanup | 1 hour | Remove CARTO refs, delete old notebook |
| **Total** | **~14-18 hours** | |
