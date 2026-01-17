"""Data service for loading geospatial data from Databricks."""
import json
from typing import Dict, Any, List, Optional

from core.config import get_settings
from core.database import get_db


class DataService:
    """Service for loading and transforming geospatial data."""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_db()

    def load_current_network_data(self) -> Dict[str, Any]:
        """Load all data for Current Network mode from viz_* gold tables."""
        gold = self.settings.gold_table_prefix
        silver = self.settings.silver_table_prefix
        bronze = self.settings.bronze_table_prefix

        print(f"\n=== LOADING CURRENT NETWORK DATA ===")
        print(f"Gold: {gold}, Silver: {silver}, Bronze: {bronze}")

        result = {
            'stores': [],
            'isochrones': [],
            'convenience_isochrones': [],
            'convenience_stores': [],
            'competitors': [],
            'ma_boundary': None
        }

        # Load existing stores
        try:
            print(f"Loading viz_existing_stores...")
            stores_df = self.db.execute_query(f"""
                SELECT store_number, city, state, latitude, longitude,
                       population, poi_count as total_poi_count,
                       h3_cell_id, geometry_geojson,
                       COALESCE(annual_sales, 0) as annual_sales
                FROM {gold}.viz_existing_stores
            """)
            result['stores'] = stores_df.to_dict('records') if not stores_df.empty else []
            print(f"Loaded {len(result['stores'])} existing stores")
        except Exception as e:
            print(f"ERROR loading viz_existing_stores: {str(e)}")

        # Load LCE isochrones (MA only)
        try:
            print(f"Loading isochrones_lce...")
            isochrones_df = self.db.execute_query(f"""
                SELECT iso.location_id as store_number, ST_AsGeoJSON(iso.geometry) as isochrone_geojson
                FROM {silver}.isochrones_lce iso
                INNER JOIN {gold}.viz_existing_stores stores
                    ON iso.location_id = stores.store_number
                WHERE stores.state = 'MA'
            """)
            result['isochrones'] = isochrones_df.to_dict('records') if not isochrones_df.empty else []
            print(f"Loaded {len(result['isochrones'])} LCE isochrones")
        except Exception as e:
            print(f"ERROR loading isochrones_lce: {str(e)}")

        # Load convenience isochrones
        try:
            print(f"Loading viz_convenience...")
            convenience_iso_df = self.db.execute_query(f"""
                SELECT id as location_id, geometry_geojson as isochrone_geojson,
                       candidate_count_in_isochrone, total_candidate_sales_in_isochrone
                FROM {gold}.viz_convenience
            """)
            result['convenience_isochrones'] = convenience_iso_df.to_dict('records') if not convenience_iso_df.empty else []
            print(f"Loaded {len(result['convenience_isochrones'])} convenience isochrones")
        except Exception as e:
            print(f"ERROR loading viz_convenience: {str(e)}")

        # Load convenience stores
        try:
            convenience_stores_df = self.db.execute_query(f"""
                SELECT name, latitude, longitude, store_type as poi_category
                FROM {gold}.viz_convenience
            """)
            result['convenience_stores'] = convenience_stores_df.to_dict('records') if not convenience_stores_df.empty else []
            print(f"Loaded {len(result['convenience_stores'])} convenience stores")
        except Exception as e:
            print(f"ERROR loading convenience stores: {str(e)}")

        # Load competitors
        try:
            print(f"Loading viz_competitors...")
            competitors_df = self.db.execute_query(f"""
                SELECT name, latitude, longitude, poi_category, poi_subcategory
                FROM {gold}.viz_competitors
            """)
            result['competitors'] = competitors_df.to_dict('records') if not competitors_df.empty else []
            print(f"Loaded {len(result['competitors'])} competitors")
        except Exception as e:
            print(f"ERROR loading viz_competitors: {str(e)}")

        # Load MA boundary
        try:
            print(f"Loading MA boundary...")
            ma_boundary_df = self.db.execute_query(f"""
                SELECT ST_AsGeoJSON(geometry) as geometry_geojson
                FROM {bronze}.census_states
                WHERE state_abbr = 'MA'
            """)
            if not ma_boundary_df.empty and ma_boundary_df.iloc[0].get('geometry_geojson'):
                result['ma_boundary'] = json.loads(ma_boundary_df.iloc[0]['geometry_geojson'])
                print("Loaded MA boundary")
        except Exception as e:
            print(f"ERROR loading MA boundary: {str(e)}")

        return result

    def load_expansion_data(self) -> Dict[str, Any]:
        """Load all data for Expansion Analysis mode from viz_* gold tables."""
        gold = self.settings.gold_table_prefix

        print(f"\n=== LOADING EXPANSION DATA ===")
        print(f"Gold: {gold}")

        result = {
            'candidates': [],
            'current_stores': [],
            'convenience_stores': [],
            'competitors': []
        }

        # Load expansion candidates
        try:
            print(f"Loading viz_expansion_candidates...")
            candidates_df = self.db.execute_query(f"""
                SELECT h3_cell_id as store_number,
                       COALESCE(
                           CASE
                               WHEN convenience_city IS NOT NULL THEN convenience_city
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
                       within_convenience_isochrone, convenience_store_name,
                       convenience_city, convenience_drive_time,
                       fulfillment_strategy, quality_tier,
                       center_lat, center_lon, geometry_geojson
                FROM {gold}.viz_expansion_candidates
            """)
            result['candidates'] = candidates_df.to_dict('records') if not candidates_df.empty else []
            print(f"Loaded {len(result['candidates'])} expansion candidates")
        except Exception as e:
            print(f"ERROR loading viz_expansion_candidates: {str(e)}")

        # Load current stores
        try:
            print(f"Loading current_stores...")
            stores_df = self.db.execute_query(f"""
                SELECT store_number, city, state, latitude, longitude,
                       population, poi_count as total_poi_count,
                       h3_cell_id, geometry_geojson,
                       COALESCE(annual_sales, 0) as annual_sales
                FROM {gold}.viz_existing_stores
            """)
            result['current_stores'] = stores_df.to_dict('records') if not stores_df.empty else []
            print(f"Loaded {len(result['current_stores'])} current stores")
        except Exception as e:
            print(f"ERROR loading current stores: {str(e)}")

        # Load convenience stores
        try:
            convenience_stores_df = self.db.execute_query(f"""
                SELECT name, latitude, longitude, store_type as poi_category
                FROM {gold}.viz_convenience
            """)
            result['convenience_stores'] = convenience_stores_df.to_dict('records') if not convenience_stores_df.empty else []
            print(f"Loaded {len(result['convenience_stores'])} convenience stores")
        except Exception as e:
            print(f"ERROR loading convenience stores: {str(e)}")

        # Load competitors
        try:
            competitors_df = self.db.execute_query(f"""
                SELECT name, latitude, longitude, poi_category, poi_subcategory
                FROM {gold}.viz_competitors
            """)
            result['competitors'] = competitors_df.to_dict('records') if not competitors_df.empty else []
            print(f"Loaded {len(result['competitors'])} competitors")
        except Exception as e:
            print(f"ERROR loading competitors: {str(e)}")

        return result

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
            return results
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
                return metrics_df.to_dict('records')[0]
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
            'max_stores': [10, 50, 100],
            'min_dist_new': [1.0, 2.0, 3.0],
            'min_dist_existing': [1.0, 2.0, 3.0]
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

        # If candidates provided, map H3 cells to full objects
        if candidates:
            selected = [
                c for c in candidates
                if c.get('store_number') in h3_cells
            ]
        else:
            # Load candidates if not provided
            expansion_data = self.load_expansion_data()
            selected = [
                c for c in expansion_data.get('candidates', [])
                if c.get('store_number') in h3_cells
            ]

        print(f"Optimization lookup: max={snapped['max_stores']}, "
              f"dist_new={snapped['min_dist_new']}, "
              f"dist_exist={snapped['min_dist_existing']} -> "
              f"{len(selected)} stores")

        return {
            'selected_candidates': selected,
            'snapped_params': snapped,
            'total_sales': result.get('total_predicted_sales', 0)
        }


# Singleton instance
_service_instance = None


def get_data_service() -> DataService:
    """Get singleton data service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataService()
    return _service_instance
