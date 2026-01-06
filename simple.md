1. Upload pois_convenience

2. Run isochrone notebook 
- pois_convenience
- lce_locations_mass
- harcode in census_states geometry

3. can we create a notebook in the exploration folder
  that does the following:
  1. takes input of three tables that are specified in dbutils parameters in notebook cell
  - convenience locations table = poi_convenience
  - lce locations table = lce_locations_mass
  - carto h3 features = 
  2. copies functionality of @transformations/02_silver/create_isochrones.ipynb to output as delta tables from specificed output catalog and schema dbutils parameters
  - isochrones_convenience
  - isochrones_lce

3. visualize with folium
- use the map styling like the app.py uses
- use the jupyter/databricks notebook python only approach for marker clustering
- # GREEN clusters for LCE stores
- # BLUE clusters for convenience stores
- no need for toggles or competitor data or anything too extra



Existing stores
- Lat/Long , polygon of isochrone, Actual annual Sales, address, city, state
-- rolled up from H3 level: # of POIs, population,

Convenience stores
- Lat/Long , polygon of isochrone, address, city, state

Candidate locations
- H3 id, # of POIs, population, city, state, predicted annual sales, 

Competitors
- Lat/Long, address, city, state


