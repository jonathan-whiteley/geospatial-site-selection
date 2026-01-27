# Model Improvement Implementation Plan

## Executive Summary

This plan addresses the fundamental issues with the current sales prediction model and outlines a phased approach to achieve meaningful improvements. The current model produces a **negative R² (-0.64)**, meaning it performs worse than simply predicting the mean. This is primarily a **data limitation problem**, not a hyperparameter tuning problem.

### Key Issues Identified
| Issue | Impact | Solution |
|-------|--------|----------|
| Only 76 training stores | Model can't learn generalizable patterns | Expand to 575 stores (7 states) |
| Negative feature correlations | Population negatively correlated with sales | Add competition density, tract-level income |
| `state_median_income` leakage | Acts as proxy for state ID | Remove or replace with tract-level |
| Aggressive spatial CV | 13-store test set is statistically unstable | Implement LORO with larger folds |
| Overly complex model | XGBoost overfits with small data | Start with Ridge/Lasso, add complexity gradually |

---

## Phase 1: Data Expansion (High Impact)

### 1.1 Expand Training Data to 575 Stores

**Objective:** Increase training data from 76 to 575 stores using "peer states" that share Massachusetts' economic and spatial characteristics.

**Target Store Distribution:**
| State | Stores | Strategic Value |
|-------|--------|-----------------|
| Michigan (MI) | 288 | Legacy proxy - similar climate, seasonality, older infrastructure |
| Virginia (VA) | 91 | Wealth proxy - NoVa suburbs mirror Greater Boston demographics |
| New York (NY) | 73 | Density proxy - complex urban centers, high competitive pressure |
| Washington (WA) | 67 | Innovation proxy - high-tech coastal wealth, geographic barriers |
| Maryland (MD) | 39 | Commuter proxy - intense traffic patterns, high median income |
| New Jersey (NJ) | 7 | Saturation proxy - extreme density for "over-stored" market modeling |
| Massachusetts (MA) | 10 | Target state - final validation and gold standard testing |
| **TOTAL** | **575** | **Optimal for XGBoost (~14% of national footprint)** |

#### Files to Modify

**1. `transformations/03_gold/agg_h3_features_current_stores.ipynb`**

```python
# CURRENT (line ~20-30):
# Only loads NE states
state_filter = "MA,CT,NJ,MD"

# CHANGE TO:
state_filter = "MA,MI,VA,NY,WA,MD,NJ"
```

**2. `transformations/02_silver/clean_h3_features.ipynb`**

```python
# CURRENT:
target_states = ['MA', 'CT', 'NJ', 'MD']

# CHANGE TO:
target_states = ['MA', 'MI', 'VA', 'NY', 'WA', 'MD', 'NJ']
```

**3. `resources/configs/silver_config.yml` (if state filter is configured here)**

Update any state filter configurations to include the expanded state list.

**4. Data Requirements**
- Ensure `lce_locations_raw` table contains stores from all 7 states with:
  - `store_number` or `location_id`
  - `latitude`, `longitude`
  - `city`, `state`
  - `annual_sales` (actual sales data - critical!)

### 1.2 Generate H3 Features for New States

**Prerequisite:** CARTO Marketplace data must include H3 cells for MI, VA, NY, WA.

```python
# In clean_h3_features.ipynb, verify CARTO coverage:
carto_states = spark.table(carto_table).select("state").distinct().collect()
print(f"CARTO coverage: {[r.state for r in carto_states]}")

# Required: MI, VA, NY, WA must be present
# If missing, need to expand CARTO subscription or use alternative data
```

### 1.3 Generate Isochrones for New States

**File:** `transformations/02_silver/create_isochrones.ipynb`

```python
# Ensure isochrone generation covers all training states
# Current: Only generates for stores in state_filter
# Update state_filter variable to include all 7 states
```

---

## Phase 2: Feature Engineering Improvements (Medium Impact)

### 2.1 Remove Problematic Features

**Issue:** `state_median_income` is a state-level constant that acts as a proxy for state ID, causing the model to learn spurious state-level patterns.

**File:** `transformations/03_gold/predict_candidate_sales.ipynb`

