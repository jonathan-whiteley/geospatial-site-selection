Create a plan to do the following

- add a new map layer to the app, corresponding to Customer locations (lat/longs) around existing stores
- the markers should be smaller than the existing stores and candidate store markers 
- pins icons perhaps but still look good visually on the map
- the UI side panel should have another slider to turn on/off this layer "Customer Locations" like the other layers (default is off)
- it should be under NETWORK section of panel, in between Current Stores and Expansion Candidates

UNDERLYING DATA
it would be based on an existing table currently at jdub_demo.geo_gold.viz_ma_pins , which    
  has this schema   

DeviceID	Latitude	Longitude	Store
bd3bc91e125bbc76c035ccd04b08bf20efdcae5c	42.776383	-71.105964	1707-0001

col_name	data_type
DeviceID	string
Latitude	double
Longitude	double
Store	string
