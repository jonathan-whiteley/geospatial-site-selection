# Model Improvement Plan - Phased Approach

## Current State (Baseline)

| Metric | Value |
|--------|-------|
| Training stores | 42 (CT:2, NJ:20, MD:20) |
| Test stores | 9 (MA hold-out) |
| Features | 5 (food_drink, human_activity_index, population, target_demographic_total, transportation) |
| Target | log1p(annual_sales) |
| Linear Regression RMSE | $807,227 (R² = -1.135) |
| XGBoost RMSE | $664,653 (R² = -0.447) |

Both models perform **worse than predicting the mean**. The core problem is insufficient training data (42 stores) and a geographic split where the training states don't adequately represent MA patterns.

---

## Phase 1: Expand Training Data (Highest Impact)

### 1.1 New Store Distribution (~570 stores)

| State | Stores | Role |
|-------|--------|------|
| MI | 284 | Largest training contributor - Midwest anchor |
| VA | 90 | East coast suburb/commuter patterns |
| NY | 73 | Dense urban/suburban metro mix |
| WA | 67 | West coast high-income markets |
| MD | 39 | Mid-Atlantic, current training state |
| MA | 10 | **Hold-out for final validation** |
| NJ | 7 | Dense corridor markets |
| **Total** | **570** | |

### 1.2 Files to Modify

**A. `transformations/02_silver/clean_h3_features.ipynb`** - Expand CARTO H3 coverage

The `state_filter` widget currently defaults to `"MA,CT,NJ,MD"`. Update to include all training states:

```python
# Cell 2 - change state_filter default
dbutils.widgets.text("state_filter", "MA,MI,VA,NY,WA,MD,NJ")
```

This drives the spatial filter that pulls CARTO H3 cells for those states. Verify that the CARTO Marketplace table (`carto_spatial_features_usa_h3_res_8`) has coverage for MI, VA, NY, WA. If not, you'll need to expand the CARTO subscription.

**B. `transformations/01_bronze/ingest_current_stores.ipynb`** - Load all 570 stores

The input `lce_locations_table` parameter must point to a table containing stores from all 7 states with actual `AvgSalesPerYear` data. The notebook already handles any state - it just reads what's in the input table. Ensure the upload contains:
- `location_id`, `latitude`, `longitude`, `city`, `state`
- `AvgSalesPerYear` (actual sales - **critical**, do not use generated dummy data)

The notebook's `Supported States` comment says "MA, CT, NJ, MD" but the code doesn't actually filter by state - it ingests everything in the input table. No code change needed, just supply the expanded data.

**C. `transformations/02_silver/create_isochrones.ipynb`** - Generate isochrones for new stores

Isochrones are generated for all stores in `current_stores_ne`. Since the bronze table will now contain stores from all 7 states, isochrones will automatically be generated for the new stores. No code change needed if the notebook processes all stores in the table.

**D. `transformations/03_gold/agg_h3_features_current_stores.ipynb`** - Aggregate features for all stores

This notebook loads from `isochrones_lce` and joins to `h3_features_clean`. As long as both silver tables cover the 7 states, it will aggregate correctly. No code change needed.

**E. `transformations/03_gold/predict_candidate_sales.ipynb`** - Update train/test split

```python
# Cell 2 - update spatial CV config
TRAIN_STATES = ['MI', 'VA', 'NY', 'WA', 'MD', 'NJ']  # ~560 stores
TEST_STATE = 'MA'  # 10 stores - hold-out target market
```

### 1.3 Pipeline Run Order

```
1. ingest_current_stores.ipynb        (bronze - load 570 stores)
2. clean_h3_features.ipynb            (silver - H3 features for 7 states)
3. create_isochrones.ipynb            (silver - 5-min isochrones for all stores)
4. agg_h3_features_current_stores.ipynb (gold - aggregate features per store)
5. predict_candidate_sales.ipynb      (gold - train & predict)
6. viz_layer_prep.ipynb               (gold - refresh viz tables)
```

### 1.4 Expected Impact

Going from 42 to 560 training stores is the single biggest improvement. With more data:
- XGBoost can learn actual patterns instead of memorizing noise
- Feature selection via RFE becomes more reliable
- The model has enough examples to distinguish signal from noise

**Realistic target:** R² of 0.15-0.35 on MA hold-out (positive R² = meaningful improvement)

---

## Phase 2: Spatial Cross-Validation Strategy