```python
# REMOVE from feature list:
# 'state_median_income'  # State-level constant - remove

# KEEP location-level features only:
feature_columns = [
    'population',
    'target_demographic_total',
    'retail', 'food_drink', 'leisure', 'education',
    'healthcare', 'financial', 'tourism', 'transportation',
    'total_poi_count',
    'human_activity_index',
    # NEW features (see 2.2)
]
```

### 2.2 Add New Predictive Features

#### A. Competition Density

**File:** `transformations/03_gold/agg_h3_features_current_stores.ipynb`

```python
# Add competition density feature
# Count pizza competitors within trade area

competitors = spark.table(f"{catalog}.{silver_schema}.pois_competitors")

# For each store's trade area, count competitors inside
stores_with_competition = stores_agg.join(
    competitors.alias("comp"),
    expr("ST_Contains(stores_agg.geometry, ST_Point(comp.longitude, comp.latitude))"),
    "left"
).groupBy("store_number").agg(
    F.count("comp.poi_id").alias("competitor_count_in_trade_area")
)

# Merge back to main features
stores_agg = stores_agg.join(stores_with_competition, "store_number", "left")
stores_agg = stores_agg.fillna({"competitor_count_in_trade_area": 0})
```

#### B. Tract-Level Income (Replace State-Level)

**File:** `transformations/02_silver/clean_h3_features.ipynb`

```python
# Option 1: Use CARTO's income data at H3 level (if available)
# Check for income-related columns in CARTO data

# Option 2: Join with Census tract-level income
# Census ACS B19013 = Median Household Income by tract
census_income = spark.table(f"{catalog}.{bronze_schema}.census_tract_income")

# Spatial join: H3 cell center → Census tract → tract median income
h3_with_income = h3_features.join(
    census_income,
    expr("ST_Contains(census_income.geometry, ST_Point(h3_features.center_lon, h3_features.center_lat))"),
    "left"
).select(
    h3_features["*"],
    census_income["median_household_income"].alias("tract_median_income")
)
```

#### C. Distance-Based Features

**File:** `transformations/03_gold/agg_h3_features_current_stores.ipynb`

```python
# Distance to nearest competitor
from pyspark.sql.window import Window

# For each store, find distance to nearest pizza competitor
stores_with_nearest_competitor = stores_agg.crossJoin(
    competitors.select(
        "poi_id",
        F.col("latitude").alias("comp_lat"),
        F.col("longitude").alias("comp_lon")
    )
).withColumn(
    "distance_to_competitor",
    expr("ST_Distance(ST_Point(longitude, latitude), ST_Point(comp_lon, comp_lat))")
).groupBy("store_number").agg(
    F.min("distance_to_competitor").alias("distance_to_nearest_competitor")
)
```

#### D. Partner Store Proximity

```python
# Count partner stores within trade area (co-location opportunity)
partners = spark.table(f"{catalog}.{silver_schema}.pois_partners")

stores_with_partners = stores_agg.join(
    partners.alias("part"),
    expr("ST_Contains(stores_agg.geometry, ST_Point(part.longitude, part.latitude))"),
    "left"
).groupBy("store_number").agg(
    F.count("part.poi_id").alias("partner_count_in_trade_area")
)
```

### 2.3 Updated Feature List

```python
# Final feature set for model training
feature_columns = [
    # Demographics
    'population',
    'target_demographic_total',

    # POI counts
    'retail', 'food_drink', 'leisure', 'education',
    'healthcare', 'financial', 'tourism', 'transportation',
    'total_poi_count',

    # Activity
    'human_activity_index',

    # NEW: Competition & Partners
    'competitor_count_in_trade_area',
    'distance_to_nearest_competitor',
    'partner_count_in_trade_area',

    # NEW: Income (tract-level, not state-level)
    'tract_median_income',
]
```

---

## Phase 3: Validation Strategy Improvements (High Impact)

### 3.1 Implement Leave-One-Region-Out (LORO) Cross-Validation

**Current Problem:** Single train/test split with only 13 MA stores in test set is statistically unstable.

**Solution:** Regional fold cross-validation that ensures model learns generalizable patterns.

**File:** `transformations/03_gold/predict_candidate_sales.ipynb`

