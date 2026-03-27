"""Pydantic models for API request/response schemas."""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ============================================
# Store Models
# ============================================

class Store(BaseModel):
    """Current store location."""
    store_number: str
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: float
    longitude: float
    population: Optional[float] = 0
    total_poi_count: Optional[int] = 0
    h3_cell_id: Optional[str] = None
    geometry_geojson: Optional[str] = None
    annual_sales: Optional[float] = 0


class Isochrone(BaseModel):
    """Trade area isochrone (drive time polygon)."""
    store_number: Optional[str] = Field(None, alias="location_id")
    isochrone_geojson: str


class PartnerIsochrone(BaseModel):
    """Partner store trade area with candidate info."""
    location_id: str
    isochrone_geojson: str
    candidate_count_in_isochrone: Optional[int] = 0
    total_candidate_sales_in_isochrone: Optional[float] = 0


class PartnerStore(BaseModel):
    """Potential partner store (e.g., convenience stores, Walmart)."""
    name: str
    latitude: float
    longitude: float
    poi_category: Optional[str] = None
    poi_subcategory: Optional[str] = None
    partner_brand: Optional[str] = None  # Normalized brand: "Walmart", "7-Eleven/Speedway", "Shaw's"


# Backward compatibility aliases (deprecated)
ConvenienceIsochrone = PartnerIsochrone
ConvenienceStore = PartnerStore


class Competitor(BaseModel):
    """Competitor store location."""
    name: str
    latitude: float
    longitude: float
    poi_category: Optional[str] = None
    poi_subcategory: Optional[str] = None


class CustomerLocation(BaseModel):
    """Customer device location."""
    device_id: str
    latitude: float
    longitude: float
    store: str


# ============================================
# Expansion Models
# ============================================

class ExpansionCandidate(BaseModel):
    """Expansion candidate location (H3 cell)."""
    store_number: str  # H3 cell ID
    city: Optional[str] = None
    state: Optional[str] = "MA"
    latitude: float
    longitude: float
    predicted_annual_sales: float
    population: Optional[float] = 0
    total_poi_count: Optional[int] = 0
    min_distance_to_existing: Optional[float] = None
    nearest_existing_store: Optional[str] = None
    within_partner_isochrone: Optional[bool] = False
    partner_store_name: Optional[str] = None
    partner_city: Optional[str] = None
    partner_drive_time: Optional[float] = None
    fulfillment_strategy: Optional[str] = "new_store"
    partner_brand: Optional[str] = None  # Walmart, 7-Eleven/Speedway, Shaw's
    partner_type: Optional[str] = None  # Big Box, Convenience, Grocery
    sales_rank: Optional[int] = None
    region: Optional[str] = None  # Boston Metro, Greater Boston, Western MA, Cape & Islands
    cannibalization_risk: Optional[str] = None  # High, Medium, Low, None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    geometry_geojson: Optional[str] = None
    # Backward compatibility aliases (deprecated)
    within_convenience_isochrone: Optional[bool] = None
    convenience_store_name: Optional[str] = None
    convenience_city: Optional[str] = None
    convenience_drive_time: Optional[float] = None


# ============================================
# Optimization Models
# ============================================

class OptimizationParams(BaseModel):
    """Parameters for optimization lookup."""
    max_stores: int = 50
    min_dist_new: float = 2.0
    min_dist_existing: float = 2.0


class OptimizationResult(BaseModel):
    """Pre-computed optimization result."""
    max_stores: int
    min_distance_new: float
    min_distance_existing: float
    selected_h3_cells: Any  # Can be JSON string or list
    selected_count: int
    total_predicted_sales: float


class OptimizationLookupResponse(BaseModel):
    """Response from optimization lookup."""
    selected_candidates: List[ExpansionCandidate]
    snapped_params: OptimizationParams
    total_sales: float


# ============================================
# Metrics Models
# ============================================

class NetworkMetrics(BaseModel):
    """Pre-computed network-wide metrics."""
    total_stores: Optional[int] = 0
    total_candidates: Optional[int] = 0
    total_predicted_sales: Optional[float] = 0
    avg_population: Optional[float] = 0
    partnership_opportunity_rate: Optional[float] = 0


# ============================================
# Response Models
# ============================================

class CurrentNetworkResponse(BaseModel):
    """Response containing all current network data."""
    stores: List[Store]
    isochrones: List[Isochrone]
    partner_isochrones: List[PartnerIsochrone]
    partner_stores: List[PartnerStore]
    competitors: List[Competitor]
    ma_boundary: Optional[Any] = None
    # Backward compatibility aliases (deprecated)
    convenience_isochrones: Optional[List[PartnerIsochrone]] = None
    convenience_stores: Optional[List[PartnerStore]] = None


class ExpansionDataResponse(BaseModel):
    """Response containing all expansion analysis data."""
    candidates: List[ExpansionCandidate]
    current_stores: List[Store]
    partner_stores: List[PartnerStore]
    competitors: List[Competitor]
    # Backward compatibility alias (deprecated)
    convenience_stores: Optional[List[PartnerStore]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    auth_type: str
