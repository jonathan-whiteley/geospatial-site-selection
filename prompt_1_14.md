Agg notebooks (AFTER ISOCRONES)
  - agg_h3_features_current_stores - Find all H3 cells whose centers fall inside the 5-min isochrone (polyfill), Match that list of h3_ids against clean_h3_features with inner join, aggregate by store
  - agg_h3_features_candidates - Find all H3 cells use krings to approximate 5 min drive based on urbanity, Match that list of h3_ids against clean_h3_features with inner join 
  - make sure Distance-to-Nearest-Store is a feature
  
  




  LATER
  - expand POIs to include name LIKE 'Walmart' or 'Walmart Supercenter', 'Shaw's' , ensure we keep subcategory in viz layer table 
  - rename to pois_partners instead of pois_convenience
  - isochrones_partners instead of isochrones_convenience

APP
  Update app to React/Vite and FASTAPI backend, use Ashwins md and the repo/styling from Brian Store Ops app