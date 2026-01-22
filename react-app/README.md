# Geospatial Retail Site Selection - React + FastAPI App

A modern React frontend with FastAPI backend for retail site selection and expansion analysis.

## Architecture

- **Backend**: FastAPI (Python) with Databricks SQL connector
- **Frontend**: React + Vite + Tailwind CSS + react-leaflet
- **Auth**: Service Principal (Databricks Apps) or PAT (local development)
- **Map Features**: H3 hexagons, isochrones, marker clustering, optimization

## Project Structure

```
react-app/
├── main.py                    # FastAPI entry point
├── app.yaml                   # Databricks Apps config
├── requirements.txt           # Python dependencies
├── api/routes/                # API endpoints
│   ├── health.py              # Health check
│   ├── stores.py              # Store data endpoints
│   ├── expansion.py           # Expansion candidates
│   ├── optimization.py        # Optimization lookup
│   └── metrics.py             # Network metrics
├── core/
│   ├── config.py              # Environment configuration
│   └── database.py            # Databricks SQL connection
├── models/
│   └── schemas.py             # Pydantic models
├── services/
│   └── data_service.py        # Business logic
└── frontend/
    ├── package.json           # Node dependencies
    ├── vite.config.js         # Vite configuration
    ├── tailwind.config.js     # Tailwind configuration
    └── src/
        ├── App.jsx            # Main React component
        ├── components/        # React components
        ├── hooks/             # Custom React hooks
        ├── services/          # API client
        └── lib/               # Utilities
```

## Development Setup

### Backend

1. Create a Python virtual environment:
   ```bash
   cd react-app
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (copy from .env.example):
   ```bash
   export DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
   export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
   export DATABRICKS_TOKEN=your-personal-access-token
   ```

4. Start the backend:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend

1. Install Node dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open http://localhost:5173 in your browser.

## Building for Production

1. Build the frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. The FastAPI server will automatically serve the built files from `frontend/dist/`.

## Deploying to Databricks Apps

1. Ensure the frontend is built (`frontend/dist/` exists)

2. Deploy using the Databricks Apps CLI or UI

3. The app will use Service Principal authentication automatically

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/stores/current` | GET | Current stores |
| `/api/stores/isochrones` | GET | LCE trade areas |
| `/api/stores/convenience` | GET | Convenience isochrones |
| `/api/stores/competitors` | GET | Competitor locations |
| `/api/stores/network` | GET | All network data |
| `/api/expansion/candidates` | GET | Expansion candidates (filterable) |
| `/api/expansion/data` | GET | All expansion data |
| `/api/optimization/results` | GET | Pre-computed grid |
| `/api/optimization/lookup` | POST | Lookup specific params |
| `/api/metrics/network` | GET | Aggregate metrics |

## Features

### Overview Mode
- Current store locations with trade areas
- H3 hexagon demand heatmap
- Store metrics and statistics

### Detail Mode
- Expansion candidate analysis
- Filterable by sales and population
- Optimization with distance constraints
- Partner vs new store recommendations
- CSV export

### Map Layers
- Current stores (green)
- Expansion candidates (red, clustered)
- H3 hexagons with sales gradient
- LCE isochrones (green)
- Convenience isochrones (blue)
- Competitor locations (purple)

## Data Requirements

The app expects the following tables in Unity Catalog:

**Gold Layer** (`geo_gold`):
- `viz_existing_stores` - Current store locations
- `viz_expansion_candidates` - H3 cells with predictions
- `viz_convenience` - Partner store data
- `viz_competitors` - Competitor locations
- `viz_optimization_results` - Pre-computed optimization
- `viz_network_metrics` - Aggregate metrics

**Silver Layer** (`geo_silver`):
- `isochrones_lce` - Store trade area polygons
