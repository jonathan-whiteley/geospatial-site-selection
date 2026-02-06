# Databricks Apps: React + FastAPI Best Practices

> An opinionated guide for building production-quality Databricks Apps with React (Vite) frontends and FastAPI backends. Distilled from real-world learnings.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [FastAPI Backend](#2-fastapi-backend)
3. [React Frontend](#3-react-frontend)
4. [Databricks Integration](#4-databricks-integration)
5. [Deployment](#5-deployment)
6. [Performance Optimization](#6-performance-optimization)
7. [Common Pitfalls](#7-common-pitfalls)
8. [Reusable Patterns](#8-reusable-patterns)

---

## 1. Project Structure

### Recommended Layout

```
my-databricks-app/
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py          # Health check endpoint
│       ├── init.py            # Consolidated initial load
│       └── [feature].py       # Feature-specific routes
├── core/
│   ├── __init__.py
│   ├── config.py              # Environment configuration
│   └── database.py            # Databricks SQL connection
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic models
├── services/
│   └── data_service.py        # Business logic layer
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API client functions
│   │   └── lib/               # Utility functions
│   ├── dist/                  # Production build (COMMIT THIS!)
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── main.py                    # FastAPI entry point
├── app.yaml                   # Databricks App manifest
├── requirements.txt           # Python dependencies
└── .env.example               # Environment template
```

### Key Principles

- **Separation of concerns**: API routes → Services → Database
- **Commit `dist/`**: Databricks Apps don't run `npm build` for you
- **Environment-driven config**: Never hardcode credentials

---

## 2. FastAPI Backend

### Entry Point (`main.py`)

```python
"""FastAPI entry point for Databricks App."""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import health, init, feature

# Initialize FastAPI with API docs under /api prefix
app = FastAPI(
    title="My Databricks App API",
    version="1.0.0",
    docs_url="/api/docs",           # Swagger UI
    redoc_url="/api/redoc",         # ReDoc
    openapi_url="/api/openapi.json" # OpenAPI schema
)

# CORS middleware - required for Databricks Apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # Databricks Apps use same-origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers - ALWAYS with /api prefix
app.include_router(health.router, prefix="/api")
app.include_router(init.router, prefix="/api")
app.include_router(feature.router, prefix="/api")

# Frontend build directory
FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"

# Mount static assets BEFORE catch-all route
assets_dir = FRONTEND_BUILD_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Serve static files (favicon, logos)
@app.get("/favicon.ico")
async def favicon():
    path = FRONTEND_BUILD_DIR / "favicon.png"
    if path.exists():
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404)

# Serve React SPA root
@app.get("/")
async def root():
    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"message": "API running", "docs": "/api/docs"}

# SPA catch-all route - serves index.html for client-side routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Don't serve for API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    # Check if file exists in dist
    file_path = FRONTEND_BUILD_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Otherwise, serve index.html for SPA routing
    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")

    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Configuration (`core/config.py`)

```python
"""Environment configuration with Service Principal support."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    """Application settings from environment variables."""

    # Databricks connection
    databricks_server_hostname: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""              # Local dev only
    databricks_client_id: str = ""          # Service Principal
    databricks_client_secret: str = ""      # Service Principal

    # Catalog and schemas (Unity Catalog)
    databricks_catalog: str = "main"
    databricks_schema: str = "default"

    def __post_init__(self):
        """Load values from environment."""
        self.databricks_server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "")
        self.databricks_http_path = os.getenv("DATABRICKS_HTTP_PATH", "")
        self.databricks_token = os.getenv("DATABRICKS_TOKEN", "")
        self.databricks_client_id = os.getenv("DATABRICKS_CLIENT_ID", "")
        self.databricks_client_secret = os.getenv("DATABRICKS_CLIENT_SECRET", "")
        self.databricks_catalog = os.getenv("DATABRICKS_CATALOG", "main")
        self.databricks_schema = os.getenv("DATABRICKS_SCHEMA", "default")

    @property
    def is_service_principal(self) -> bool:
        """Check if running with Service Principal auth."""
        return bool(self.databricks_client_id and self.databricks_client_secret)

    @property
    def table_prefix(self) -> str:
        """Fully qualified table prefix."""
        return f"{self.databricks_catalog}.{self.databricks_schema}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Database Connection (`core/database.py`)

```python
"""Databricks SQL connection with thread-safe connection pooling."""
import threading
from contextlib import contextmanager
from typing import Generator, Any

import pandas as pd
from databricks import sql as dbsql
from databricks.sdk.core import Config

from core.config import get_settings


class DatabricksDB:
    """Database manager with thread-local connections for parallel queries."""

    def __init__(self):
        self.settings = get_settings()
        self._config = None
        self._config_lock = threading.Lock()
        self._thread_local = threading.local()

    def _get_config(self) -> Config:
        """Get or create Config for OAuth auth (thread-safe)."""
        if self._config is None:
            with self._config_lock:
                if self._config is None:
                    # Config auto-detects credentials in Databricks Apps
                    self._config = Config()
        return self._config

    def _create_connection(self) -> Any:
        """Create a new database connection."""
        cfg = self._get_config()
        return dbsql.connect(
            server_hostname=cfg.host,
            http_path=self.settings.databricks_http_path,
            credentials_provider=lambda: cfg.authenticate,
            _use_arrow_native_complex_types=False
        )

    def _get_thread_connection(self) -> Any:
        """Get or create connection for current thread."""
        if not hasattr(self._thread_local, 'connection') or \
           self._thread_local.connection is None:
            self._thread_local.connection = self._create_connection()
        return self._thread_local.connection

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Context manager for database connections."""
        try:
            yield self._get_thread_connection()
        except Exception as e:
            # Invalidate connection on error
            if hasattr(self._thread_local, 'connection'):
                self._thread_local.connection = None
            raise

    def execute_query(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL and return DataFrame."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                return pd.DataFrame(data, columns=columns)


# Singleton instance
_db_instance = None

def get_db() -> DatabricksDB:
    """Get singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabricksDB()
    return _db_instance
```

### Health Check (`api/routes/health.py`)

```python
"""Health check endpoint - essential for monitoring."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import get_settings
from core.database import get_db


class HealthResponse(BaseModel):
    status: str
    database: str
    auth_type: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and database connectivity."""
    settings = get_settings()
    db = get_db()

    auth_type = "service_principal" if settings.is_service_principal else "pat_token"

    try:
        df = db.execute_query("SELECT 1 as test")
        db_status = "connected" if not df.empty else "no_data"
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

    return HealthResponse(status="healthy", database=db_status, auth_type=auth_type)
```

### Pydantic Models (`models/schemas.py`)

```python
"""Pydantic models for API request/response schemas."""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """Base model with common fields."""
    id: str
    name: str
    latitude: float
    longitude: float


class ItemResponse(ItemBase):
    """Response model with computed fields."""
    score: Optional[float] = None
    metadata: Optional[dict] = None


class ListResponse(BaseModel):
    """Paginated list response."""
    items: List[ItemResponse]
    total: int
    page: int = 1
    page_size: int = 100


class FilterParams(BaseModel):
    """Common filter parameters."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    category: Optional[str] = None
```

### Requirements (`requirements.txt`)

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
databricks-sql-connector>=3.0.0
databricks-sdk>=0.17.0
pandas>=2.0.0
python-dotenv>=1.0.0
httpx>=0.25.0
```

---

## 3. React Frontend

### Vite Configuration (`frontend/vite.config.js`)

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/',  // Critical for Databricks Apps
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,  // Disable for production
  },
})
```

### Package.json

```json
{
  "name": "my-databricks-app-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint . --ext js,jsx",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "clsx": "^2.0.0",
    "lucide-react": "^0.294.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "tailwind-merge": "^2.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.53.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "postcss": "^8.4.31",
    "tailwindcss": "^3.3.5",
    "vite": "^5.0.0"
  }
}
```

### Tailwind Configuration (`frontend/tailwind.config.js`)

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors
        brand: {
          primary: '#3b82f6',
          'primary-dark': '#2563eb',
          secondary: '#10b981',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### PostCSS Configuration (`frontend/postcss.config.js`)

```javascript
// Keep it simple - avoid @tailwindcss/postcss for v3
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### API Client (`frontend/src/services/api.js`)

```javascript
import axios from 'axios'

// API client with /api prefix
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health check
export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

// Initial data load - single endpoint pattern
export async function getInitialData() {
  const response = await api.get('/init')
  return response.data
}

// Feature-specific endpoints
export async function getItems(filters = {}) {
  const params = new URLSearchParams()
  if (filters.minValue) params.append('min_value', filters.minValue)
  if (filters.maxValue) params.append('max_value', filters.maxValue)
  if (filters.category) params.append('category', filters.category)

  const response = await api.get(`/items?${params.toString()}`)
  return response.data
}

export async function createItem(data) {
  const response = await api.post('/items', data)
  return response.data
}

export default api
```

### Custom Hook Pattern (`frontend/src/hooks/useData.js`)

```javascript
import { useState, useEffect, useCallback } from 'react'
import { getInitialData } from '../services/api'

export function useData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await getInitialData()
      setData(result)
    } catch (err) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  return {
    data,
    loading,
    error,
    refresh: loadData,
  }
}
```

### Component Structure

```
src/
├── components/
│   ├── layout/           # Page layout components
│   │   ├── AppLayout.jsx
│   │   ├── Sidebar.jsx
│   │   └── Header.jsx
│   ├── ui/               # Reusable UI components
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   └── LoadingSpinner.jsx
│   ├── features/         # Feature-specific components
│   │   └── Dashboard/
│   └── panels/           # Slide-out panels, modals
├── hooks/                # Custom React hooks
├── services/             # API client functions
├── lib/                  # Utilities (cn, formatters)
└── App.jsx               # Root component
```

### Utility Functions (`frontend/src/lib/utils.js`)

```javascript
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Merge Tailwind classes safely
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

// Format currency
export function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

// Format large numbers
export function formatNumber(value) {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
  return value.toString()
}
```

---

## 4. Databricks Integration

### App Manifest (`app.yaml`)

```yaml
command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  - name: DATABRICKS_SERVER_HOSTNAME
    value: your-workspace.cloud.databricks.com
  - name: DATABRICKS_HTTP_PATH
    value: /sql/1.0/warehouses/your-warehouse-id
  - name: DATABRICKS_CATALOG
    value: your_catalog
  - name: DATABRICKS_SCHEMA
    value: your_schema
```

### Service Principal Authentication

Databricks Apps automatically inject `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`. The `databricks.sdk.core.Config()` class auto-detects these.

```python
from databricks.sdk.core import Config

# In Databricks Apps - credentials injected automatically
cfg = Config()
print(f"Host: {cfg.host}")
print(f"Auth type: {cfg.auth_type}")  # "oauth-m2m" for Service Principal
```

### Local Development

Create a `.env` file (add to `.gitignore`):

```bash
# .env
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your-personal-access-token
DATABRICKS_CATALOG=your_catalog
DATABRICKS_SCHEMA=your_schema
```

Load with `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

---

## 5. Deployment

### Build Workflow

1. **Local development**:
   ```bash
   # Terminal 1: Backend
   cd my-app
   uvicorn main:app --reload --port 8000

   # Terminal 2: Frontend
   cd my-app/frontend
   npm run dev
   ```

2. **Build frontend**:
   ```bash
   cd frontend
   npm run build
   ```

3. **Commit `dist/`**:
   ```bash
   git add frontend/dist -f
   git commit -m "Update frontend build"
   git push
   ```

4. **Deploy in Databricks**:
   - Sync repo in Databricks Repos
   - Go to Apps → Create/Update
   - Select your repo and `app.yaml`
   - Deploy

### CI/CD with GitHub Actions

```yaml
name: Build & Deploy
on:
  push:
    branches: [main]
    paths:
      - 'frontend/src/**'
      - 'frontend/package.json'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 18

      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build

      - name: Commit build
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add frontend/dist -f
          git commit -m "Build frontend [skip ci]" || echo "No changes"
          git push
```

---

## 6. Performance Optimization

### Backend: Consolidated Endpoints

Reduce round-trips with a single initial load endpoint:

```python
@router.get("/init")
async def get_initial_data():
    """Load all app data in one request."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(load_items): 'items',
            executor.submit(load_config): 'config',
            executor.submit(load_metadata): 'metadata',
        }

        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    return {
        'items': results['items'],
        'config': results['config'],
        'metadata': results['metadata'],
    }
```

### Backend: Thread-Local Connections

Enable parallel query execution with thread-local DB connections (see `core/database.py` above).

### Frontend: Viewport-Based Filtering

Only render items visible in the current viewport:

```javascript
const visibleItems = useMemo(() => {
  return filterByBounds(allItems, mapBounds)
}, [allItems, mapBounds])
```

### Frontend: Pre-Computed Ranges

Compute min/max ranges on the backend:

```python
# Backend
return {
    'items': items,
    'ranges': {
        'price': {'min': min(prices), 'max': max(prices)},
        'quantity': {'min': min(quantities), 'max': max(quantities)},
    }
}
```

```javascript
// Frontend - no O(n) iteration needed
const { items, ranges } = data
```

---

## 7. Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Old UI after deploy | `dist/` not committed | Run `npm run build` and commit `dist/` |
| 404 on JS/CSS | Wrong Vite `base` path | Set `base: '/'` in `vite.config.js` |
| CORS errors in dev | Missing proxy | Add `/api` proxy in Vite config |
| Blank page | HTML cached | Hard refresh (`Cmd+Shift+R`) |
| API not found | Mount order wrong | Mount static files AFTER API routes |
| Auth fails in App | Missing env vars | Check `app.yaml` has all env vars |
| Slow initial load | Multiple API calls | Use single `/init` endpoint |
| Tailwind styles missing | Build error or config | Check terminal, restart Vite, verify config |

---

## 8. Reusable Patterns

### Pattern: Loading/Error States

```jsx
function DataComponent() {
  const { data, loading, error } = useData()

  if (loading) return <LoadingSpinner message="Loading..." />
  if (error) return <ErrorDisplay error={error} />

  return <DataView data={data} />
}
```

### Pattern: Feature Router

```python
# api/routes/__init__.py
from .health import router as health_router
from .init import router as init_router
from .feature import router as feature_router

__all__ = ['health_router', 'init_router', 'feature_router']
```

### Pattern: Barrel Exports

```javascript
// components/index.js
export { Button } from './Button'
export { Card } from './Card'
export { LoadingSpinner } from './LoadingSpinner'
```

### Pattern: Environment Detection

```python
import os

def is_databricks_app() -> bool:
    """Check if running inside Databricks Apps."""
    return bool(os.environ.get('DATABRICKS_CLIENT_ID'))
```

---

## Quick Reference

### Startup Checklist

- [ ] Create project structure
- [ ] Set up FastAPI with `/api` prefix
- [ ] Configure Vite with `base: '/'` and proxy
- [ ] Add health check endpoint
- [ ] Set up database connection with thread-local pools
- [ ] Create Pydantic schemas
- [ ] Build frontend with `npm run build`
- [ ] Commit `dist/` to repo
- [ ] Create `app.yaml` with env vars
- [ ] Deploy and test

### Debug Checklist

1. Check `/api/health` returns `200`
2. Check `dist/` exists and is current (`ls -la frontend/dist`)
3. Check browser DevTools Network tab (disable cache)
4. Check Databricks App logs for errors
5. Verify env vars in `app.yaml`
6. Click **Restart** in Databricks Apps UI

---

*Last updated: January 2025*
