# Removed Visualization Features

Features removed from `viz_layer_prep.ipynb` for simplicity. Reference this document if you want to restore them.

---

## 1. AI Feasibility Score (ai_query)

Used `ai_query()` to evaluate location feasibility based on factors not captured in demographic features.

### What it did
- Filtered to `new_store` candidates only (partner candidates don't need this)
- Called Databricks AI model to evaluate each location based on:
  1. Proximity to bodies of water, parks, or green spaces
  2. Proximity to major highways and accessibility
  3. Visibility from main roads
  4. Physical barriers (railroads, rivers, hills)
  5. Nearby landmarks affecting foot traffic
- Returned a 1-5 feasibility score and 2-sentence rationale
- Added columns: `ai_feasibility_score`, `ai_feasibility_rationale`

### Code (commented out)
```python
# Filter to only new_store candidates
new_store_candidates = viz_candidates.filter(col("fulfillment_strategy") == "new_store")
partner_candidates = viz_candidates.filter(col("fulfillment_strategy") == "partner")

new_store_candidates.createOrReplaceTempView("new_store_candidates_temp")

ai_evaluated = spark.sql("""
    SELECT
        candidate_id, latitude, longitude,
        ai_query(
            'databricks-gpt-5-2',
            CONCAT(
                'You are a retail site selection expert for Little Caesars Pizza. ',
                'Evaluate the feasibility of opening a new restaurant at coordinates: ',
                CAST(latitude AS STRING), ', ', CAST(longitude AS STRING), ' in Massachusetts. ',
                'Consider ONLY these location-specific factors NOT captured in demographic data: ',
                '1) Proximity to bodies of water, parks, or green spaces that limit development ',
                '2) Proximity to major highways and accessibility ',
                '3) Visibility from main roads ',
                '4) Physical barriers (railroads, rivers, hills) affecting access ',
                '5) Nearby landmarks or attractions affecting foot traffic. ',
                'Provide a feasibility score from 1-5 (5=highest feasibility) and a brief 2-sentence rationale. ',
                'Format your response EXACTLY as: SCORE: [1-5] | RATIONALE: [your 2-sentence explanation]'
            )
        ) as ai_response
    FROM new_store_candidates_temp
""")

# Parse response
ai_parsed = ai_evaluated.withColumn(
    "ai_feasibility_score",
    F.regexp_extract(col("ai_response"), r"SCORE:\s*(\d)", 1).cast("int")
).withColumn(
    "ai_feasibility_rationale",
    F.regexp_extract(col("ai_response"), r"RATIONALE:\s*(.+)", 1)
).drop("ai_response")

# Handle parsing failures - default to score 3 (neutral)
ai_parsed = ai_parsed.withColumn(
    "ai_feasibility_score",
    when(col("ai_feasibility_score").isNull(), 3).otherwise(col("ai_feasibility_score"))
)

# Join back and union with partner candidates (which get null scores)
new_store_with_ai = new_store_candidates.join(
    ai_parsed.select("candidate_id", "ai_feasibility_score", "ai_feasibility_rationale"),
    "candidate_id", "left"
)
partner_with_nulls = partner_candidates.withColumn(
    "ai_feasibility_score", lit(None).cast("int")
).withColumn(
    "ai_feasibility_rationale", lit(None).cast("string")
)
viz_candidates = new_store_with_ai.unionByName(partner_with_nulls)
```

### Why removed
- Adds significant runtime cost (AI calls for each candidate)
- Requires specific model availability
- Not essential for core visualization functionality

---

## 2. Folium Map Visualization

Interactive map rendered in the notebook showing stores, trade areas, and candidates.

### What it did
- Created an interactive Folium map centered on Massachusetts
- Displayed 4 layers:
  1. **LCE Trade Areas** (green isochrones) - 5-min drive polygons
  2. **Partner Trade Areas** (blue isochrones) - convenience store coverage
  3. **LCE Store Markers** (green circles) - existing stores with popups
  4. **Expansion Candidates** (red circles) - top 50 by predicted sales
- Added legend and fullscreen button

### Code
```python
%pip install folium --quiet

import folium
from folium.plugins import Fullscreen
import pandas as pd
from shapely import wkt
from shapely.geometry import mapping

# Load data
lce_stores_pd = spark.table(f"{catalog}.{gold_schema}.viz_existing_stores").select(
    "store_number", "latitude", "longitude", "city", "state", "population"
).toPandas()

lce_isochrones_df = spark.table(f"{catalog}.{silver_schema}.isochrones_lce")
lce_isochrones_gdf = lce_isochrones_df.selectExpr(
    "location_id as store_number", "ST_AsText(geometry) as geometry_wkt",
    "drive_time_minutes", "area_sqkm"
).toPandas()

# Convert to GeoJSON
lce_isochrones_geojson = {"type": "FeatureCollection", "features": []}
for _, row in lce_isochrones_gdf.iterrows():
    geom = wkt.loads(row['geometry_wkt'])
    lce_isochrones_geojson["features"].append({
        "type": "Feature",
        "properties": {"store_number": row['store_number'], "drive_time_minutes": row['drive_time_minutes']},
        "geometry": mapping(geom)
    })

# Similar for partner isochrones...
partner_isochrones_df = spark.table(f"{catalog}.{silver_schema}.isochrones_partners")
# ... conversion code ...

candidates_pd = spark.table(f"{catalog}.{gold_schema}.viz_expansion_candidates").orderBy(
    F.desc("predicted_annual_sales")
).limit(50).select("h3_cell_id", "latitude", "longitude", "predicted_annual_sales", "population").toPandas()

# Create map
ma_center = [42.4072, -71.3824]
folium_map = folium.Map(
    location=ma_center, zoom_start=9,
    tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attr='CartoDB'
)

# Add LCE trade areas (green isochrones)
for feature in lce_isochrones_geojson['features']:
    coords = feature['geometry']['coordinates'][0]
    polygon_coords = [[lat, lon] for lon, lat in coords]
    folium.Polygon(
        locations=polygon_coords, color='#10b981', fill=True,
        fillColor='#10b981', fillOpacity=0.1, weight=1,
        popup=f"<b>LCE Store {feature['properties']['store_number']}</b>"
    ).add_to(folium_map)

# Add partner trade areas (blue isochrones)
for feature in partner_isochrones_geojson['features']:
    # ... similar code with blue color ...

# Add LCE store markers (green)
for _, store in lce_stores_pd.iterrows():
    folium.CircleMarker(
        location=[store['latitude'], store['longitude']], radius=6,
        popup=f"<b>Little Caesars</b><br>Store: {store['store_number']}",
        color='#10b981', fill=True, fillColor='#34d399', fillOpacity=0.8
    ).add_to(folium_map)

# Add expansion candidates (red)
for _, cand in candidates_pd.iterrows():
    folium.CircleMarker(
        location=[cand['latitude'], cand['longitude']], radius=5,
        popup=f"<b>Expansion</b><br>Sales: ${cand['predicted_annual_sales']:,.0f}",
        color='#ef4444', fill=True, fillColor='#f87171', fillOpacity=0.7
    ).add_to(folium_map)

# Add legend HTML
legend_html = '''
<div style="position: fixed; bottom: 30px; right: 30px; ...">
<p>LCE Stores (green), Trade Areas, Partner Areas (blue), Candidates (red)</p>
</div>
'''
folium_map.get_root().html.add_child(folium.Element(legend_html))

# Add fullscreen
Fullscreen(position='topleft').add_to(folium_map)

display(folium_map)
```

### Why removed
- Adds `folium` and `shapely` dependencies
- Notebook-only visualization (not used by React app)
- Can view same data in React app or create separate viz notebook

---

## Restoring These Features

To restore either feature:
1. Copy the code from this document
2. Add as a new cell in `viz_layer_prep.ipynb`
3. For Folium: add `folium` to job dependencies in `gold_job.yml`
4. For AI: ensure `ai_query` model is available in your workspace
