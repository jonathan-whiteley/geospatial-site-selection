# Model Fixes - 2/6/2026

## Current State
- **Training**: MI, VA, NY, WA, MD, NJ (~536 stores)
- **Test (hold-out)**: MA (10 stores)
- **LORO CV**: 4 geographic folds within training states
- **Result**: LORO mean R² = -0.269, MA hold-out R² = -0.141 (LR) / -0.283 (XGB)

## Fix 1: Train on ALL Stores (Including MA) with Stratified K-Fold CV

### Why
- 10 MA test stores is too few for a reliable R² estimate (a single outlier store flips the sign)
- Holding out MA wastes the only data we have for the target market
- Stratified k-fold gives ~109 test stores per fold (11x more than current MA hold-out)

### Proposed Split
| | Current | Proposed |
|---|---|---|
| **Strategy** | Spatial hold-out (MA) | Stratified 5-fold CV |
| **Train size** | ~536 stores | ~437 per fold (5-fold) |
| **Test size** | 10 stores (MA only) | ~109 per fold (all states) |
| **Folds** | 1 fixed split | 5 rotations |
| **States in test** | MA only | All 7 states (stratified) |
| **MA in training** | Never | 4 out of 5 folds |

### What Changes
- Remove `TRAIN_STATES` / `TEST_STATE` constants
- Replace spatial hold-out with `StratifiedKFold(n_splits=5)` stratified by state
- Keep LORO as a secondary diagnostic (logged to MLflow, not used for model selection)
- Train final production model on ALL ~546 stores

### Impact on Evaluation
- R² evaluated on ~109 stores per fold instead of 10 → much more stable
- Mean R² across 5 folds gives confidence interval
- If R² is still negative with this setup, the features genuinely lack signal

## Fix 2: Use All 14 Features (Skip RFE)

### Why
- With ~546 stores and regularized XGBoost (L1 + L2), 14 features is well within capacity
- RFE may drop the new `competitor_count` / `partner_count` features before they can prove useful
- XGBoost's built-in regularization handles feature selection naturally

### What Changes
- Remove RFE cell entirely (or keep as optional diagnostic)
- Use all 14 features directly: population, target_demographic_total, retail, food_drink, leisure, education, healthcare, financial, tourism, transportation, competitor_count, partner_count, human_activity_index, h3_cell_count

## Fix 3: Fix `area_sqkm` Calculation in Isochrone Notebook

### Problem
`ST_Area(geometry) / 1000000` on WGS84 (EPSG:4326) geometry returns **square degrees**, not square meters. A 5-min drive-time polygon is ~0.003 sq degrees → dividing by 1M gives ~0, so `area_sqkm` is effectively always 0.

### Fix
Project to an equal-area CRS before computing area:
```python
.withColumn("area_sqkm", expr("ST_Area(ST_Transform(geometry, 'EPSG:4326', 'EPSG:5070')) / 1000000"))
```
EPSG:5070 = NAD83/Conus Albers (equal-area projection for CONUS).

### Impact
- `area_sqkm` becomes a meaningful feature (~10-50 sq km for a 5-min drive)
- Can be added to the feature list as a trade area size proxy
- Distinct from `h3_cell_count` (which is a discrete count of H3 cells)
