create a plan and put in docs/ folder for how to implement an AI Feasibility score (1-5 stars, based on candidate location to evaluate each location based on:
  1. Proximity to bodies of water, parks, or green spaces, major highways and accessibility, Visibility from main roads, Physical barriers (railroads, rivers, hills), Nearby landmarks affecting foot traffic
  2. proximity to competitors
- just examples, the prompt can be far simpler 
- Returned a 1-5 feasibility score and 2-sentence rationale

I want to explore how to do this with Grounding with Google Maps and Gemini tool to ensure factual up to date data on each candidate location's lat/long. I want to use Databricks model serving endpoint ideally and then a simpler ai_query call in the app to actually generate the score at runtime 

https://ai.google.dev/gemini-api/docs/maps-grounding

Is this feasible and any changes you would suggest/requirements to be mindful of