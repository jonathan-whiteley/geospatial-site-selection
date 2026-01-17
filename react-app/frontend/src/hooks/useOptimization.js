import { useState, useCallback } from 'react'
import { lookupOptimization } from '../services/api'
import { snapToGrid } from '../lib/utils'
import { PARAM_GRID } from './useMapState'

/**
 * Hook for managing optimization operations
 */
export function useOptimization(expansionData, setOptimizationResults) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Run optimization lookup
  const runOptimization = useCallback(async (params) => {
    setLoading(true)
    setError(null)

    try {
      // Snap params to grid
      const snappedParams = {
        maxStores: snapToGrid(params.maxStores, PARAM_GRID.maxStores),
        minDistNew: snapToGrid(params.minDistNew, PARAM_GRID.minDistNew),
        minDistExisting: snapToGrid(params.minDistExisting, PARAM_GRID.minDistExisting),
      }

      console.log('Running optimization with params:', snappedParams)

      const result = await lookupOptimization(snappedParams)

      if (result && result.selected_candidates) {
        setOptimizationResults(result.selected_candidates)
        console.log(`Optimization returned ${result.selected_candidates.length} candidates`)
        return result
      } else {
        console.warn('No optimization results returned')
        setOptimizationResults([])
        return { selected_candidates: [], total_sales: 0 }
      }
    } catch (err) {
      console.error('Optimization error:', err)
      setError(err.message || 'Optimization failed')
      return null
    } finally {
      setLoading(false)
    }
  }, [setOptimizationResults])

  // Client-side optimization fallback (uses pre-loaded candidates)
  const runLocalOptimization = useCallback((params, candidates, existingStores) => {
    if (!candidates || candidates.length === 0) {
      return []
    }

    const { maxStores, minDistNew, minDistExisting } = params

    // Sort by predicted sales descending
    const sorted = [...candidates].sort(
      (a, b) => (b.predicted_annual_sales || 0) - (a.predicted_annual_sales || 0)
    )

    const selected = []

    for (const candidate of sorted) {
      if (selected.length >= maxStores) break

      // Check distance to existing stores
      const tooCloseToExisting = existingStores.some(store => {
        const dist = distanceMiles(
          candidate.latitude,
          candidate.longitude,
          store.latitude,
          store.longitude
        )
        return dist < minDistExisting
      })

      if (tooCloseToExisting) continue

      // Check distance to already selected
      const tooCloseToSelected = selected.some(s => {
        const dist = distanceMiles(
          candidate.latitude,
          candidate.longitude,
          s.latitude,
          s.longitude
        )
        return dist < minDistNew
      })

      if (tooCloseToSelected) continue

      selected.push(candidate)
    }

    return selected
  }, [])

  return {
    runOptimization,
    runLocalOptimization,
    loading,
    error,
  }
}

// Helper function for distance calculation
function distanceMiles(lat1, lon1, lat2, lon2) {
  const R = 3959
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
           Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
           Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c
}
