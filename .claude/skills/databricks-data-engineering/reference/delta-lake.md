# Delta Lake - ACID Transactions & Operations

Delta Lake provides ACID guarantees for data lakes.

## MERGE Operations

```python
from delta.tables import DeltaTable

target = DeltaTable.forName(spark, "catalog.silver.customers")

# SCD Type 1: Update existing, insert new
target.alias("t").merge(updates_df.alias("u"), "t.id = u.id") \
    .whenMatchedUpdateAll() \
    .whenNotMatchedInsertAll() \
    .execute()

# SCD Type 2: Track history
target.alias("t").merge(updates_df.alias("u"), "t.id = u.id AND t.is_current = true") \
    .whenMatchedUpdate(set={
        "is_current": "false",
        "end_date": "current_date()"
    }) \
    .whenNotMatchedInsertAll() \
    .execute()
```

## Time Travel

```sql
-- Query historical version
SELECT * FROM catalog.silver.customers VERSION AS OF 100;

-- Query as of timestamp
SELECT * FROM catalog.silver.customers TIMESTAMP AS OF '2024-10-30';

-- Restore to previous version
RESTORE TABLE catalog.silver.customers TO VERSION AS OF 100;
```

## Change Data Feed

```sql
-- Enable CDF
ALTER TABLE catalog.silver.customers
SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- Query changes
SELECT * FROM table_changes('catalog.silver.customers', 100)
WHERE _change_type IN ('insert', 'update_postimage');
```

## Table Constraints

```sql
-- NOT NULL constraint
ALTER TABLE catalog.silver.orders
ADD CONSTRAINT valid_order_id CHECK (order_id IS NOT NULL);

-- Business rule constraint
ALTER TABLE catalog.silver.orders
ADD CONSTRAINT positive_amount CHECK (order_amount > 0);
```