```python
# Define regional folds
REGIONAL_FOLDS = {
    'fold_1_great_lakes': {
        'train': ['VA', 'MD', 'NY', 'NJ', 'WA', 'MA'],
        'test': ['MI'],  # 288 stores
        'description': 'Test on Great Lakes region'
    },
    'fold_2_south_atlantic': {
        'train': ['MI', 'NY', 'NJ', 'WA', 'MA'],
        'test': ['VA', 'MD'],  # 130 stores
        'description': 'Test on South Atlantic region'
    },
    'fold_3_northeast_corridor': {
        'train': ['MI', 'VA', 'MD', 'WA', 'MA'],
        'test': ['NY', 'NJ'],  # 80 stores
        'description': 'Test on Northeast Corridor'
    },
    'fold_4_target_pacific': {
        'train': ['MI', 'VA', 'MD', 'NY', 'NJ'],
        'test': ['WA', 'MA'],  # 77 stores (includes target state)
        'description': 'Test on Target & Pacific'
    },
}

# Run LORO cross-validation
fold_results = []

for fold_name, fold_config in REGIONAL_FOLDS.items():
    print(f"\n{'='*60}")
    print(f"Running {fold_name}: {fold_config['description']}")
    print(f"Train states: {fold_config['train']}")
    print(f"Test states: {fold_config['test']}")

    # Split data
    train_mask = stores_df['state'].isin(fold_config['train'])
    test_mask = stores_df['state'].isin(fold_config['test'])

    X_train_fold = stores_df[train_mask][feature_columns]
    y_train_fold = stores_df[train_mask]['annual_sales']
    X_test_fold = stores_df[test_mask][feature_columns]
    y_test_fold = stores_df[test_mask]['annual_sales']

    print(f"Train size: {len(X_train_fold)}, Test size: {len(X_test_fold)}")

    # Train model
    model = xgb.XGBRegressor(**xgb_params)
    model.fit(X_train_fold, np.log1p(y_train_fold))

    # Evaluate
    y_pred_log = model.predict(X_test_fold)
    y_pred = np.expm1(y_pred_log)

    fold_rmse = np.sqrt(mean_squared_error(y_test_fold, y_pred))
    fold_r2 = r2_score(y_test_fold, y_pred)
    fold_mae = mean_absolute_error(y_test_fold, y_pred)

    fold_results.append({
        'fold': fold_name,
        'train_states': fold_config['train'],
        'test_states': fold_config['test'],
        'test_size': len(X_test_fold),
        'rmse': fold_rmse,
        'r2': fold_r2,
        'mae': fold_mae,
    })

    print(f"RMSE: ${fold_rmse:,.0f}, R²: {fold_r2:.3f}, MAE: ${fold_mae:,.0f}")

# Summary
results_df = pd.DataFrame(fold_results)
print("\n" + "="*60)
print("LORO Cross-Validation Summary:")
print(f"Mean RMSE: ${results_df['rmse'].mean():,.0f} (±${results_df['rmse'].std():,.0f})")
print(f"Mean R²: {results_df['r2'].mean():.3f} (±{results_df['r2'].std():.3f})")
print(f"Mean MAE: ${results_df['mae'].mean():,.0f}")
```

### 3.2 Final MA Validation (Guardrail)

After LORO CV, train final model on all non-MA stores and validate exclusively on MA:

```python
# Final model: Train on ALL non-MA stores, test on MA only
print("\n" + "="*60)
print("FINAL MA VALIDATION (Guardrail)")

train_final = stores_df[stores_df['state'] != 'MA']
test_final = stores_df[stores_df['state'] == 'MA']

X_train_final = train_final[feature_columns]
y_train_final = train_final['annual_sales']
X_test_final = test_final[feature_columns]
y_test_final = test_final['annual_sales']

print(f"Training on {len(X_train_final)} stores from {train_final['state'].nunique()} states")
print(f"Testing on {len(X_test_final)} MA stores")

# Train final model
final_model = xgb.XGBRegressor(**xgb_params)
final_model.fit(X_train_final, np.log1p(y_train_final))

# Evaluate on MA
y_pred_ma = np.expm1(final_model.predict(X_test_final))
ma_rmse = np.sqrt(mean_squared_error(y_test_final, y_pred_ma))
ma_r2 = r2_score(y_test_final, y_pred_ma)
ma_mae = mean_absolute_error(y_test_final, y_pred_ma)

print(f"\nMA Validation Results:")
print(f"  RMSE: ${ma_rmse:,.0f}")
print(f"  R²: {ma_r2:.3f}")
print(f"  MAE: ${ma_mae:,.0f}")

# This is the model to use for MA candidate predictions
if ma_r2 > 0:
    print("\n✓ Model ready for MA site selection")
else:
    print("\n⚠ Warning: Negative R² on MA - consider simpler model or heuristic scoring")
```

