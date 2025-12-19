-- Drop corrupted Gold tables to force clean recreation
DROP TABLE IF EXISTS jdub_demo_aws.geo_gold.lce_trade_area_features;
DROP TABLE IF EXISTS jdub_demo_aws.geo_gold.lce_expansion_candidates;

-- Optionally, also drop and recreate the Silver isochrone table if issues persist
-- DROP TABLE IF EXISTS jdub_demo_aws.geo_silver.lce_isochrones_5min;

-- You can run this SQL in Databricks SQL Editor or in a notebook cell with:
-- spark.sql("DROP TABLE IF EXISTS jdub_demo_aws.geo_gold.lce_trade_area_features")
-- spark.sql("DROP TABLE IF EXISTS jdub_demo_aws.geo_gold.lce_expansion_candidates")