### 2.1 Problem with Current Split

The current approach (train on CT/NJ/MD, test on MA) has two issues:
1. **CT only has 2 stores** - barely contributes to training
2. **9 MA test stores is too small** - a single outlier store can swing R² from +0.3 to -0.5

With 570 stores, MA still only has 10 stores for testing - small, but the training set is dramatically better.

### 2.2 Recommended Approach: Two-Stage Validation

**Stage 1: Leave-One-Region-Out (LORO) Cross-Validation** - for model development and hyperparameter tuning

Use LORO CV across geographic folds to get robust performance estimates. This tells you if the model generalizes across regions in general:

```python
REGIONAL_FOLDS = {
    'fold_great_lakes': {
        'test': ['MI'],           # 284 stores
        'description': 'Hold out Great Lakes'
    },
    'fold_south_atlantic': {
        'test': ['VA', 'MD'],     # 129 stores
        'description': 'Hold out Mid-Atlantic'
    },
    'fold_northeast': {
        'test': ['NY', 'NJ'],     # 80 stores
        'description': 'Hold out Northeast Corridor'
    },
    'fold_pacific': {
        'test': ['WA'],           # 67 stores
        'description': 'Hold out Pacific Northwest'
    },
}
# For each fold, train = all states NOT in test (excluding MA)
# MA is NEVER in training during LORO - reserved for final validation
```

Report mean and std of RMSE/R² across folds. This gives you a confidence interval on model quality.

**Stage 2: Final MA Validation (Guardrail)** - for production decision

After selecting the best model via LORO, train on ALL non-MA stores (560 stores) and evaluate on the 10 MA stores. This is the number that matters for the expansion use case:

```python
# Final model
X_train_final = all_stores[all_stores['state'] != 'MA'][features]
y_train_final = all_stores[all_stores['state'] != 'MA']['annual_sales']
X_test_final  = all_stores[all_stores['state'] == 'MA'][features]
y_test_final  = all_stores[all_stores['state'] == 'MA']['annual_sales']
```

### 2.3 Implementation in predict_candidate_sales.ipynb

Keep the notebook simple by adding LORO as an **evaluation section** (not replacing the current flow):

1. Load all 570 stores
2. Run LORO CV (4 folds) - log metrics to MLflow
3. Train final model on all non-MA stores
4. Evaluate on MA (guardrail)
5. If MA R² > 0: use ML predictions for candidates
6. If MA R² <= 0: fall back to heuristic ranking (Phase 3 fallback)

### 2.4 Why Not Random K-Fold?

Random k-fold would leak spatial information. Stores in the same city or metro area share local economic patterns. If you randomly split, some NJ training stores might be 5 miles from NJ test stores - the model sees nearly the same market in both sets. Geographic hold-out prevents this optimistic bias.

---

## Phase 3: Feature Recommendations

### 3.1 Feature Aggregation - Confirmed

**Current aggregation in `agg_h3_features_current_stores.ipynb`:**

| Feature | Aggregation | Validation |
|---------|-------------|------------|
| population | SUM | Confirmed: counts, SUM correct |
| target_demographic_total | SUM | Confirmed: counts, SUM correct |
| retail, food_drink, etc. (8 POI cats) | SUM | Confirmed: these are POI counts, SUM correct |
| total_poi_count | SUM | Redundant with 8 individual categories - **drop from feature set** |
| human_activity_index | AVG | Confirmed: CARTO 0-100 normalized score (country-level), AVG correct |
| h3_cell_count | COUNT | Already computed - **add as feature** (captures trade area size) |

No changes needed to the aggregation logic itself. Changes are in the model notebook's feature list only.

### 3.2 Recommended Feature Changes (Phase 3A - Quick Wins)

These require no new data sources, just changes in the model notebook:

**A. Add `h3_cell_count` as a feature**

Already computed in the aggregation. It captures trade area size/density - a proxy for urbanity. Stores in dense areas have smaller isochrones with fewer H3 cells; rural stores have large isochrones with many cells.

```python
# In predict_candidate_sales.ipynb, add to feature_columns:
'h3_cell_count'
```

**B. Drop `total_poi_count`, use individual POI categories**

`total_poi_count` is the literal sum of the 8 individual POI categories - perfect multicollinearity. Drop it and let RFE choose from the granular categories instead:

