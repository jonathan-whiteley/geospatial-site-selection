import { useState, useEffect, useCallback, useMemo } from 'react'
import { getInitialData, getFullNetwork, getExpansionData } from '../services/api'

/**
 * Hook for loading and managing store data
 *
 * Phase 1 Performance Optimization:
 * - Uses single /api/init endpoint instead of 3 parallel calls
 * - Receives pre-computed sales/population ranges from backend
 * - Optimization results loaded on-demand (not on initial load)
 */
export function useStoreData() {
  const [networkData, setNetworkData] = useState({
    stores: [],
    isochrones: [],
    partnerIsochrones: [],
    partnerStores: [],
    competitors: [],
    maBoundary: null,
    // Backward compatibility aliases (deprecated)
    convenienceIsochrones: [],
    convenienceStores: [],
  })

  const [expansionData, setExpansionData] = useState({
    candidates: [],
    currentStores: [],
    partnerStores: [],
    competitors: [],
    // Backward compatibility alias (deprecated)
    convenienceStores: [],
  })

  // Pre-computed ranges from backend (avoids O(n) frontend calculations)
  const [backendRanges, setBackendRanges] = useState({
    sales: { min: 0, max: 1000000 },
    population: { min: 0, max: 100000 },
  })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load all data on mount using consolidated endpoint
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      setError(null)

      try {
        console.time('initialDataLoad')
        console.log('=== LOADING DATA (CONSOLIDATED) ===')

        // Single API call replaces 3 parallel calls
        const response = await getInitialData()

        // Process network data
        const network = response.network || {}
        const partnerIsochrones = network.partner_isochrones || network.convenience_isochrones || []
        const partnerStores = network.partner_stores || network.convenience_stores || []

        setNetworkData({
          stores: network.stores || [],
          isochrones: network.isochrones || [],
          partnerIsochrones,
          partnerStores,
          competitors: network.competitors || [],
          maBoundary: network.ma_boundary || null,
          // Backward compatibility aliases
          convenienceIsochrones: partnerIsochrones,
          convenienceStores: partnerStores,
        })

        // Process expansion data
        const expansion = response.expansion || {}
        const expansionPartnerStores = expansion.partner_stores || expansion.convenience_stores || []

        setExpansionData({
          candidates: expansion.candidates || [],
          currentStores: expansion.current_stores || [],
          partnerStores: expansionPartnerStores,
          competitors: expansion.competitors || [],
          // Backward compatibility alias
          convenienceStores: expansionPartnerStores,
        })

        // Use pre-computed ranges from backend
        if (response.ranges) {
          setBackendRanges(response.ranges)
        }

        console.log(`Loaded: ${network.stores?.length || 0} stores, ${expansion.candidates?.length || 0} candidates`)
        console.timeEnd('initialDataLoad')
        console.log('=== DATA LOAD COMPLETE ===')

      } catch (err) {
        console.error('Error loading data:', err)
        setError(err.message || 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  // Refresh data using consolidated endpoint
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getInitialData()

      // Process network data
      const network = response.network || {}
      const partnerIsochrones = network.partner_isochrones || network.convenience_isochrones || []
      const partnerStores = network.partner_stores || network.convenience_stores || []

      setNetworkData({
        stores: network.stores || [],
        isochrones: network.isochrones || [],
        partnerIsochrones,
        partnerStores,
        competitors: network.competitors || [],
        maBoundary: network.ma_boundary || null,
        convenienceIsochrones: partnerIsochrones,
        convenienceStores: partnerStores,
      })

      // Process expansion data
      const expansion = response.expansion || {}
      const expansionPartnerStores = expansion.partner_stores || expansion.convenience_stores || []

      setExpansionData({
        candidates: expansion.candidates || [],
        currentStores: expansion.current_stores || [],
        partnerStores: expansionPartnerStores,
        competitors: expansion.competitors || [],
        convenienceStores: expansionPartnerStores,
      })

      // Update ranges
      if (response.ranges) {
        setBackendRanges(response.ranges)
      }
    } catch (err) {
      setError(err.message || 'Failed to refresh data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Use pre-computed ranges from backend (memoized for stability)
  const salesRange = useMemo(() => backendRanges.sales, [backendRanges.sales])
  const populationRange = useMemo(() => backendRanges.population, [backendRanges.population])

  return {
    networkData,
    expansionData,
    salesRange,
    populationRange,
    loading,
    error,
    refresh,
  }
}
