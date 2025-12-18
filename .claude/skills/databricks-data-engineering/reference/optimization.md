# Data Optimization - Performance & Cost

Optimize tables for query performance and storage efficiency.

## Liquid Clustering (Recommended)

```sql
-- Create with clustering
CREATE TABLE catalog.silver.orders (
    order_id STRING,
    customer_id STRING,
    order_date DATE
) CLUSTER BY (customer_id, order_date);

-- Convert existing table
ALTER TABLE catalog.silver.orders CLUSTER BY (customer_id, order_date);

-- Auto-optimized on writes
```

## File Compaction

```sql
-- Compact small files
OPTIMIZE catalog.silver.orders;

-- Optimize specific partition
OPTIMIZE catalog.silver.orders
WHERE order_date >= '2024-01-01';

-- Enable auto-optimization
ALTER TABLE catalog.silver.orders SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
```

## Storage Cleanup

```sql
-- Remove old file versions (preserves time travel)
VACUUM catalog.silver.orders RETAIN 168 HOURS;  -- 7 days

-- Shallow clone for testing (metadata only)
CREATE TABLE catalog.dev.orders_test SHALLOW CLONE catalog.prod.orders;
```

## Query Performance

```python
# Enable Photon
spark.conf.set("spark.databricks.photon.enabled", "true")

# Partition pruning
df = spark.read.table("catalog.silver.events") \
    .filter(col("event_date").between("2024-10-01", "2024-10-31"))

# Column pruning (read only needed columns)
df = spark.read.table("catalog.silver.events") \
    .select("event_id", "user_id", "event_timestamp")
```

