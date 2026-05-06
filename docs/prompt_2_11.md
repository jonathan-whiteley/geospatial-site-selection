Create a plan (put in /docs folder) to create a simple standalone Databricks data science notebook to show the major steps being taken in the transformation pipeline / do some EDA leading up to the prediction model 

Theres something wrong with our model/aggregation steps and i want to use this to pinpoint what could be issue.  It should bring in the necessary bronze/silver tables and step through what the other notebooks are doing in GOLD layer to help troubleshoot without too much complexity. It should not include all the partner poi details or anything that is just for the app frontend, it should be focused on just the Current Stores (across 7 states) features and actual sales for training data and Predicting sales in candidate whitespace locations in MA.

It should be able to be run seperate from the existing pipeline, in a new /explorations folder. It should have all the parameters dbutils defaults and package imports needed accounted for in the notebook itself so we can run interactively and change as needed.

Key Sections

0. start with current_stores_raw, annual sales 
1. Create Trade Areas (this is handled in the isochrone notebooks already so just importing the isochrone tables, isochrones_lce and candidate_isochrones )
2. Aggregate Data at the H3 Level (this should also already be handled since we have the CARTO dataset with h3 level features, h3_features_clean)

I WANT TO MAKE SURE THESE NEXT steps are correct, so show prints/displays along the way for the dataframes created, no need to create/save any tables, 

3. Enrich Trade Areas - 
-  Index Trade Areas: Use the native H3 tessellate/polyfill function to generate H3 spatial indices for the newly created trade areas (from Step 1).
- Perform Enrichment: Execute a standard inner join and apply necessary aggregations to enrich your Little Caesars trade areas with the pre-processed data from the H3 hexes (from Step 2). 
- Seperate step for aggregating by store to see how that looks
- consider if showing a folium map quickly to understand how many h3 cells are being aggregated into a store_id too
- any additional features that are added (like distance features)
4. Creating a Prediction Model for expansion candidates in MA
- correlations for features
- lets normalize features by population
- lets explore not using log transform (is another approach needed for XGBoost to get between 0-1?)
- lets try a few different models - linear regress , XGBOOST, random forest
- use mlflow best practices to create a different experiment than the pipeline does and log the different models and performance for easy comparison 

Anything else that is done in the agg_ notebooks or predict_candidate notebook that could warrant verification, include in this standalone notebook. 
