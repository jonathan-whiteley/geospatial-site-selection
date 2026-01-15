Create a plan for modifying the following & document the decisions you make and ensure all reference to tables and columns are updated. If you aren't sure about schema of existing input or output table, ask and I can run a DESCRIBE for you

1. Update ingest_current_stores to rename output table current_stores_ne 
- here is what the input table looks like (it includes 83 stores now across MA, CT, NJ, and MD )

col_name	data_type
location_id	int
store_name	string
latitude	decimal(11,6)
longitude	decimal(11,6)
address	string
city	string
state	string
zip_code	string

Add this column along with the sales data
  * Store_Type = 'Current Store'
  * country_code = 'US'

2. Add a notebook in silver, create_whitespace_locations, similar to logic used in @explorations/generate_rmc_retail_locations example
- filter to the top 25% of H3 cells with highest total POI counts (from h3_features_clean)
- Calculate centroids of H3 cells and get geographic context
- use below schema

  Candidate Stores columns
  * location_id - # Start at 999001
  * Store_Type = Expansion Candidate
  * lat/long , address (NA), city (NA), zip_code (NA), state, country_code
  * geo_accuracy --> H3_CENTROID
  * distance_to_nearest_current_store
  * h3_cell_id
  * total_poi_count , population_density,  Urbanity from carto table

3. Add logic in silver create_isochrone notebook to have a task to create isochrones for the whitespace locations (with output as candidate_isochrones), use 5 min drive time for isochrone generation 



