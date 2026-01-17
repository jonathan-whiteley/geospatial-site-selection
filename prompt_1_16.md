Create a plan to implement the app backend and frontend migration plan outlined in detailed_migration_plan.md, modifying if needed for the following resources and references:

- https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth to ensure we are using App service principal authentication NOT PAT token, 
- best practices for databricks apps with FastAPI backend https://apps-cookbook.dev/docs/fastapi/getting_started/create 
- helpful general rules for React frontend in cursor-ai-react-typescript-shadcn-ui-cursorrules-p folder
- more specific rules here: databricks_frontend_deployment.md
- Keep the core Leaflet map, layers, and functionality in the current app_v2.py but i like the front end look and feel, esp the right panel components in this similar map centric React app under @Downloads/bc_nrf_app/bc_nrf_app

Ask for any clarification as you go