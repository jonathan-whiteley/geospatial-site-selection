# Structured Streaming - Real-Time Processing

Real-time data processing with Structured Streaming and Auto Loader.

## Auto Loader

```python
df = spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "json") \
    .option("cloudFiles.schemaLocation", "/mnt/checkpoints/schema") \
    .option("cloudFiles.inferColumnTypes", "true") \
    .option("cloudFiles.useNotifications", "true") \
    .load("/mnt/landing/events/")

df.writeStream.format("delta") \
    .option("checkpointLocation", "/mnt/checkpoints/events") \
    .toTable("catalog.bronze.events")
```

## Watermarks & Late Data

```python
df = spark.readStream.table("catalog.bronze.events") \
    .withWatermark("event_timestamp", "1 hour") \
    .groupBy(window("event_timestamp", "10 minutes"), "event_type") \
    .agg(count("*").alias("count"))
```

## Stream-Stream Joins

```python
events = spark.readStream.table("catalog.bronze.events") \
    .withWatermark("event_timestamp", "2 hours")

clicks = spark.readStream.table("catalog.bronze.clicks") \
    .withWatermark("click_timestamp", "2 hours")

joined = events.join(clicks,
    expr("events.user_id = clicks.user_id AND " +
         "events.event_timestamp >= clicks.click_timestamp AND " +
         "events.event_timestamp <= clicks.click_timestamp + interval 1 hour"))
```

