# Delta Live Tables - Declarative Pipelines

DLT provides declarative ETL with built-in quality checks.

## Basic Pipeline

```python
import dlt
from pyspark.sql.functions import *

@dlt.table(name="bronze_events")
def bronze_events():
    return spark.readStream.format("cloudFiles") \
        .option("cloudFiles.format", "json") \
        .load("/Volumes/catalog/landing/events/")

@dlt.table(name="silver_events")
@dlt.expect_or_drop("valid_id", "event_id IS NOT NULL")
@dlt.expect("valid_timestamp", "event_timestamp IS NOT NULL")
def silver_events():
    return dlt.read_stream("bronze_events") \
        .dropDuplicates(["event_id"])
```

## Data Quality Expectations

```python
# Drop invalid records
@dlt.expect_or_drop("valid_email", "email RLIKE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'")

# Fail pipeline on critical violations
@dlt.expect_or_fail("no_pii", "text NOT RLIKE '\\b\\d{3}-\\d{2}-\\d{4}\\b'")

# Track but don't block
@dlt.expect("reasonable_value", "value >= 0 AND value <= 1000000")

# Multiple checks
@dlt.expect_all({
    "valid_id": "id IS NOT NULL",
    "valid_date": "date >= '2020-01-01'"
})
```

## SCD Type 2 with apply_changes

```python
dlt.create_streaming_table("silver_customers")

dlt.apply_changes(
    target="silver_customers",
    source="customer_updates",
    keys=["customer_id"],
    sequence_by="updated_timestamp",
    stored_as_scd_type="2",
    track_history_column_list=["email", "address", "phone"]
)
```

