# Databricks Apps Frontend Deployment Guide

Best practices for deploying React/Vite frontends to Databricks Apps with FastAPI backend.

---

## Directory Structure

```
project/
├── app/                      # Backend (deployed)
│   ├── main.py              # FastAPI entry point
│   ├── api/                 # API routes (/api/*)
│   ├── core/                # Config, database
│   ├── app.yaml             # Databricks Apps config
│   └── requirements.txt
├── frontend/                 # Frontend source (not deployed directly)
│   ├── src/
│   ├── dist/                # Built output (deployed via FastAPI)
│   ├── package.json
│   └── vite.config.js
└── databricks.yml           # Asset bundle config
```

---

## Key Rules

### 1. Commit `dist/` to Git

Databricks Apps cannot run `npm build` at runtime. Pre-build locally:

```bash
cd frontend
npm run build
git add dist/
git commit -m "Build frontend for deployment"
```

### 2. API Routes First, Static Files Last

In `main.py`, register API routes BEFORE the static file catch-all:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

# 1. API routes (registered first)
app.include_router(health_router, prefix="/api")
app.include_router(stores_router, prefix="/api/stores")
app.include_router(expansion_router, prefix="/api/expansion")

# 2. Static files (registered last)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Serve assets with cache headers
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    # Catch-all for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(frontend_dist / "index.html")
```

### 3. Use `/api` Prefix for OAuth2

Databricks Apps OAuth2 Bearer token auth requires `/api` prefix:

> "In order to use OAuth2 Bearer token authentication with Databricks Apps, your application code must provide valid routes with a prefix of `/api`"

```python
# Correct
app.include_router(stores_router, prefix="/api/stores")

# Incorrect - won't work with OAuth2
app.include_router(stores_router, prefix="/stores")
```

### 4. Vite Build Configuration

**vite.config.js:**
```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Content-hash for cache busting
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  },
  base: '/',  // Root path for Databricks Apps
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 5. Dev Server Proxy

For local development, proxy `/api` to FastAPI:

```js
// vite.config.js
export default defineConfig({
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

Local dev workflow:
```bash
# Terminal 1: FastAPI backend
cd app && uvicorn main:app --reload --port 8000

# Terminal 2: Vite dev server
cd frontend && npm run dev
```

---

## app.yaml Configuration

```yaml
command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
env:
  - name: DATABRICKS_SERVER_HOSTNAME
    value: ${workspace_host}
  - name: DATABRICKS_HTTP_PATH
    value: /sql/1.0/warehouses/your-warehouse-id
  - name: DATABRICKS_CATALOG
    value: your_catalog
  - name: DATABRICKS_GOLD_SCHEMA
    value: your_gold_schema
```

**Notes:**
- No `DATABRICKS_TOKEN` - Service Principal credentials are auto-injected
- `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` are provided by the platform

---

## Service Principal Authentication

The app's service principal credentials are automatically available:

```python
import os
from databricks.sdk.config import Config
from databricks import sql as dbsql

def get_connection():
    # In Databricks Apps environment
    if os.getenv("DATABRICKS_CLIENT_ID"):
        cfg = Config()
        return dbsql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            credentials_provider=lambda: cfg.authenticate
        )
    # Local development with PAT
    return dbsql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    )
```

---

## Deployment Checklist

1. **Build frontend:**
   ```bash
   cd frontend && npm run build
   ```

2. **Verify dist/ contents:**
   ```
   dist/
   ├── index.html
   └── assets/
       ├── index-[hash].js
       └── index-[hash].css
   ```

3. **Commit built files:**
   ```bash
   git add frontend/dist/
   git commit -m "Build frontend"
   ```

4. **Deploy with Asset Bundles:**
   ```bash
   databricks bundle deploy -t production
   ```

5. **Verify endpoints:**
   - `https://your-app.databricks.com/api/health` → 200 OK
   - `https://your-app.databricks.com/` → React app loads

---

## Common Issues

### Issue: API routes return 404
**Cause:** Static file catch-all registered before API routes
**Fix:** Register API routers before `@app.get("/{full_path:path}")`

### Issue: React app shows but API calls fail
**Cause:** Missing `/api` prefix or CORS issues
**Fix:** Ensure all API routes use `/api` prefix, verify proxy config

### Issue: Authentication fails in Databricks Apps
**Cause:** Using PAT token instead of Service Principal
**Fix:** Use `databricks-sdk` `Config()` class for auto-detection

### Issue: Old assets served after deployment
**Cause:** Browser caching
**Fix:** Vite's content-hash filenames handle this; clear browser cache if needed

---

## React-Specific Patterns

### Environment Variables

Access build-time env vars in React:
```js
// vite.config.js
define: {
  'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || '')
}

// In React component
const apiUrl = import.meta.env.VITE_API_URL || '';
fetch(`${apiUrl}/api/stores/current`)
```

### API Client

```js
// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: { 'Content-Type': 'application/json' }
});

export const storeAPI = {
  getCurrentStores: () => api.get('/api/stores/current'),
  getIsochrones: () => api.get('/api/stores/isochrones'),
};
```

### Error Handling

```js
export async function fetchWithFallback(url, fallbackData) {
  try {
    const response = await api.get(url);
    return { success: true, data: response.data };
  } catch (error) {
    console.error(`API error: ${url}`, error);
    return { success: false, data: fallbackData, error: error.message };
  }
}
```
