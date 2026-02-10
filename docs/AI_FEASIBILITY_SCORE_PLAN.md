# AI Feasibility Score Plan

## Overview

Add a **1-5 star AI Feasibility Score** with a 2-sentence rationale to each candidate location. The score evaluates real-world site characteristics that the current XGBoost model (spatial/demographic features only) cannot capture: road access, physical barriers, nearby landmarks, water/greenspace proximity, visibility, and competitive landscape.

The core idea: use **Gemini with Google Maps Grounding** to ask an LLM grounded in live Google Maps data to evaluate each candidate's lat/lng, then surface the score and rationale in the React app.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Gold Notebook: score_candidate_feasibility.ipynb       │
│                                                         │
│  FOR each candidate (lat, lng):                         │
│    → Call Databricks Model Serving endpoint             │
│      → Custom PyFunc wraps Gemini API + Maps Grounding  │
│        → Returns: { score: 1-5, rationale: "..." }      │
│                                                         │
│  Output: gold.candidates_feasibility_scores             │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  viz_layer_prep.ipynb                                   │
│  JOIN feasibility scores → viz_expansion_candidates     │
│  New columns: feasibility_score, feasibility_rationale  │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│  React App                                              │
│  Display stars + rationale on candidate cards/popups    │
│  Optional: "Refresh Score" button → ai_query() live     │
└─────────────────────────────────────────────────────────┘
```

### Why batch (gold notebook) + optional live refresh?

- **Batch-first**: ~3,000 candidates scored during pipeline run. Scores persist in Delta table. App reads pre-computed scores at O(1). No latency at page load.
- **Live refresh (optional)**: A single candidate can be re-scored on-demand via `ai_query()` or a direct REST call to the serving endpoint from the app. Useful if a user wants a fresh evaluation.

---

## Google Maps Grounding: How It Works

Source: https://ai.google.dev/gemini-api/docs/maps-grounding

| Aspect | Detail |
|---|---|
| **What it does** | Gemini queries live Google Maps data (places, roads, reviews, landmarks) before generating a response, grounding output in real-world facts |
| **API** | Gemini API with `tools: [{"googleMaps": {}}]` and optional `latLng` in `retrievalConfig` |
| **Supported models** | Gemini 2.5 Pro, 2.5 Flash, 2.5 Flash-Lite, 2.0 Flash |
| **Cost** | $25 per 1,000 grounded prompts (only charged when Maps sources are returned) |
| **Free tier** | 500 requests/day |
| **Latency** | ~2-5s per call (Gemini inference + Maps lookup) |
| **Output** | Text response + `groundingMetadata` with place IDs, source URIs, support spans |
| **Attribution required** | Yes - must display Google Maps sources near generated text |

### Example API Call

```python
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    "Rate this location for a pizza restaurant on a 1-5 scale...",
    tools=[{"google_maps": {}}],
    tool_config={"retrieval_config": {"lat_lng": {"latitude": 42.36, "longitude": -71.06}}}
)
```

---

## Implementation Plan

### Step 1: Gemini API Key as Databricks Secret

```bash
databricks secrets create-scope gemini-api
databricks secrets put-secret gemini-api GEMINI_API_KEY
```

Store the Google AI Studio API key. The custom model and notebooks will read from this scope.

### Step 2: Custom MLflow PyFunc Model

Create a model that wraps the Gemini + Maps Grounding call. This is necessary because:
- Databricks External Model endpoints use a standard chat interface and **do not support** the `tools: [{"googleMaps": {}}]` parameter
- A custom PyFunc gives full control over the Gemini request format

```python
import mlflow
import google.generativeai as genai
import json
import pandas as pd

