"""
Consolidated initial data endpoint for fast app startup.

Phase 1 Performance Optimization:
- Single endpoint replaces 3 parallel API calls
- Eliminates duplicate queries (stores, partners, competitors loaded once)
- Uses connection pooling for all queries
- Runs queries in PARALLEL using ThreadPoolExecutor
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service

router = APIRouter(prefix="/init", tags=["init"])


@router.get("")
async def get_initial_data():
    """
    Load all initial app data in a single request.

    Combines data from:
    - /api/stores/network
    - /api/expansion/data

    Eliminates duplicate queries for:
    - stores (was loaded in both endpoints)
    - partners (was loaded in both endpoints)
    - competitors (was loaded in both endpoints)

    Returns pre-computed sales/population ranges to avoid frontend calculation.

    Uses ThreadPoolExecutor for parallel query execution.
    """
    try:
        service = get_data_service()
        start_time = time.time()

        print("\n=== LOADING INITIAL DATA (PARALLEL) ===")

        # Run all queries in parallel using ThreadPoolExecutor
        results = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(service.load_partner_data): 'partner_data',
                executor.submit(service.load_stores): 'stores',
                executor.submit(service.load_competitors): 'competitors',
                executor.submit(service.load_expansion_candidates): 'candidates',
                executor.submit(service.load_isochrones): 'isochrones',
                executor.submit(service.load_ma_boundary): 'ma_boundary',
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                    print(f"  ✓ {key} loaded")
                except Exception as e:
                    print(f"  ✗ {key} failed: {e}")
                    results[key] = [] if key != 'ma_boundary' else None

        # Extract results
        partner_data = results.get('partner_data', {'isochrones': [], 'stores': []})
        stores = results.get('stores', [])
        competitors = results.get('competitors', [])
        candidates = results.get('candidates', [])
        isochrones = results.get('isochrones', [])
        ma_boundary = results.get('ma_boundary')

        query_time = time.time() - start_time
        print(f"All queries completed in {query_time:.2f}s")

        # Pre-compute sales and population ranges (avoids O(n) frontend iterations)
        sales_values = [c.get('predicted_annual_sales', 0) or 0 for c in candidates]
        population_values = [c.get('population', 0) or 0 for c in candidates]

        sales_range = {
            'min': min(sales_values) if sales_values else 0,
            'max': max(sales_values) if sales_values else 1000000,
        }

        population_range = {
            'min': min(population_values) if population_values else 0,
            'max': max(population_values) if population_values else 100000,
        }

        print(f"Loaded: {len(stores)} stores, {len(candidates)} candidates, "
              f"{len(partner_data.get('stores', []))} partners, {len(competitors)} competitors")
        print("=== INITIAL DATA LOAD COMPLETE ===\n")

        return {
            # Network data
            'network': {
                'stores': stores,
                'isochrones': isochrones,
                'partner_isochrones': partner_data.get('isochrones', []),
                'partner_stores': partner_data.get('stores', []),
                'competitors': competitors,
                'ma_boundary': ma_boundary,
                # Backward compatibility
                'convenience_isochrones': partner_data.get('isochrones', []),
                'convenience_stores': partner_data.get('stores', []),
            },
            # Expansion data
            'expansion': {
                'candidates': candidates,
                'current_stores': stores,  # Reuse already-loaded stores
                'partner_stores': partner_data.get('stores', []),
                'competitors': competitors,  # Reuse already-loaded competitors
                # Backward compatibility
                'convenience_stores': partner_data.get('stores', []),
            },
            # Pre-computed ranges (saves frontend O(n) calculations)
            'ranges': {
                'sales': sales_range,
                'population': population_range,
            }
        }

    except Exception as e:
        print(f"ERROR in get_initial_data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
