# Implementation Plan - Streamlit to React + FastAPI Migration

## Goal Description

Migrate the existing Geospatial Retail Site Selection Streamlit application to a React (Vite) frontend served by a FastAPI backend, adhering to Databricks deployment guidelines. The goal is to decouple the architecture, maintain core functionality (map, logo, analysis), and improve the user experience with a modern frontend.

## User Review Required

> [!IMPORTANT]
>
> - **Source of Truth**: `app/app_v2.py` will be used as the reference implementation.
> - **Map Library**: We will use `react-leaflet` to maintain compatibility with the existing Leaflet logic and `markercluster` usage in `app_v2.py`.
> - **Styling**: We will migrate the custom CSS in `app_v2.py` to Tailwind CSS + Shadcn/UI components.

## References

- [Databricks Apps Cookbook: Building Endpoints (Tables Read)](https://apps-cookbook.dev/docs/fastapi/building_endpoints/tables_read)

## Inefficiencies of Current Implementation (To Address)

> [!WARNING]
> The current `app_v2.py` has several performance bottlenecks that should be addressed during migration:
>
> 1.  **Runtime Optimization Loop**: `run_optimization` (lines 374-405) performs an O(N\*M) distance calculation loop in Python. This is extremely slow for large datasets. **Fix**: Move distance logic to H3/PostGIS queries in Databricks SQL.
> 2.  **Blocking Data Loads**: All data (`viz_existing_stores`, `viz_convenience`, etc.) is loaded into memory at startup, causing slow cold starts. **Fix**: Implement lazy loading or pagination for map bounds.
> 3.  **Memory Usage**: Loading full datasets into Pandas DataFrames and serializing to JSON can cause OOM errors. **Fix**: Query only required columns/rows based on viewport or filters.
> 4.  **Manual Token Handling**: Uses `os.getenv("DATABRICKS_TOKEN")` directly. **Fix**: Use Service Principal via `SDK` or standard env injection.

## Proposed Changes

### Project Structure

#### [NEW] `my-app` (New Root Directory)

- `backend/`: Python FastAPI code
- `frontend/`: React Vite code
- `app.yaml`: Databricks App Manifest
- `.env`: Environment variables (migrated from `app/.env` if exists)

### Frontend (React + Vite)

#### [NEW] `frontend/`

- Initialize with `npm create vite@latest`
- Install Tailwind CSS, Shadcn/UI
- **Components**:
  - `Dashboard`: Main layout
  - `Sidebar`: Filters and controls
  - `MapComponent`: Geospatial visualization
  - `StatsPanel`: Data metrics
- **Styling**:
  - Port styles from `retail1-dashboard` references (if available) or create a "Retail App" look.
  - Ensure Logo (`Little-Caesars-man-logo.png`) is included.

### Backend (FastAPI)

#### [NEW] `backend/`

#### [NEW] `backend/`

- `app.py`: FastAPI entry point
- **Authentication**:
  - Use **Service Principal** identity automatically injected by Databricks Apps.
  - **Implementation**: initialization via `WorkspaceClient()` or `databricks.sql.connect()` using environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN` - automatically set).
  - _Reference_: See linked Cookbook article.
- **Endpoints** (Ported from `app_v2.py`):
  - `GET /api/current-network`: Returns `viz_existing_stores`, `viz_convenience`, `viz_competitors`.
  - `GET /api/expansion-candidates`: Returns `viz_expansion_candidates`.
  - `GET /api/optimization-results`: Returns `viz_optimization_results` (pre-computed).
  - `GET /api/network-metrics`: Returns `viz_network_metrics`.
  - `POST /api/optimize`: (Optional) Runtime optimization if pre-computed results are missing (logic from `run_optimization`).
- **Static files**:
  - Mount `frontend/dist` to `/`

### Migration Logic

- **State**: `st.session_state` -> React `useState`/`Context`
  - `tab`: "Current Network" | "Expansion Candidates" | "Network Optimizer"
  - `data_loaded`: Loading states
- **Interactions**:
  - Checkboxes: "Show Isochrones", "Show Competitors", etc.
  - Sliders: "Catchment Radius", "Max Stores", etc.
- **Data**: Pandas logic -> FastAPI endpoints using `databricks.sql`
- **Assets**:
  - `Little-Caesars-man-logo.png` -> Move to `frontend/public/` or serve via API.

## Verification Plan

### Automated Tests

- `npm run build` to verify frontend build
- Local FastAPI run to valid API responses and static serving

### Manual Verification

- Verify Map renders correctly with data
- Verify filters update the map and stats
- Verify Logo is present
- Verify deployment to Databricks Apps (or simulating the environment)
