import { useState, useEffect, useCallback } from 'react'
import { getFullNetwork, getExpansionData, getOptimizationResults } from '../services/api'

/**
 * Hook for loading and managing store data
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

  const [optimizationCache, setOptimizationCache] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load all data on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      setError(null)

      try {
        console.log('=== LOADING DATA ===')

        // Load network and expansion data in parallel
        const [networkResponse, expansionResponse, optimizationResponse] = await Promise.all([
          getFullNetwork().catch(e => {
            console.error('Failed to load network data:', e)
            return null
          }),
          getExpansionData().catch(e => {
            console.error('Failed to load expansion data:', e)
            return null
          }),
          getOptimizationResults().catch(e => {
            console.error('Failed to load optimization cache:', e)
            return []
          }),
        ])

        if (networkResponse) {
          // Support both partner_* (new) and convenience_* (deprecated) response keys
          const partnerIsochrones = networkResponse.partner_isochrones || networkResponse.convenience_isochrones || []
          const partnerStores = networkResponse.partner_stores || networkResponse.convenience_stores || []
          setNetworkData({
            stores: networkResponse.stores || [],
            isochrones: networkResponse.isochrones || [],
            partnerIsochrones,
            partnerStores,
            competitors: networkResponse.competitors || [],
            maBoundary: networkResponse.ma_boundary || null,
            // Backward compatibility aliases
            convenienceIsochrones: partnerIsochrones,
            convenienceStores: partnerStores,
          })
          console.log(`Loaded network data: ${networkResponse.stores?.length || 0} stores`)
        }

        if (expansionResponse) {
          // Support both partner_stores (new) and convenience_stores (deprecated)
          const partnerStores = expansionResponse.partner_stores || expansionResponse.convenience_stores || []
          setExpansionData({
            candidates: expansionResponse.candidates || [],
            currentStores: expansionResponse.current_stores || [],
            partnerStores,
            competitors: expansionResponse.competitors || [],
            // Backward compatibility alias
            convenienceStores: partnerStores,
          })
          console.log(`Loaded expansion data: ${expansionResponse.candidates?.length || 0} candidates`)
        }

        if (optimizationResponse) {
          setOptimizationCache(optimizationResponse)
          console.log(`Loaded optimization cache: ${optimizationResponse.length} combinations`)
        }

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

  // Refresh data
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [networkResponse, expansionResponse] = await Promise.all([
        getFullNetwork(),
        getExpansionData(),
      ])

      if (networkResponse) {
        const partnerIsochrones = networkResponse.partner_isochrones || networkResponse.convenience_isochrones || []
        const partnerStores = networkResponse.partner_stores || networkResponse.convenience_stores || []
        setNetworkData({
          stores: networkResponse.stores || [],
          isochrones: networkResponse.isochrones || [],
          partnerIsochrones,
          partnerStores,
          competitors: networkResponse.competitors || [],
          maBoundary: networkResponse.ma_boundary || null,
          convenienceIsochrones: partnerIsochrones,
          convenienceStores: partnerStores,
        })
      }

      if (expansionResponse) {
        const partnerStores = expansionResponse.partner_stores || expansionResponse.convenience_stores || []
        setExpansionData({
          candidates: expansionResponse.candidates || [],
          currentStores: expansionResponse.current_stores || [],
          partnerStores,
          competitors: expansionResponse.competitors || [],
          convenienceStores: partnerStores,
        })
      }
    } catch (err) {
      setError(err.message || 'Failed to refresh data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Calculate sales range from candidates
  const salesRange = {
    min: expansionData.candidates.length > 0
      ? Math.min(...expansionData.candidates.map(c => c.predicted_annual_sales || 0))
      : 0,
    max: expansionData.candidates.length > 0
      ? Math.max(...expansionData.candidates.map(c => c.predicted_annual_sales || 0))
      : 1000000,
  }

  // Calculate population range from candidates
  const populationRange = {
    min: expansionData.candidates.length > 0
      ? Math.min(...expansionData.candidates.map(c => c.population || 0))
      : 0,
    max: expansionData.candidates.length > 0
      ? Math.max(...expansionData.candidates.map(c => c.population || 0))
      : 100000,
  }

  return {
    networkData,
    expansionData,
    optimizationCache,
    salesRange,
    populationRange,
    loading,
    error,
    refresh,
  }
}
