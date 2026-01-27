# Strategic Modeling Plan: Massachusetts Sales Prediction

This document outlines a high-relevance modeling framework using a curated subset of **575 stores**. By focusing on "peer states" that share Massachusetts’ economic and spatial DNA, we ensure high predictive accuracy while minimizing the overhead of national-scale isochrone generation.

---

## 1. The Dataset (High-Correlation Cluster)
We exclude high-variance or geographically dissimilar states (e.g., TX, AL) in favor of states that mirror the urban density, wealth, and infrastructure of Massachusetts.

| State | Store Count | Strategic Modeling Value |
| :--- | :--- | :--- |
| **Massachusetts (MA)** | 10 | **Target State:** Used for final validation and "Gold Standard" testing. |
| **Michigan (MI)** | 288 | **Legacy Proxy:** Similar climate, seasonality, and older town infrastructure. |
| **Virginia (VA)** | 91 | **Wealth Proxy:** NoVa suburbs mirror the demographics of Greater Boston. |
| **New York (NY)** | 73 | **Density Proxy:** Complex urban centers and high competitive pressure. |
| **Washington (WA)** | 67 | **Innovation Proxy:** High-tech coastal wealth and geographic barriers. |
| **Maryland (MD)** | 39 | **Commuter Proxy:** Intense traffic patterns and high median income. |
| **New Jersey (NJ)** | 7 | **Saturation Proxy:** Extreme density; helps model "over-stored" markets. |
| **TOTAL** | **575** | **~14% of national footprint; optimal for XGBoost.** |

---

## 2. Spatial Cross-Validation Strategy
Standard random splits suffer from **Spatial Autocorrelation**, where the model "cheats" by looking at nearby neighbors. We implement **Leave-One-Region-Out (LORO)** validation to ensure the model learns generalizable retail logic.

### Fold Distribution
* **Fold 1 (Great Lakes):** Michigan (288 stores)
* **Fold 2 (South-Atlantic):** Virginia + Maryland (130 stores)
* **Fold 3 (Northeast Corridor):** New York + New Jersey (80 stores)
* **Fold 4 (Target & Pacific):** Washington + Massachusetts (77 stores)

### Validation Workflow
1. **Iterate:** In each round, the model is trained on 3 folds and tested on the 4th (completely unseen) region.
2. **MA Guardrail:** To finalize the model for your specific goal, train on Folds 1-3 and test exclusively on the 10 MA stores. If the error (MAE) is low here, the model is ready for MA site selection.

---

## 3. XGBoost Configuration
With 575 rows, we can capture non-linearities (e.g., how sales peak at a certain income level) without over-fitting.

| Parameter | Recommended | Purpose |
| :--- | :--- | :--- |
| `max_depth` | 4 | Allows for interaction between density and income. |
| `learning_rate`| 0.05 | Prevents the model from over-prioritizing MI's larger sample size. |
| `subsample` | 0.8 | Ensures robustness by training on random subsets of stores. |
| `reg_lambda` | 1.0 | L2 regularization to penalize extreme coefficient weights. |

---

---