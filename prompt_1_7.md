1/7 
- rename bronze notebooks 
  -ingest_census , ingest_pois, ingest_current_stores (include dummy annual sales data for current stores inserted to table for use in model later),
  -ingest_carto_h3 (validate carto marketplace dataset, and move it into bronze)

- rename silver notebooks
  - clean_pois
  - clean_h3_features - filter carto to just state (MA in this case), just relevant feature columns
  - create_isochrones (two tasks, convenience and lce)
  - agg_h3_features_current_stores - Find all H3 cells whose centers fall inside the 5-min isochrone (polyfill), Match that list of h3_ids against clean_h3_features with inner join, aggregate by store
  - agg_h3_features_candidates - Find all H3 cells use krings to approximate 5 min drive based on urbancity, Match that list of h3_ids against clean_h3_features with inner join (make comment that hybrid approach to generate 5 min isochrones for final candidates after using more efficient Krings intially)
- Fix urbanicity logic in silver, there dhould be a column in CARTO dataset dont need to infer with population

- GOLD
- Build a simple, easy to follow Regression Sales model that predicts annual sales for candidate locations at h3 id level using existing store data and features from carto(with MLFlow best practices to register the model) as a seperate task and notebook (called predict_candidates_sales), use output of that model in expansion_candidates 
- rename expansion_prediction to finalize_candidates and remove cannabalization logic (this is accounted for in app optimization)

for any of these changes, suggest changes to table names to created or anything to make more clear/concise