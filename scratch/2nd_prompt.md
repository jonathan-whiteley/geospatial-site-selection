Can you recommend how I can adjust it to simplify it, ensure everything is self contained within the pipeline (seperated into medallion stages of bronze, silver, gold), but still achieve functionality like we have in the app currently

APP functionality
- Interactive Map focused on state in question (Massachusetts here)
- Plot existing store network of little caesars stores with current sales
- isochrones to show 5 min drive time area around existing stores
- expansion candidates (cannablization considered)
- network optimizer configurable sliders for revenue and population 

CHANGES:
1. H3 Features (census, demographics, POI)
- Use this marketplace table, aggregated at h3_res 8 level already, as the replacement for the h3_features_gold table
- carto_spatial_features_usa_h3_res_8.carto.derived_spatialfeatures_usa_h3res8_v1_yearly_v3
- here is the schema
- make sure we update the downstream feature metrics to use the relevant ones from this table, not using ones it doesnt have as columns like income_100k_125k, income_125k_150k, income_150k_200k, income_200k_plus, bachelors_degree, masters_degree
- ensure the configs are updated 
- keep the part of the pipeline that gives us the clean poi table and anything that ensures we map the selected state correctly


2. Current Store Footprint
- Use "jdub_demo_aws.geo_bronze.lce_locations_mass" as the current store locations replacing jdub_demo_aws.geo_bronze.rmc_retail_locations_grocery
- create a new config store_config.yml for current store dim table (lce_locations_mass for now) and historical store sales table (help me to indicate required columns here)
- drop all features and requirements related to competitors 

3. Isochrones
- ensure the osrm isochrones for drive time of 5 mins is working properly

4. Clean up the flow as there are tables created and reference from outside the pipeline like in the exploration folder