Create a plan to do the following

- Update Current Stores Metrics cards (4) to show: Current Stores, Current Stores - Total Annual Sales (this is sum of actual sales for all current stores), Convenience Stores, Competitor Stores
- Replace the layer controls as well as map output we have on the Existing tab with those on the Expansion tab. Add the Expansion Metrics below Current Stores Metrics on left side panel. The map should be the same on both tabs. Expansion tab should have Refine and Optimize sections still but those should not be included in Existing tab
- Dont include isochrones from existing stores outside of MA on both tabs, look into why only 12 MA stores are showing up instead of 13
- If Expansion Candidates layer is checked off, dont remove the H3 hexagons from the map, just hide the markers and clustering
- Have the right side panel display current store annual sales
- include clusters for current stores with total actual sales as the cluster value
- create a layer control for displaying the candidate store isochrones, using a lighter red color (off by default)
- make sure the candidate store gradient adapts to the filters candidates ie the min and max values change based on the filters

  LATER

  - expand POIs to include name LIKE 'Walmart' or 'Walmart Supercenter', 'Shaw's' , ensure we keep subcategory in viz layer table
  - rename to pois_partners instead of pois_convenience
  - isochrones_partners instead of isochrones_convenience

APP
Update app to React/Vite and FASTAPI backend, use Ashwins md and the repo/styling from Brian Store Ops app