---

## Phase 4: Model Architecture Improvements (Medium Impact)

### 4.1 Establish Baselines First

Before any ML, verify simple approaches beat random:

```python
# Baseline 1: Predict the mean
mean_sales = y_train.mean()
baseline_rmse = np.sqrt(mean_squared_error(y_test, [mean_sales] * len(y_test)))
print(f"Baseline (predict mean) RMSE: ${baseline_rmse:,.0f}")

# Baseline 2: Median
median_sales = y_train.median()
median_rmse = np.sqrt(mean_squared_error(y_test, [median_sales] * len(y_test)))
print(f"Baseline (predict median) RMSE: ${median_rmse:,.0f}")

# ML model must beat these baselines to be useful
```

### 4.2 Start Simple: Ridge/Lasso Regression

With limited data, regularized linear models often outperform complex ensembles:

```python
from sklearn.linear_model import RidgeCV, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Ridge regression (handles multicollinearity)
ridge_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('ridge', RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0]))
])

ridge_pipeline.fit(X_train, np.log1p(y_train))
ridge_pred = np.expm1(ridge_pipeline.predict(X_test))
ridge_rmse = np.sqrt(mean_squared_error(y_test, ridge_pred))
ridge_r2 = r2_score(y_test, ridge_pred)

print(f"Ridge Regression - RMSE: ${ridge_rmse:,.0f}, R²: {ridge_r2:.3f}")

# Lasso for automatic feature selection
lasso_pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('lasso', LassoCV(alphas=[0.01, 0.1, 1.0, 10.0], cv=5))
])

lasso_pipeline.fit(X_train, np.log1p(y_train))
lasso_pred = np.expm1(lasso_pipeline.predict(X_test))
lasso_rmse = np.sqrt(mean_squared_error(y_test, lasso_pred))
lasso_r2 = r2_score(y_test, lasso_pred)

print(f"Lasso Regression - RMSE: ${lasso_rmse:,.0f}, R²: {lasso_r2:.3f}")

# Show Lasso-selected features (non-zero coefficients)
lasso_coefs = pd.Series(
    lasso_pipeline.named_steps['lasso'].coef_,
    index=feature_columns
)
print("\nLasso-selected features:")
print(lasso_coefs[lasso_coefs != 0].sort_values(ascending=False))
```

### 4.3 Updated XGBoost Configuration

With 575 stores, we can use slightly more complex settings:

```python
# Optimized for 575 stores (per MODEL_EXPANSION_PLAN.md)
xgb_params = {
    'n_estimators': 150,        # More trees with larger dataset
    'max_depth': 4,             # Slightly deeper (was 3)
    'min_child_weight': 10,     # Increased (was 5) - more conservative
    'learning_rate': 0.05,      # Slower (was 0.1) - prevents MI domination
    'subsample': 0.8,           # Same - train on 80% of samples per tree
    'colsample_bytree': 0.8,    # Same - use 80% of features per tree
    'reg_alpha': 0.1,           # L1 regularization
    'reg_lambda': 1.0,          # L2 regularization
    'random_state': 42,
    'n_jobs': -1,
    'early_stopping_rounds': 20,  # Stop if no improvement
}
```

### 4.4 Hyperparameter Tuning with Optuna

