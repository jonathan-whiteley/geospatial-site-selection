"""FastAPI entry point for Geospatial Retail Site Selection app."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import health, stores, expansion, optimization, metrics, init

# Initialize FastAPI app
app = FastAPI(
    title="Geospatial Retail Site Selection API",
    description="API for retail site selection with expansion analysis and optimization",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Databricks Apps
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api")
app.include_router(init.router, prefix="/api")  # Consolidated initial load endpoint
app.include_router(stores.router, prefix="/api")
app.include_router(expansion.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")

# Determine frontend build path
FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    from core.config import get_settings
    settings = get_settings()
    print("=" * 60)
    print("GEOSPATIAL RETAIL SITE SELECTION API")
    print("=" * 60)
    print(f"Server Hostname: {settings.databricks_server_hostname}")
    print(f"Catalog: {settings.databricks_catalog}")
    print(f"Auth Type: {'Service Principal' if settings.is_service_principal else 'PAT Token'}")
    print(f"Frontend Build: {FRONTEND_BUILD_DIR}")
    print(f"Frontend Exists: {FRONTEND_BUILD_DIR.exists()}")
    print("=" * 60)


# Mount static assets if they exist
assets_dir = FRONTEND_BUILD_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    favicon_path = FRONTEND_BUILD_DIR / "favicon.png"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/png")
    logo_path = FRONTEND_BUILD_DIR / "logo.png"
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/logo.png")
async def logo():
    """Serve logo."""
    logo_path = FRONTEND_BUILD_DIR / "logo.png"
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/")
async def root():
    """Serve the React SPA index.html or fallback message."""
    index_path = FRONTEND_BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {
        "message": "Geospatial Retail Site Selection API",
        "docs": "/api/docs",
        "health": "/api/health",
        "note": "Build frontend with 'cd frontend && npm run build' to serve the UI"
    }


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the React SPA for all non-API routes."""
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

    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