```python
feature_columns = [
    'population', 'target_demographic_total',
    'retail', 'food_drink', 'leisure', 'education',
    'healthcare', 'financial', 'tourism', 'transportation',
    'human_activity_index',
    'h3_cell_count',
]
```

**C. Remove `state_median_income` from the model**

It's a state-level constant (only 4 unique values currently, 7 with expansion). The model can learn "MI stores sell more" without understanding why. This is information leakage that won't help predict for new MA locations. It's already hardcoded in `STATE_MEDIAN_INCOME` dict - just don't add it to the feature set.

**D. Keep all 14 features going into RFE, let it select top 7-8**

With 560 training stores, you can support more features than with 42. Increase RFE target from 5 to 7-8:

```python
n_features_to_select = min(8, len(feature_columns) - 1)
```

### 3.3 Recommended Feature Changes (Phase 3B - New Features)

These require modifying the gold aggregation notebooks:

**A. Competitor density within trade area**

Count pizza competitors (Domino's, Pizza Hut, Papa John's) inside each store's 5-min isochrone. You already have `pois_competitors` in silver.

```python
# In agg_h3_features_current_stores.ipynb, after feature aggregation:
competitors = spark.table(f"{catalog}.{silver_schema}.pois_competitors")

# Spatial join: count competitors inside each store's trade area polygon
stores_with_comp = ta_features_agg.alias("s").join(
    competitors.alias("c"),
    expr("ST_Contains(s.geometry, ST_Point(c.longitude, c.latitude))"),
    "left"
).groupBy("s.store_number").agg(
    F.countDistinct("c.location_id").alias("competitor_count")
)
```

**B. Partner density within trade area**

Same approach using `pois_partners` - count Walmart, 7-Eleven, etc. inside each isochrone.

**C. Distance to nearest existing store (for candidates)**

This is already in the whitespace generation. For training stores, compute pairwise distances:

```python
# Nearest-neighbor distance for each training store
# Captures market isolation vs. clustering effects
```

### 3.4 Feature Priority Order

| Priority | Feature | Effort | Expected Impact |
|----------|---------|--------|-----------------|
| 1 | Drop `state_median_income` | None (just remove) | Removes leakage |
| 2 | Add `h3_cell_count` | None (already computed) | Captures trade area size |
| 3 | Drop `total_poi_count` from candidate set when using individual categories | None (just remove) | Reduces multicollinearity |
| 4 | Increase RFE from 5 to 7-8 features | Trivial | Better with more training data |
| 5 | Add `competitor_count` | Moderate (modify agg notebook) | Highly predictive - more competition = price pressure |
| 6 | Add `partner_count` | Moderate (modify agg notebook) | Co-location signal |

---

## Phase Summary & Implementation Order

### Phase 1 (Do First): Expand Data
- Upload 570-store dataset with actual sales
- Update `state_filter` in `clean_h3_features.ipynb`
- Update `TRAIN_STATES` in `predict_candidate_sales.ipynb`
- Re-run full pipeline
- **Expected: R² goes from -0.45 to 0.15-0.35**

### Phase 2 (Do With Phase 1): Spatial CV
- Add LORO CV section to model notebook (4 geographic folds)
- Keep MA as final guardrail validation
- Log fold metrics to MLflow
- **Expected: Reliable performance estimates with confidence intervals**

### Phase 3A (Quick Wins): Feature Cleanup
- Remove `state_median_income`
- Add `h3_cell_count`
- Drop `total_poi_count` from RFE candidate set
- Increase RFE target to 7-8 features
- **Expected: Modest improvement, cleaner model**

### Phase 3B (Follow-up): New Features
- Add competitor/partner counts (requires modifying aggregation notebook)
- Re-run pipeline and compare to Phase 3A results
- **Expected: Meaningful improvement if competition density is predictive**

---

## What NOT to Change Yet

To keep things simple in the first iteration:

- **Don't add Optuna hyperparameter tuning** - get the data right first, default XGBoost params are fine for 560 stores
- **Don't switch to Ridge/Lasso** - XGBoost with regularization is appropriate at 560 stores
- **Don't add tract-level Census income** - requires a new data source and spatial join; defer to a later phase
- **Don't change the isochrone methodology** - 5-min drive time is a reasonable trade area definition
- **Don't modify the aggregation method** - confirmed SUM for counts, AVG for human_activity_index (0-100 score) is correct

---

*Created: 2026-02-06*
*Based on current model results (R² = -0.447) and prompt_2_6.md requirements*
