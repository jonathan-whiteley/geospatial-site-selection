# Geospatial Retail Site Selection - React + FastAPI App

A modern React frontend with FastAPI backend for retail site selection and expansion analysis.

## Architecture

- **Backend**: FastAPI (Python) with Databricks SQL connector
- **Frontend**: React + Vite + Tailwind CSS + react-leaflet
- **Auth**: Service Principal (Databricks Apps) or PAT (local development)
- **Map Features**: Isochrones, marker clustering, trade area analysis, optimization

## Project Structure

```
react-app/
├── main.py                    # FastAPI entry point
├── app.yaml                   # Databricks Apps config
├── requirements.txt           # Python dependencies
├── api/routes/                # API endpoints
│   ├── health.py              # Health check
│   ├── init.py                # Consolidated initial data load (parallel queries)
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
| `/api/init` | GET | **Consolidated initial load** (parallel queries, pre-computed ranges) |
| `/api/stores/current` | GET | Current stores |
| `/api/stores/isochrones` | GET | LCE trade areas |
| `/api/stores/partners` | GET | Partner store isochrones |
| `/api/stores/competitors` | GET | Competitor locations |
| `/api/stores/network` | GET | All network data |
| `/api/expansion/candidates` | GET | Expansion candidates (filterable) |
| `/api/expansion/data` | GET | All expansion data |
| `/api/optimization/results` | GET | Pre-computed grid |
| `/api/optimization/lookup` | POST | Lookup specific params |
| `/api/metrics/network` | GET | Aggregate metrics |

> **Performance:** The `/api/init` endpoint uses `ThreadPoolExecutor` to run 6 database queries in parallel with thread-local connections, significantly reducing initial load time.

## Features

### Sidebar Tabs
- **Overview Tab**: Expansion metrics, filter controls, layer toggles, partnership recommendations
- **Chat Tab**: AI assistant placeholder for future conversational analytics

### Left Panel Sections
- **Map Layers**: Toggle visibility for network and expansion layers
- **Expansion Metrics**: Population and sales distribution charts
- **Filter Candidates**: Filter by sales, population, fulfillment strategy, quality tier
- **Partnership Recommendations**: Identify partner vs greenfield opportunities

### Map Layers
- **Current Stores** (green markers) - Existing store locations
- **Expansion Candidates** (red, clustered) - AI-scored opportunity areas
- **Candidate Trade Areas** - 5-minute drive-time circles with sales-based gradient (darker = higher predicted sales)
- **Store Trade Areas** (green) - LCE isochrones showing current coverage
- **Partner Isochrones** (blue) - Partner store coverage areas
- **Competitor Locations** (purple markers) - Competitor stores

## Data Requirements

The app expects the following tables in Unity Catalog:

**Gold Layer** (`geo_gold`):
- `viz_existing_stores` - Current store locations with sales and POI data
- `viz_expansion_candidates` - H3 cells with ML-predicted sales, demographics
- `viz_partners` - Partner store data with isochrones
- `viz_competitors` - Competitor locations
- `viz_optimization_results` - Pre-computed optimization (27 parameter combinations)
- `viz_network_metrics` - Aggregate network KPIs

**Silver Layer** (`geo_silver`):
- `isochrones_lce` - Store trade area polygons (5-minute drive-time)

**Bronze Layer** (`geo_bronze`):
- `census_states` - State boundary geometries (for MA outline)

## Performance Optimizations

- **Consolidated API**: Single `/api/init` endpoint reduces frontend API calls from 3+ to 1
- **Parallel Queries**: ThreadPoolExecutor runs 6 database queries concurrently
- **Thread-Local Connections**: Each thread gets its own Databricks SQL connection
- **Pre-computed Ranges**: Sales/population min/max calculated server-side (avoids O(n) frontend loops)
- **Connection Pooling**: OAuth token cached and shared across threads

See `docs/PERFORMANCE_OPTIMIZATION_PLAN.md` for the full optimization roadmap.
