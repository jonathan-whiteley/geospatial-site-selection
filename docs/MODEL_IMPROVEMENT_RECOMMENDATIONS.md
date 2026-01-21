# Sales Prediction Model - Diagnosis & Recommendations

## Executive Summary

**The current XGBoost model produces predictions worse than simply guessing the average sales.** This is not a hyperparameter tuning problem—it's a fundamental data limitation issue.

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Test R² | **-0.64** | Worse than predicting the mean |
| Test RMSE | $260,160 | 2.5x worse than training |
| Train RMSE | $102,411 | Overfitting to training states |

**Root Cause:** 76 total stores is insufficient for ML-based sales prediction, especially with spatial cross-validation that leaves only 13 stores for testing.

---

## Current State Analysis

### Sample Size Breakdown

| State | Stores | Role | Issue |
|-------|--------|------|-------|
| MD | 38 | Training (60%) | Model learns MD-specific patterns |
| NJ | 20 | Training (32%) | Some signal |
| CT | 5 | Training (8%) | **Too few—contributes noise** |
| **MA** | **13** | **Test (100%)** | **Each store = 8% of R²** |
| **Total** | **76** | | **Insufficient for ML** |

### Feature-Target Correlations

**Critical Finding:** Features have almost no predictive relationship with sales.

| Feature | Correlation | Problem |
|---------|-------------|---------|
| population | **-0.30** | **Negative** (counterintuitive) |
| target_demographic_total | **-0.30** | **Negative** (counterintuitive) |
| education | -0.29 | Negative |
| human_activity_index | -0.07 | ~Zero |
| retail | +0.01 | ~Zero |
| food_drink | -0.02 | ~Zero |
| transportation | +0.08 | Strongest, but still weak |

**The strongest predictor (population) is negatively correlated with sales.** This suggests:
1. Selection bias in store placement (stores placed in cheaper/lower-pop areas)
2. Confounding variables (high-pop areas have more competition)
3. Small sample noise masquerading as signal

### Problematic Feature: `state_median_income`

RFE selected `state_median_income` as a top-5 feature, but it's a **state-level constant**:

| State | state_median_income | All stores in state |
|-------|---------------------|---------------------|
| MA | $89,645 | Same value |
| CT | $83,572 | Same value |
| NJ | $89,703 | Same value |
| MD | $90,203 | Same value |

This acts as a **proxy for state ID**, not a meaningful location feature. The model learns spurious state-level patterns that don't generalize.

---

## Why XGBoost Failed