class FeasibilityScorer(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        import os
        # API key injected via endpoint environment variable (from secret scope)
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        """
        Input:  DataFrame with columns [latitude, longitude, candidate_id]
        Output: DataFrame with columns [candidate_id, feasibility_score, feasibility_rationale]
        """
        results = []
        for _, row in model_input.iterrows():
            prompt = self._build_prompt(row["latitude"], row["longitude"])
            response = self.model.generate_content(
                prompt,
                tools=[{"google_maps": {}}],
                tool_config={
                    "retrieval_config": {
                        "lat_lng": {
                            "latitude": row["latitude"],
                            "longitude": row["longitude"]
                        }
                    }
                }
            )
            parsed = self._parse_response(response.text)
            results.append({
                "candidate_id": row["candidate_id"],
                "feasibility_score": parsed["score"],
                "feasibility_rationale": parsed["rationale"]
            })
        return pd.DataFrame(results)

    def _build_prompt(self, lat, lng):
        return f"""You are a commercial real estate analyst evaluating a location at
coordinates ({lat}, {lng}) for a new pizza restaurant.

Rate this location from 1 to 5 stars based on:
- Proximity to major roads and highway access
- Visibility and foot traffic potential
- Nearby complementary businesses (retail, offices, gyms)
- Physical barriers (railroads, rivers, steep terrain)
- Proximity to parks, waterfronts, or green spaces
- Competitor saturation (other pizza/fast food nearby)
- Nearby landmarks that drive traffic

Respond in EXACTLY this JSON format:
{{"score": <1-5>, "rationale": "<2 sentences>"}}

Be strict: 1 = poor site, 5 = excellent site. Only return the JSON."""

    def _parse_response(self, text):
        try:
            return json.loads(text.strip().strip("```json").strip("```"))
        except:
            return {"score": 3, "rationale": "Unable to evaluate location."}
```

**Register and log:**

```python
with mlflow.start_run():
    mlflow.pyfunc.log_model(
        artifact_path="feasibility_scorer",
        python_model=FeasibilityScorer(),
        pip_requirements=["google-generativeai>=0.8.0", "pandas"],
        registered_model_name=f"{catalog}.{gold_schema}.feasibility_scorer"
    )
```

### Step 3: Deploy Model Serving Endpoint

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.serving_endpoints.create(
    name="feasibility-scorer",
    config={
        "served_entities": [{
            "entity_name": f"{catalog}.{gold_schema}.feasibility_scorer",
            "entity_version": "1",
            "workload_size": "Small",
            "scale_to_zero_enabled": True,
            "environment_vars": {
                "GEMINI_API_KEY": "{{secrets/gemini-api/GEMINI_API_KEY}}"
            }
        }]
    }
)
```

Key config:
- **Scale to zero** = True (only pay when scoring)
- **Workload size** = Small (each request is a single Gemini API call, not compute-heavy)
- Secret reference injects the API key at runtime

### Step 4: Gold Notebook - Batch Scoring

New notebook: `transformations/03_gold/score_candidate_feasibility.ipynb`

```python
# Cell 1: Read candidates
candidates_df = spark.table(f"{catalog}.{gold_schema}.candidates_finalized") \
    .select("candidate_id", "latitude", "longitude")

# Cell 2: Score via serving endpoint (batched with rate limiting)
import requests, time

endpoint_url = f"https://{workspace_host}/serving-endpoints/feasibility-scorer/invocations"
token = dbutils.notebook.entry_point.getDbUtils().notebook().getContext().apiToken().get()

results = []
for batch in chunk(candidates_df.collect(), size=50):
    pdf = pd.DataFrame([row.asDict() for row in batch])
    resp = requests.post(endpoint_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"dataframe_records": pdf.to_dict(orient="records")}
    )
    results.extend(resp.json()["predictions"])
    time.sleep(1)  # Rate limiting

# Cell 3: Write results
scores_df = spark.createDataFrame(results)
scores_df.write.mode("overwrite").saveAsTable(
    f"{catalog}.{gold_schema}.candidates_feasibility_scores"
)
```

**Rate limiting strategy**: Batch 50 candidates, 1s pause between batches. At ~3,000 candidates and ~3s per Gemini call, full scoring takes ~3-4 hours sequentially. Can parallelize with ThreadPoolExecutor (10 workers) to bring down to ~20-30 min.

### Step 5: Integrate into viz_layer_prep

In `viz_layer_prep.ipynb`, join feasibility scores into `viz_expansion_candidates`:

```sql
SELECT c.*, f.feasibility_score, f.feasibility_rationale
FROM candidates_finalized c
LEFT JOIN candidates_feasibility_scores f
  ON c.candidate_id = f.candidate_id
```

### Step 6: React App - Display Scores

**Backend** (`expansion.py`): Scores already in `viz_expansion_candidates` - no new endpoint needed.

**Frontend**: Add to candidate card/popup:
- Star rating display (1-5 filled/empty stars)
- Rationale text (2 sentences, expandable)
- Google Maps attribution link (required)

**Optional live refresh** endpoint:
```python
@router.post("/api/expansion/rescore")
async def rescore_candidate(candidate_id: str, lat: float, lng: float):
    """Call serving endpoint for a single candidate re-evaluation."""
    resp = requests.post(SERVING_ENDPOINT_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"dataframe_records": [{"candidate_id": candidate_id,
                                      "latitude": lat, "longitude": lng}]}
    )
    return resp.json()["predictions"][0]
```

### Step 7: Gold Job DAG Update

In `resources/gold_job.yml`, add a new task:

```yaml
- task_key: score_candidate_feasibility
  depends_on:
    - task_key: predict_candidate_sales
  notebook_task:
    notebook_path: transformations/03_gold/score_candidate_feasibility.ipynb
```

Updated DAG:
```
agg_h3_features_current_stores ──┐
                                 ├──► predict_candidate_sales
agg_h3_features_candidates ──────┘              │
                                                ▼
                                 score_candidate_feasibility
                                                │
                                                ▼
                                         viz_layer_prep
```

---

## Cost Estimate

| Item | Calculation | Cost |
|---|---|---|
| Batch scoring (3,000 candidates) | 3,000 prompts x $0.025 | **$75** |
| Live refresh (ad-hoc) | ~10-50 per session x $0.025 | **$0.25 - $1.25** |
| Model serving (scale-to-zero) | Only during scoring | **~$2-5/run** |
| **Total per pipeline run** | | **~$80** |

Free tier (500/day) covers live refresh and testing. Batch runs will exceed free tier.

---

## Requirements & Considerations

### Must-Have
1. **Google AI Studio API key** - Sign up at https://aistudio.google.com, create an API key with Maps Grounding enabled
2. **Databricks Secret Scope** - Store the key securely
3. **Google Maps attribution** - Required in the app wherever scores/rationale are displayed. Must show "Powered by Google Maps" with proper formatting

### Technical Considerations
1. **Gemini rate limits** - Default 15 RPM for free tier, 2,000 RPM for paid. Batch scoring needs paid tier or careful throttling
2. **Latency** - Each call ~2-5s. Batch scoring is long-running. Use `ThreadPoolExecutor` for parallelism
3. **Determinism** - LLM outputs vary between calls. Same location may get 3 stars one run, 4 the next. Consider averaging multiple runs or setting temperature=0
4. **Prompt tuning** - The prompt is the most important lever. Iterate on it with a sample of ~20 known-good/bad locations before batch scoring
5. **Fallback** - If Gemini/Maps API is down, the pipeline shouldn't fail. Use try/except with a default score of `null`
6. **Model versioning** - Log the prompt template and model version in MLflow for reproducibility

### Alternative Approaches Considered

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| **Gemini + Maps Grounding via custom PyFunc** (chosen) | Real-time Maps data, structured scoring, works with Databricks serving | Cost ($75/batch), latency, Gemini dependency | **Best fit** - gives factual grounding |
| **Databricks External Model → Gemini** | Simpler setup | Cannot pass `tools: [{"googleMaps": {}}]` through external model interface | **Won't work** for Maps grounding |
| **Direct Gemini API from app only (no serving)** | Simplest | No Databricks integration, no batch scoring, harder to audit | Good for prototype |
| **OpenAI + Google Places API separately** | More control | Two APIs to manage, no grounding integration, more code | Over-engineered |
| **Static feature engineering (OSM data)** | No LLM cost, deterministic | Stale data, no subjective assessment, massive feature work | Different problem |

---

## Phased Rollout

### Phase 1: Prototype (1-2 days)
- Get Gemini API key
- Test Maps grounding manually with 5-10 candidate lat/lngs
- Tune the prompt for consistent 1-5 scoring
- Validate that grounding returns useful local context

### Phase 2: Serving Endpoint (1 day)
- Create and register the custom PyFunc model
- Deploy to model serving with scale-to-zero
- Test with sample requests

### Phase 3: Batch Pipeline (1 day)
- Create `score_candidate_feasibility.ipynb`
- Add to gold job DAG
- Run on full candidate set
- Join into viz layer

### Phase 4: App Integration (1 day)
- Add score display to candidate cards
- Add Google Maps attribution
- Optional: live refresh endpoint

---

## Open Questions

1. **Google Maps API key vs AI Studio key** - Maps Grounding uses the Gemini API (AI Studio key), not the Google Maps Platform API key. Confirm which billing account to use.
2. **Score caching** - Should we cache scores across pipeline runs (only re-score new candidates) or always re-score all? Caching saves cost but scores may go stale.
3. **Prompt customization** - Should the scoring criteria be configurable (e.g., in `poi_config.yml`) or hardcoded in the model?
4. **Widget rendering** - Google Maps Grounding can return a widget context token for interactive map display. Worth exploring for the app?