```python
import optuna

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 2, 6),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'min_child_weight': trial.suggest_int('min_child_weight', 5, 20),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 2.0),
        'n_estimators': 100,
        'random_state': 42,
    }

    # Use LORO CV for robust evaluation
    fold_rmses = []
    for fold_name, fold_config in REGIONAL_FOLDS.items():
        train_mask = stores_df['state'].isin(fold_config['train'])
        test_mask = stores_df['state'].isin(fold_config['test'])

        X_train_fold = stores_df[train_mask][feature_columns]
        y_train_fold = stores_df[train_mask]['annual_sales']
        X_test_fold = stores_df[test_mask][feature_columns]
        y_test_fold = stores_df[test_mask]['annual_sales']

        model = xgb.XGBRegressor(**params)
        model.fit(X_train_fold, np.log1p(y_train_fold), verbose=False)

        y_pred = np.expm1(model.predict(X_test_fold))
        fold_rmse = np.sqrt(mean_squared_error(y_test_fold, y_pred))
        fold_rmses.append(fold_rmse)

    return np.mean(fold_rmses)

# Run optimization
study = optuna.create_study(direction='minimize')
study.optimize(objective, n_trials=50, show_progress_bar=True)

print(f"Best RMSE: ${study.best_value:,.0f}")
print(f"Best params: {study.best_params}")
```

---

## Phase 5: Alternative Approaches (Fallback)

### 5.1 Heuristic Scoring (If ML Fails)

If R² remains negative even with more data, use domain-driven heuristic:

```python
def heuristic_score(df):
    """
    Simple scoring based on retail fundamentals:
    - Higher population = more customers (40%)
    - More POIs = more foot traffic (25%)
    - Fewer competitors = less competition (20%)
    - Higher activity index = more engagement (15%)
    """
    score = (
        df['population'].rank(pct=True) * 0.40 +
        df['total_poi_count'].rank(pct=True) * 0.25 +
        (1 - df['competitor_count_in_trade_area'].rank(pct=True)) * 0.20 +
        df['human_activity_index'].rank(pct=True) * 0.15
    )
    return score

# Apply to candidates
candidates['heuristic_score'] = heuristic_score(candidates)
candidates['heuristic_rank'] = candidates['heuristic_score'].rank(ascending=False)
```

**Advantages:**
- Transparent and explainable to stakeholders
- No overfitting risk
- Works with any sample size
- Easy to adjust weights based on business intuition

### 5.2 Focus on Ranking, Not Prediction

Even with poor R², the model may rank locations correctly:

```python
from scipy.stats import spearmanr

# Spearman rank correlation (more robust than R²)
rank_corr, p_value = spearmanr(y_test, y_pred)
print(f"Spearman rank correlation: {rank_corr:.3f} (p={p_value:.3f})")

# Top-quartile precision (most actionable metric)
k = max(1, len(y_test) // 4)
actual_top = set(y_test.nlargest(k).index)
predicted_top = set(pd.Series(y_pred, index=y_test.index).nlargest(k).index)
precision = len(actual_top & predicted_top) / k
print(f"Top-quartile precision: {precision:.0%}")

# If Spearman > 0.5, model is useful for ranking even if R² is poor
```

### 5.3 Ensemble with Heuristic

Combine ML predictions with heuristic for robustness:

```python
# Weighted ensemble
ml_weight = 0.6 if r2_score > 0 else 0.3  # Trust ML more if it works
heuristic_weight = 1 - ml_weight

candidates['ensemble_score'] = (
    candidates['predicted_annual_sales'].rank(pct=True) * ml_weight +
    candidates['heuristic_score'] * heuristic_weight
)

candidates['final_rank'] = candidates['ensemble_score'].rank(ascending=False)
```

---

## Phase 6: MLflow & Model Registry Integration

### 6.1 Log All Experiments

```python
import mlflow

with mlflow.start_run(run_name="model_improvement_v2"):
    # Log data expansion
    mlflow.log_param("training_states", ",".join(TRAIN_STATES))
    mlflow.log_param("training_store_count", len(X_train))
    mlflow.log_param("test_state", "MA")
    mlflow.log_param("cv_strategy", "LORO")

    # Log feature list
    mlflow.log_param("features", ",".join(feature_columns))
    mlflow.log_param("feature_count", len(feature_columns))

    # Log LORO CV results
    for fold_result in fold_results:
        mlflow.log_metric(f"rmse_{fold_result['fold']}", fold_result['rmse'])
        mlflow.log_metric(f"r2_{fold_result['fold']}", fold_result['r2'])

    mlflow.log_metric("mean_cv_rmse", results_df['rmse'].mean())
    mlflow.log_metric("mean_cv_r2", results_df['r2'].mean())

    # Log MA validation (guardrail)
    mlflow.log_metric("ma_rmse", ma_rmse)
    mlflow.log_metric("ma_r2", ma_r2)
    mlflow.log_metric("ma_mae", ma_mae)

    # Log model
    mlflow.xgboost.log_model(final_model, "model")

    # Register if performance is acceptable
    if ma_r2 > 0:
        mlflow.register_model(
            f"runs:/{mlflow.active_run().info.run_id}/model",
            f"{catalog}.{gold_schema}.sales_prediction_model_v2"
        )
```