1. **Dominated by MD** (60% of training) → Learned MD-specific patterns
2. **CT is noise** (5 stores can't teach generalizable patterns)
3. **Spatial CV too aggressive** → 13-store test set is statistically unstable
4. **No feature signal** → Best correlation is |0.30|, and it's in the wrong direction
5. **State-level feature leakage** → `state_median_income` encodes state identity

---

## Recommended Approach

### Phase 1: Establish Baselines (Immediate)

Before any ML, verify simple approaches:

```python
# Baseline 1: Predict the mean
mean_sales = y_train.mean()
baseline_rmse = np.sqrt(mean_squared_error(y_test, [mean_sales] * len(y_test)))
print(f"Predict-mean RMSE: ${baseline_rmse:,.0f}")

# Baseline 2: Single-feature linear regression
from sklearn.linear_model import LinearRegression
simple = LinearRegression()
simple.fit(X_train[['population']], np.log1p(y_train))
simple_pred = np.expm1(simple.predict(X_test[['population']]))
print(f"Population-only R²: {r2_score(y_test, simple_pred):.3f}")
```

### Phase 2: Abandon Spatial CV, Use All Data

With 76 stores, you cannot afford to hold out 17% for testing.

```python
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.linear_model import RidgeCV

# Use ALL 76 stores with Leave-One-Out CV
X_all = train_encoded[['population', 'total_poi_count']]  # Just 2 features
y_all = np.log1p(train_encoded['annual_sales'])

# Ridge regression (appropriate for small samples)
ridge = RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0])

# Leave-One-Out cross-validation
loo = LeaveOneOut()
y_pred_loo = cross_val_predict(ridge, X_all, y_all, cv=loo)
y_pred_loo = np.expm1(y_pred_loo)
y_actual = np.expm1(y_all)

loo_r2 = r2_score(y_actual, y_pred_loo)
loo_rmse = np.sqrt(mean_squared_error(y_actual, y_pred_loo))

print(f"Leave-One-Out CV R²: {loo_r2:.3f}")
print(f"Leave-One-Out CV RMSE: ${loo_rmse:,.0f}")
```

### Phase 3: Simplify the Model

**Rule of thumb:** With n samples, use at most n/10 to n/20 features.
- 76 stores → **4-7 features maximum**
- Prefer regularized linear models over tree ensembles

```python
from sklearn.linear_model import RidgeCV, LassoCV

# Remove state_median_income, use only location-level features
simple_features = ['population', 'total_poi_count', 'human_activity_index']

# Ridge handles multicollinearity
ridge = RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0])
ridge.fit(X_train[simple_features], y_train_log)

# Lasso for automatic feature selection
lasso = LassoCV(alphas=[0.01, 0.1, 1.0, 10.0], cv=5)
lasso.fit(X_train[simple_features], y_train_log)

print(f"Ridge coefficients: {dict(zip(simple_features, ridge.coef_))}")
print(f"Lasso coefficients: {dict(zip(simple_features, lasso.coef_))}")
```

### Phase 4: Shift Goal from Prediction to Ranking

Even with poor R², the model may rank locations correctly:

```python
from scipy.stats import spearmanr

# Spearman rank correlation
rank_corr, p_value = spearmanr(y_test, y_pred_test)
print(f"Spearman rank correlation: {rank_corr:.3f} (p={p_value:.3f})")

# Top-quartile precision (most actionable metric)
k = max(1, len(y_test) // 4)  # Top 25%
actual_top = set(y_test.nlargest(k).index)
predicted_top = set(pd.Series(y_pred_test, index=y_test.index).nlargest(k).index)
precision = len(actual_top & predicted_top) / k
print(f"Top-quartile precision: {precision:.0%}")
```

**If Spearman > 0.5**, the model is useful for ranking candidates even if R² is poor.

---

## Alternative: Heuristic Scoring

Given the data limitations, a domain-driven heuristic may outperform ML:

```python
def heuristic_score(df):
    """
    Simple scoring based on retail fundamentals:
    - Higher population = more customers
    - More POIs = more foot traffic
    - Fewer food/drink competitors = less competition
    """
    score = (
        df['population'].rank(pct=True) * 0.40 +
        df['total_poi_count'].rank(pct=True) * 0.30 +
        (1 - df['food_drink'].rank(pct=True)) * 0.20 +  # Lower = better
        df['human_activity_index'].rank(pct=True) * 0.10
    )
    return score

candidates['heuristic_score'] = heuristic_score(candidates)
candidates_ranked = candidates.sort_values('heuristic_score', ascending=False)
```

**Advantages:**
- Transparent and explainable
- No overfitting risk
- Easy to adjust weights based on business intuition
- Works with any sample size

---

## Realistic Expectations

### What's Achievable with 76 Stores

| Metric | Realistic Target | Notes |
|--------|------------------|-------|
| LOO-CV R² | 0.10 - 0.30 | Positive R² would be a win |
| Spearman correlation | 0.40 - 0.60 | Useful for ranking |
| Top-quartile precision | 50% - 70% | Better than random (25%) |

### What's NOT Achievable

- Accurate dollar predictions (±$50K)
- R² > 0.5 without more data
- Reliable spatial generalization (train on CT/NJ/MD → predict MA)

---

## Data Collection Priorities

If you can acquire more data, prioritize:

| Data Type | Impact | Feasibility |
|-----------|--------|-------------|
| **More stores** (other regions) | High | Depends on franchise network |
| **Historical sales** (multi-year) | High | Internal data request |
| **Competition density** | Medium | Derivable from existing POI data |
| **Traffic counts** | Medium | State DOT (free but effort) |
| **Tract-level income** | Medium | Census API (already integrated) |

---

## Action Items

### Immediate (This Week)

1. [x] ~~Diagnose model failure~~ → Completed: small sample + no feature signal
2. [ ] Establish predict-mean baseline RMSE
3. [ ] Run Leave-One-Out CV with Ridge on all 76 stores
4. [ ] Calculate Spearman rank correlation (even if R² is negative)
5. [ ] Remove `state_median_income` from features

### Short-Term (Next Sprint)

6. [ ] Implement heuristic scoring as alternative
7. [ ] Add competition density feature from `pois_competitors`
8. [ ] Replace state-level income with tract-level from Census
9. [ ] Evaluate model on ranking metrics (Spearman, top-k precision)

### If More Data Becomes Available

10. [ ] Re-evaluate XGBoost with 150+ stores
11. [ ] Consider mixed-effects model with state random effects
12. [ ] Implement proper train/validation/test split

---

## Summary

| Question | Answer |
|----------|--------|
| Why did XGBoost fail? | 76 stores is too few; features don't correlate with sales |
| Can tuning fix it? | No—this is a data problem, not a model problem |
| What should we do? | Simpler models, all-data CV, focus on ranking |
| Is ML the right approach? | Possibly not—consider heuristic scoring |

**The path forward is simplification, not sophistication.**

---

*Document updated: 2026-01-21*
*Based on diagnostic analysis of XGBoost model failure*
