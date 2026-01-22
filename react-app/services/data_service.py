"""Data service for loading geospatial data from Databricks."""
import json
import math
import time
from typing import Dict, Any, List, Optional
from decimal import Decimal

from core.config import get_settings
from core.database import get_db


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize data for JSON serialization.

    Converts:
    - NaN, Infinity, -Infinity floats to None
    - Decimal to float
    - Other non-JSON-serializable types to strings
    """
    if obj is None:
        return None
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, Decimal):
        float_val = float(obj)
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    elif isinstance(obj, (int, str, bool)):
        return obj
    else:
        # Try to convert to string for unknown types
        try:
            return str(obj)
        except Exception:
            return None


class DataService:
    """Service for loading and transforming geospatial data."""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()

    # ========== Individual Loaders (Phase 2.1: Split N+1 queries) ==========

    def load_stores(self) -> List[Dict[str, Any]]:
        """Load existing store locations (MA only)."""
        gold = self.settings.gold_table_prefix
        try:
            start = time.time()
            print(f"Loading viz_existing_stores (MA only)...")
            stores_df = self.db.execute_query(f"""
                SELECT store_number, city, state, latitude, longitude,
                       population, poi_count as total_poi_count,
                       h3_cell_id, geometry_geojson,
                       COALESCE(annual_sales, 0) as annual_sales
                FROM {gold}.viz_existing_stores
                WHERE UPPER(state) IN ('MA', 'MASSACHUSETTS') OR state IS NULL
            """)
            result = stores_df.to_dict('records') if not stores_df.empty else []
            elapsed = time.time() - start
            print(f"Loaded {len(result)} existing stores in {elapsed:.2f}s")
            return sanitize_for_json(result)
        except Exception as e:
            print(f"ERROR loading viz_existing_stores: {str(e)}")
            return []

    def load_isochrones(self) -> List[Dict[str, Any]]:
        """Load LCE store trade area isochrones (MA only)."""
        gold = self.settings.gold_table_prefix
        silver = self.settings.silver_table_prefix
        try:
            start = time.time()
            print(f"Loading isochrones_lce...")
            isochrones_df = self.db.execute_query(f"""
                SELECT iso.location_id as store_number, ST_AsGeoJSON(iso.geometry) as isochrone_geojson
                FROM {silver}.isochrones_lce iso
                INNER JOIN {gold}.viz_existing_stores stores
                    ON iso.location_id = stores.store_number
                WHERE stores.state = 'MA'
            """)
            result = isochrones_df.to_dict('records') if not isochrones_df.empty else []
            elapsed = time.time() - start
            print(f"Loaded {len(result)} LCE isochrones in {elapsed:.2f}s")
            return sanitize_for_json(result)
        except Exception as e:
            print(f"ERROR loading isochrones_lce: {str(e)}")
            return []

    def load_partner_data(self) -> Dict[str, Any]:
        """
        Load partner (convenience) store data with a single query.
        Phase 2.2: Combined duplicate viz_partners queries into one.
        Returns both isochrones and store location data.
        """
        gold = self.settings.gold_table_prefix
        try:
            start = time.time()
            print(f"Loading viz_partners...")
            # Single query fetches all needed columns for both isochrones and stores
            partner_df = self.db.execute_query(f"""
                SELECT id as location_id,
                       geometry_geojson as isochrone_geojson,
                       candidate_count_in_isochrone,
                       total_candidate_sales_in_isochrone,
                       name, latitude, longitude, store_type as poi_category, poi_subcategory
                FROM {gold}.viz_partners
            """)

            if partner_df.empty:
                print("No partner data found")
                return {'isochrones': [], 'stores': []}

            records = partner_df.to_dict('records')

            # Split into isochrone and store views from single query result
            isochrones = [
                {
                    'location_id': r['location_id'],
                    'isochrone_geojson': r['isochrone_geojson'],
                    'candidate_count_in_isochrone': r['candidate_count_in_isochrone'],
                    'total_candidate_sales_in_isochrone': r['total_candidate_sales_in_isochrone']
                }
                for r in records
            ]
            stores = [
                {
                    'name': r['name'],
                    'latitude': r['latitude'],
                    'longitude': r['longitude'],
                    'poi_category': r['poi_category'],
                    'poi_subcategory': r['poi_subcategory']
                }
                for r in records
            ]

            elapsed = time.time() - start
            print(f"Loaded {len(isochrones)} partner isochrones and {len(stores)} partner stores in {elapsed:.2f}s")
            return sanitize_for_json({'isochrones': isochrones, 'stores': stores})
        except Exception as e:
            print(f"ERROR loading viz_partners: {str(e)}")
            return {'isochrones': [], 'stores': []}

    def load_competitors(self) -> List[Dict[str, Any]]:
        """Load competitor store locations."""
        gold = self.settings.gold_table_prefix
        try:
            start = time.time()
            print(f"Loading viz_competitors...")
            competitors_df = self.db.execute_query(f"""
                SELECT name, latitude, longitude, poi_category, poi_subcategory
                FROM {gold}.viz_competitors
            """)
            result = competitors_df.to_dict('records') if not competitors_df.empty else []
            elapsed = time.time() - start
            print(f"Loaded {len(result)} competitors in {elapsed:.2f}s")
            return sanitize_for_json(result)
        except Exception as e:
            print(f"ERROR loading viz_competitors: {str(e)}")
            return []

    def load_ma_boundary(self) -> Optional[Dict[str, Any]]:
        """Load Massachusetts state boundary."""
        bronze = self.settings.bronze_table_prefix
        try:
            print(f"Loading MA boundary...")
            ma_boundary_df = self.db.execute_query(f"""
                SELECT ST_AsGeoJSON(geometry) as geometry_geojson
                FROM {bronze}.census_states
                WHERE state_abbr = 'MA'
            """)
            if not ma_boundary_df.empty and ma_boundary_df.iloc[0].get('geometry_geojson'):
                print("Loaded MA boundary")
                return json.loads(ma_boundary_df.iloc[0]['geometry_geojson'])
            return None
        except Exception as e:
            print(f"ERROR loading MA boundary: {str(e)}")
            return None

    # ========== Composite Loaders ==========

    def load_current_network_data(self) -> Dict[str, Any]:
        """Load all data for Current Network mode from viz_* gold tables."""
        print(f"\n=== LOADING CURRENT NETWORK DATA ===")

        # Use individual loaders for better granularity
        partner_data = self.load_partner_data()

        result = {
            'stores': self.load_stores(),
            'isochrones': self.load_isochrones(),
            'partner_isochrones': partner_data['isochrones'],
            'partner_stores': partner_data['stores'],
            'competitors': self.load_competitors(),
            'ma_boundary': self.load_ma_boundary(),
            # Backward compatibility aliases (deprecated)
            'convenience_isochrones': partner_data['isochrones'],
            'convenience_stores': partner_data['stores']
        }

        return result

    def load_expansion_candidates(
        self,
        min_sales: Optional[float] = None,
        max_sales: Optional[float] = None,
        min_population: Optional[float] = None,
        max_population: Optional[float] = None,
        fulfillment_strategy: Optional[str] = None,
        quality_tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load expansion candidate locations with optional SQL-level filtering.
        Phase 2.4: Push filters to SQL WHERE clauses for better performance.
        """
        gold = self.settings.gold_table_prefix

        # Build WHERE clause dynamically
        conditions = []
        if min_sales is not None:
            conditions.append(f"predicted_annual_sales >= {min_sales}")
        if max_sales is not None:
            conditions.append(f"predicted_annual_sales <= {max_sales}")
        if min_population is not None:
            conditions.append(f"population >= {min_population}")
        if max_population is not None:
            conditions.append(f"population <= {max_population}")
        if fulfillment_strategy is not None:
            conditions.append(f"fulfillment_strategy = '{fulfillment_strategy}'")
        if quality_tier is not None:
            conditions.append(f"quality_tier = '{quality_tier}'")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        try:
            start = time.time()
            filter_desc = f" with filters: {conditions}" if conditions else ""
            print(f"Loading viz_expansion_candidates{filter_desc}...")
            candidates_df = self.db.execute_query(f"""
                SELECT h3_cell_id as store_number,
                       COALESCE(
                           CASE
                               WHEN partner_city IS NOT NULL THEN partner_city
                               WHEN urbanity IN ('Very_High_density_urban', 'High_density_urban') THEN 'Boston Metro'
                               WHEN urbanity IN ('Medium_density_urban', 'Low_density_urban') THEN 'Greater Boston'
                               ELSE 'Massachusetts'
                           END,
                           'Massachusetts'
                       ) as city,
                       'MA' as state,
                       latitude, longitude,
                       predicted_annual_sales, population, total_poi_count,
                       min_distance_to_existing, nearest_existing_store,
                       within_partner_isochrone, partner_store_name,
                       partner_city, partner_drive_time,
                       fulfillment_strategy, quality_tier,
                       center_lat, center_lon, geometry_geojson
                FROM {gold}.viz_expansion_candidates
                {where_clause}
            """)
            result = candidates_df.to_dict('records') if not candidates_df.empty else []
            elapsed = time.time() - start
            print(f"Loaded {len(result)} expansion candidates in {elapsed:.2f}s")
            return sanitize_for_json(result)
        except Exception as e:
            print(f"ERROR loading viz_expansion_candidates: {str(e)}")
            return []

    def load_expansion_data(self) -> Dict[str, Any]:
        """Load all data for Expansion Analysis mode from viz_* gold tables."""
        print(f"\n=== LOADING EXPANSION DATA ===")

        # Reuse individual loaders to avoid duplicate queries
        partner_data = self.load_partner_data()

        result = {
            'candidates': self.load_expansion_candidates(),
            'current_stores': self.load_stores(),
            'partner_stores': partner_data['stores'],
            'competitors': self.load_competitors(),
            # Backward compatibility alias (deprecated)
            'convenience_stores': partner_data['stores']
        }

        return sanitize_for_json(result)

    def load_optimization_results(self) -> List[Dict[str, Any]]:
        """Load pre-computed optimization results for O(1) lookup."""
        gold = self.settings.gold_table_prefix

        try:
            print(f"Loading optimization results from {gold}...")
            results_df = self.db.execute_query(f"""
                SELECT max_stores, min_distance_new, min_distance_existing,
                       selected_h3_cells, selected_count, total_predicted_sales
                FROM {gold}.viz_optimization_results
            """)
            results = results_df.to_dict('records') if not results_df.empty else []
            print(f"Loaded {len(results)} optimization result combinations")
            return sanitize_for_json(results)
        except Exception as e:
            print(f"ERROR loading optimization results: {str(e)}")
            return []

    def load_network_metrics(self) -> Dict[str, Any]:
        """Load pre-computed network metrics (singleton row)."""
        gold = self.settings.gold_table_prefix

        try:
            print(f"Loading network metrics from {gold}...")
            metrics_df = self.db.execute_query(f"""
                SELECT * FROM {gold}.viz_network_metrics
            """)
            if not metrics_df.empty:
                print("Loaded network metrics")
                return sanitize_for_json(metrics_df.to_dict('records')[0])
            return {}
        except Exception as e:
            print(f"ERROR loading network metrics: {str(e)}")
            return {}

    def lookup_optimization(
        self,
        max_stores: int,
        min_dist_new: float,
        min_dist_existing: float,
        candidates: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Lookup pre-computed optimization results.

        Snaps parameters to nearest pre-computed values and returns
        matching candidates with O(1) lookup instead of O(n^2) runtime.
        """
        # Available parameter grid (must match pipeline)
        param_grid = {
            'max_stores': [10, 50],
            'min_dist_new': [2.0, 3.0],
            'min_dist_existing': [2.0, 3.0]
        }

        def snap_to_grid(value: float, grid: List[float]) -> float:
            return min(grid, key=lambda x: abs(x - value))

        # Snap to nearest values
        snapped = {
            'max_stores': snap_to_grid(max_stores, param_grid['max_stores']),
            'min_dist_new': snap_to_grid(min_dist_new, param_grid['min_dist_new']),
            'min_dist_existing': snap_to_grid(min_dist_existing, param_grid['min_dist_existing'])
        }

        # Load optimization cache
        cache = self.load_optimization_results()

        # Find matching result
        result = next(
            (r for r in cache
             if r['max_stores'] == snapped['max_stores']
             and r['min_distance_new'] == snapped['min_dist_new']
             and r['min_distance_existing'] == snapped['min_dist_existing']),
            None
        )

        if not result:
            print(f"No pre-computed result found for params: {snapped}")
            return {
                'selected_candidates': [],
                'snapped_params': snapped,
                'total_sales': 0
            }

        # Parse selected H3 cells
        h3_cells = result.get('selected_h3_cells', [])
        if isinstance(h3_cells, str):
            try:
                h3_cells = json.loads(h3_cells)
            except Exception:
                h3_cells = []

        # Phase 2.3: Convert to set for O(1) lookups instead of O(n) list membership
        h3_cells_set = set(h3_cells)

        # If candidates provided, map H3 cells to full objects
        if candidates:
            selected = [
                c for c in candidates
                if c.get('store_number') in h3_cells_set
            ]
        else:
            # Load candidates if not provided
            expansion_data = self.load_expansion_data()
            selected = [
                c for c in expansion_data.get('candidates', [])
                if c.get('store_number') in h3_cells_set
            ]

        print(f"Optimization lookup: max={snapped['max_stores']}, "
              f"dist_new={snapped['min_dist_new']}, "
              f"dist_exist={snapped['min_dist_existing']} -> "
              f"{len(selected)} stores")

        return sanitize_for_json({
            'selected_candidates': selected,
            'snapped_params': snapped,
            'total_sales': result.get('total_predicted_sales', 0)
        })


# Singleton instance
_service_instance = None


def get_data_service() -> DataService:
    """Get singleton data service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataService()
    return _service_instance