---

## Implementation Checklist

### Phase 1: Data Expansion
- [ ] Verify LCE store data available for MI, VA, NY, WA, MD, NJ
- [ ] Verify CARTO H3 data covers all 7 states
- [ ] Update `state_filter` in `clean_h3_features.ipynb`
- [ ] Update `state_filter` in `agg_h3_features_current_stores.ipynb`
- [ ] Generate isochrones for new states
- [ ] Run full silver → gold pipeline

### Phase 2: Feature Engineering
- [ ] Remove `state_median_income` from feature list
- [ ] Add `competitor_count_in_trade_area` feature
- [ ] Add `distance_to_nearest_competitor` feature
- [ ] Add `partner_count_in_trade_area` feature
- [ ] Add tract-level income (if Census data available)
- [ ] Re-run feature aggregation notebooks

### Phase 3: Validation Strategy
- [ ] Implement LORO cross-validation
- [ ] Add MA guardrail validation
- [ ] Log all fold metrics to MLflow

### Phase 4: Model Architecture
- [ ] Establish baseline metrics (predict-mean, predict-median)
- [ ] Implement Ridge/Lasso regression
- [ ] Update XGBoost parameters for 575 stores
- [ ] Run Optuna hyperparameter tuning
- [ ] Compare all models and select best

### Phase 5: Alternative Approaches
- [ ] Implement heuristic scoring function
- [ ] Calculate Spearman rank correlation
- [ ] Calculate top-quartile precision
- [ ] Implement ensemble scoring (ML + heuristic)

### Phase 6: MLflow Integration
- [ ] Log all experiments with proper tags
- [ ] Register best model to Unity Catalog
- [ ] Document model performance in model card

---

## Expected Outcomes

### Realistic Targets (575 Stores)

| Metric | Current (76 stores) | Target (575 stores) | Notes |
|--------|---------------------|---------------------|-------|
| Test R² | -0.64 | 0.20 - 0.40 | Positive R² would be significant win |
| Test RMSE | $260K | $150K - $200K | 25-40% improvement |
| Spearman correlation | Unknown | 0.50 - 0.70 | Useful for ranking |
| Top-quartile precision | ~25% (random) | 50% - 70% | Better than random |

### What's Achievable vs Not Achievable

**Achievable:**
- Positive R² (model better than mean)
- Useful ranking of candidates (Spearman > 0.5)
- Reasonable prediction intervals (±$100K)
- Generalizable patterns across peer states

**Not Achievable (even with more data):**
- Precise dollar predictions (±$25K)
- R² > 0.7 without store-specific data (traffic, tenure, format)
- Perfect generalization to states with different economics

---

## Notebook Run Order

After implementing changes, run notebooks in this order:

```
1. clean_h3_features.ipynb           # Silver: Expand state coverage
2. create_isochrones.ipynb           # Silver: Generate isochrones for new stores
3. agg_h3_features_current_stores.ipynb  # Gold: Aggregate features for training
4. agg_h3_features_candidates.ipynb  # Gold: Aggregate features for candidates
5. predict_candidate_sales.ipynb     # Gold: Train model with LORO CV
6. viz_layer_prep.ipynb              # Gold: Prepare visualization tables
```

---

## Summary

The path forward is **more data first, then model sophistication**. The key insight from the diagnosis is that 76 stores is fundamentally insufficient for ML-based sales prediction. By expanding to 575 stores from peer states and implementing proper spatial cross-validation, we can build a model that generalizes to Massachusetts expansion candidates.

If ML still struggles after data expansion, the heuristic scoring approach provides a transparent, explainable alternative that doesn't require large training sets.

**The goal is not perfect prediction—it's identifying the best candidate locations for further investigation.**

---

*Document created: 2026-01-26*
*Based on MODEL_EXPANSION_PLAN.md and MODEL_IMPROVEMENT_RECOMMENDATIONS.md*
