# Databricks notebook source
# MAGIC %md
# MAGIC # Real Drive-Time Isochrones using Mapbox API
# MAGIC
# MAGIC Uses Mapbox Isochrone API for real road network routing.
# MAGIC - **Free tier**: 100,000 requests/month
# MAGIC - **Real routing**: Uses actual road network data
# MAGIC - **Fast**: API-based, no local installation needed

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

%pip install -q requests pyyaml

# COMMAND ----------

dbutils.widgets.text("catalog", "jdub_demo_aws")
dbutils.widgets.text("schema", "geospatial_site_selection")
dbutils.widgets.text("mapbox_token", "", "Mapbox Access Token")
dbutils.widgets.text("input_table", "bronze_rmc_retail_locations_grocery", "Input Locations Table")
dbutils.widgets.text("output_table", "silver_rmc_isochrones", "Output Table")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
mapbox_token = dbutils.widgets.get("mapbox_token")
input_table = dbutils.widgets.get("input_table")
output_table = dbutils.widgets.get("output_table")

if not mapbox_token:
    raise ValueError("Mapbox token required! Get free token at https://account.mapbox.com/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Locations and Urbanicity

# COMMAND ----------

from pyspark.sql.functions import col, expr, broadcast, lit

# Read locations
locations = spark.table(f"{catalog}.{schema}.{input_table}")

# Auto-detect columns
columns = locations.columns
id_col = next((c for c in columns if c in ['store_number', 'point_id', 'id', 'location_id']), columns[0])
lat_col = next((c for c in columns if c in ['latitude', 'lat', 'y']), None)
lon_col = next((c for c in columns if c in ['longitude', 'lon', 'lng', 'x']), None)

if not lat_col or not lon_col:
    raise ValueError(f"Cannot find lat/lon columns. Available: {columns}")

# Standardize columns
locations_std = locations.select(
    col(id_col).alias("location_id"),
    col(lat_col).alias("latitude"),
    col(lon_col).alias("longitude")
).filter(col("latitude").isNotNull() & col("longitude").isNotNull())

# Load H3 features for urbanicity
h3_features = spark.table(f"{catalog}.{schema}.silver_h3_features").select(
    col("h3_cell_id"),
    col("urbanicity_category")
)

# Add urbanicity to locations
locations_with_urbanicity = (
    locations_std
    .withColumn("h3_cell", expr("h3_longlatash3string(longitude, latitude, 9)"))
    .join(
        broadcast(h3_features.withColumnRenamed("h3_cell_id", "h3_cell")),
        "h3_cell",
        "left"
    )
    .fillna({"urbanicity_category": "suburban"})
)

# Add drive times based on urbanicity
locations_with_times = locations_with_urbanicity.withColumn(
    "drive_time_minutes",
    expr("""
        CASE
            WHEN urbanicity_category = 'urban' THEN 10
            WHEN urbanicity_category = 'suburban' THEN 20
            WHEN urbanicity_category = 'rural' THEN 30
            ELSE 20
        END
    """)
)

location_count = locations_with_times.count()
print(f"Loaded {location_count} locations")

display(locations_with_times.groupBy("urbanicity_category", "drive_time_minutes").count())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Isochrones via Mapbox API

# COMMAND ----------

import requests
import json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

def get_mapbox_isochrone(lon, lat, minutes, token):
    """
    Get isochrone polygon from Mapbox API

    Returns WKT polygon string or None
    """
    url = f"https://api.mapbox.com/isochrone/v1/mapbox/driving/{lon},{lat}"

    params = {
        'contours_minutes': minutes,
        'polygons': 'true',
        'access_token': token
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if 'features' in data and len(data['features']) > 0:
                geometry = data['features'][0]['geometry']

                # Convert GeoJSON to WKT
                if geometry['type'] == 'Polygon':
                    coords = geometry['coordinates'][0]
                    wkt_coords = ', '.join([f"{lon} {lat}" for lon, lat in coords])
                    return f"POLYGON (({wkt_coords}))"

        return None

    except Exception as e:
        print(f"Error for location ({lat}, {lon}): {e}")
        return None

# COMMAND ----------

# Collect locations (if too many, process in batches)
location_rows = locations_with_times.collect()

print(f"Generating isochrones for {len(location_rows)} locations...")
print("This will make API calls - stay within rate limits!")

# COMMAND ----------

from pyspark.sql import Row
import time

results = []
batch_size = 100  # Process in batches for rate limiting

for i, row in enumerate(location_rows):
    if i % 10 == 0:
        print(f"Processing {i}/{len(location_rows)}...")

    # Get isochrone from Mapbox
    wkt = get_mapbox_isochrone(
        row.longitude,
        row.latitude,
        row.drive_time_minutes,
        mapbox_token
    )

    if wkt:
        results.append(Row(
            location_id=row.location_id,
            latitude=row.latitude,
            longitude=row.longitude,
            urbanicity_category=row.urbanicity_category,
            drive_time_minutes=row.drive_time_minutes,
            geometry_wkt=wkt
        ))

    # Rate limiting: 300 requests/minute for free tier
    if (i + 1) % batch_size == 0:
        print(f"  Pausing for rate limit...")
        time.sleep(20)  # Sleep 20 seconds every 100 requests

print(f"✅ Generated {len(results)} isochrones successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save to Delta

# COMMAND ----------

from pyspark.sql.functions import current_timestamp

# Create DataFrame from results
isochrone_schema = StructType([
    StructField("location_id", StringType(), False),
    StructField("latitude", DoubleType(), False),
    StructField("longitude", DoubleType(), False),
    StructField("urbanicity_category", StringType(), True),
    StructField("drive_time_minutes", IntegerType(), False),
    StructField("geometry_wkt", StringType(), False)
])

isochrones_df = spark.createDataFrame(results, schema=isochrone_schema)

# Convert WKT to geometry and add metadata
isochrones_final = (
    isochrones_df
    .withColumn("geometry", expr("ST_GeomFromText(geometry_wkt, 4326)"))
    .withColumn("area_sqkm", expr("ST_Area(geometry) / 1000000"))
    .withColumn("created_timestamp", current_timestamp())
    .withColumn("routing_provider", lit("mapbox"))
    .drop("geometry_wkt")
)

# Save to Delta
output_table_name = f"{catalog}.{schema}.{output_table}"

(
    isochrones_final
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(output_table_name)
)

print(f"✅ Saved {len(results)} isochrones to {output_table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Statistics

# COMMAND ----------

display(spark.sql(f"""
    SELECT
        urbanicity_category,
        drive_time_minutes,
        COUNT(*) as location_count,
        ROUND(AVG(area_sqkm), 2) as avg_area_sqkm,
        ROUND(MIN(area_sqkm), 2) as min_area_sqkm,
        ROUND(MAX(area_sqkm), 2) as max_area_sqkm
    FROM {output_table_name}
    GROUP BY urbanicity_category, drive_time_minutes
    ORDER BY urbanicity_category
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Visualize

# COMMAND ----------

%pip install -q folium

# COMMAND ----------

import folium

sample = spark.table(output_table_name).limit(50)

geojson_rows = sample.withColumn(
    "geojson",
    expr("ST_AsGeoJSON(geometry)")
).select("location_id", "urbanicity_category", "drive_time_minutes", "geojson").collect()

features = [
    {
        "type": "Feature",
        "properties": {
            "location_id": row["location_id"],
            "urbanicity": row["urbanicity_category"],
            "minutes": row["drive_time_minutes"]
        },
        "geometry": json.loads(row["geojson"])
    }
    for row in geojson_rows
]

m = folium.Map(location=[42.4, -71.4], zoom_start=10)

colors = {"urban": "red", "suburban": "blue", "rural": "green"}

for feature in features:
    urbanicity = feature["properties"]["urbanicity"]
    folium.GeoJson(
        feature,
        style_function=lambda x, color=colors.get(urbanicity, "gray"): {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.3
        }
    ).add_to(m)

m
