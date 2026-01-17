import { useState, useEffect, useCallback } from 'react'
import { getFullNetwork, getExpansionData, getOptimizationResults } from '../services/api'

/**
 * Hook for loading and managing store data
 */
export function useStoreData() {
  const [networkData, setNetworkData] = useState({
    stores: [],
    isochrones: [],
    convenienceIsochrones: [],
    convenienceStores: [],
    competitors: [],
    maBoundary: null,
  })

  const [expansionData, setExpansionData] = useState({
    candidates: [],
    currentStores: [],
    convenienceStores: [],
    competitors: [],
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
          setNetworkData({
            stores: networkResponse.stores || [],
            isochrones: networkResponse.isochrones || [],
            convenienceIsochrones: networkResponse.convenience_isochrones || [],
            convenienceStores: networkResponse.convenience_stores || [],
            competitors: networkResponse.competitors || [],
            maBoundary: networkResponse.ma_boundary || null,
          })
          console.log(`Loaded network data: ${networkResponse.stores?.length || 0} stores`)
        }

        if (expansionResponse) {
          setExpansionData({
            candidates: expansionResponse.candidates || [],
            currentStores: expansionResponse.current_stores || [],
            convenienceStores: expansionResponse.convenience_stores || [],
            competitors: expansionResponse.competitors || [],
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
        setNetworkData({
          stores: networkResponse.stores || [],
          isochrones: networkResponse.isochrones || [],
          convenienceIsochrones: networkResponse.convenience_isochrones || [],
          convenienceStores: networkResponse.convenience_stores || [],
          competitors: networkResponse.competitors || [],
          maBoundary: networkResponse.ma_boundary || null,
        })
      }

      if (expansionResponse) {
        setExpansionData({
          candidates: expansionResponse.candidates || [],
          currentStores: expansionResponse.current_stores || [],
          convenienceStores: expansionResponse.convenience_stores || [],
          competitors: expansionResponse.competitors || [],
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
