# store_type Column Fix - Complete ✅

## Problem
The `predict_seed_point_sales.ipynb` notebook was failing with:
```
[INTERNAL_ERROR_ATTRIBUTE_NOT_FOUND] Could not find store_type#738836
```

The `store_type` column was missing from the `lce_trade_area_features` table because it wasn't included in the isochrone generation.

## Root Cause
The `create_osrm_isochrones.ipynb` notebook wasn't adding `store_type` to the isochrone data, so when `aggregate_trade_area_features.ipynb` tried to group by `store_type`, it failed.

## Fixes Applied

### 1. ✅ `create_osrm_isochrones.ipynb` - Added `store_type` column

**Cell 6** - Added `store_type` when standardizing locations:
```python
locations_std = locations.select(
    col(id_col).alias("location_id"),
    col(lat_col).alias("latitude"),
    col(lon_col).alias("longitude"),
    lit("Little Caesars").alias("store_type")  # ← ADDED THIS
).filter(...)
```

**Cell 11** - Included `store_type` in results Row:
```python
results.append(Row(
    location_id=row.location_id,
    latitude=row.latitude,
    longitude=row.longitude,
    store_type=row.store_type,  # ← ADDED THIS
    urbanicity_category=row.urbanicity_category,
    drive_time_minutes=row.drive_time_minutes,
    geometry_wkt=wkt
))
```

**Cell 13** - Added `store_type` to schema:
```python
isochrone_schema = StructType([
    StructField("location_id", StringType(), False),
    StructField("latitude", DoubleType(), False),
    StructField("longitude", DoubleType(), False),
    StructField("store_type", StringType(), True),  # ← ADDED THIS
    StructField("urbanicity_category", StringType(), True),
    StructField("drive_time_minutes", IntegerType(), False),
    StructField("geometry_wkt", StringType(), False)
])
```

### 2. ✅ `predict_seed_point_sales.ipynb` - Added fallback for backward compatibility

**Cell 4** - Added check and default value:
```python
seed_points = spark.table(seed_points_table)

# Add store_type if missing (backward compatibility)
if 'store_type' not in seed_points.columns:
    seed_points = seed_points.withColumn('store_type', F.lit('Little Caesars'))
    print("Added default store_type: 'Little Caesars'")

print(f"Total seed points: {seed_points.count()}")
```

## Data Flow

```
lce_locations_mass (bronze)
    ↓
create_osrm_isochrones.ipynb
    → Adds store_type="Little Caesars"
    → Creates lce_isochrones_5min (silver)
    ↓
aggregate_trade_area_features.ipynb
    → Groups by store_type (among others)
    → Creates lce_trade_area_features (gold)
    ↓
predict_seed_point_sales.ipynb
    → Uses store_type ✅
    → Creates lce_expansion_candidates (gold)
```

## Next Steps

### If you've already run the pipeline:
You need to **re-run** `create_osrm_isochrones.ipynb` to regenerate the isochrones table with the `store_type` column.

This will cascade through:
1. `create_osrm_isochrones.ipynb` - Regenerates `lce_isochrones_5min` with `store_type`
2. `aggregate_trade_area_features.ipynb` - Uses the new column
3. `predict_seed_point_sales.ipynb` - Now works correctly

### For fresh runs:
Everything should work end-to-end now.

## Why This Matters

The `store_type` column is used for:
- **Grouping** in trade area aggregation
- **Filtering** different store brands (though we only have LCE now)
- **Future extensibility** - If you add more brands later

## Verification

After re-running, verify with:
```python
# Check isochrones table has store_type
display(spark.table("jdub_demo_aws.geo_silver.lce_isochrones_5min").select("location_id", "store_type", "drive_time_minutes").limit(5))

# Check trade area features has store_type  
display(spark.table("jdub_demo_aws.geo_gold.lce_trade_area_features").select("store_number", "store_type", "city").limit(5))
```

Both should show `store_type = "Little Caesars"`.

---

**Status**: ✅ **Fixed and Ready**
**Files Updated**: 2 notebooks
**Re-run Required**: Yes (isochrone generation and downstream)

