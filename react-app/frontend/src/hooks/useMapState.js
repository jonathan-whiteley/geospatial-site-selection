import { useState, useCallback } from 'react'

/**
 * Default layer visibility state
 */
const DEFAULT_LAYERS = {
  currentStores: true,
  customerLocations: false,
  candidates: false,
  candidateIsochrones: false,
  partners: false,
  competitors: false,
  // Backward compatibility alias (deprecated)
  convenience: false,
}

/**
 * Default partner brand filter state (all brands enabled by default)
 */
const DEFAULT_PARTNER_BRAND_FILTERS = {
  'Walmart': true,
  '7-Eleven/Speedway': true,
  "Shaw's": true,
}

/**
 * Default layer visibility for each mode
 */
const MODE_LAYERS = {
  current: {
    currentStores: true,
    customerLocations: false,
    candidates: false,
    candidateIsochrones: false,
    partners: false,
    competitors: false,
    convenience: false,
  },
  expansion: {
    currentStores: true,
    customerLocations: false,
    candidates: true,
    candidateIsochrones: false,
    partners: false,
    competitors: false,
    convenience: false,
  },
}

/**
 * Default filter values (null = no filter active)
 */
const DEFAULT_FILTERS = {
  minSales: null,
  maxSales: null,
  minPopulation: null,
  maxPopulation: null,
}

/**
 * Default optimization parameters
 */
const DEFAULT_OPTIMIZATION_PARAMS = {
  maxStores: 50,
  minDistNew: 2.0,
  minDistExisting: 2.0,
}

/**
 * Available parameter grid for optimization (must match backend)
 */
export const PARAM_GRID = {
  maxStores: [10, 50, 100],
  minDistNew: [1.0, 2.0, 3.0],
  minDistExisting: [1.0, 2.0, 3.0],
}

/**
 * Hook for managing map state including mode, layers, filters, and selection
 */
export function useMapState() {
  const [mode, setModeState] = useState('expansion')
  const [layers, setLayers] = useState(MODE_LAYERS.expansion)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [optimizationParams, setOptimizationParams] = useState(DEFAULT_OPTIMIZATION_PARAMS)
  const [optimizationResults, setOptimizationResults] = useState(null)
  const [selectedStore, setSelectedStore] = useState(null)
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)
  const [mapBounds, setMapBounds] = useState(null)
  const [partnerBrandFilters, setPartnerBrandFilters] = useState(DEFAULT_PARTNER_BRAND_FILTERS)

  // Set mode and update layers accordingly
  const setMode = useCallback((newMode) => {
    setModeState(newMode)
    setLayers(MODE_LAYERS[newMode] || DEFAULT_LAYERS)
    setDetailPanelOpen(false)
    setSelectedStore(null)

    // Reset filters when switching to expansion
    if (newMode === 'expansion') {
      setFilters(DEFAULT_FILTERS)
    }
  }, [])

  // Toggle a specific layer
  const toggleLayer = useCallback((layerName) => {
    setLayers(prev => ({
      ...prev,
      [layerName]: !prev[layerName],
    }))
  }, [])

  // Set a layer's visibility
  const setLayerVisibility = useCallback((layerName, visible) => {
    setLayers(prev => ({
      ...prev,
      [layerName]: visible,
    }))
  }, [])

  // Update filters
  const updateFilters = useCallback((updates) => {
    setFilters(prev => ({
      ...prev,
      ...updates,
    }))
  }, [])

  // Update optimization parameters
  const updateOptimizationParams = useCallback((updates) => {
    setOptimizationParams(prev => ({
      ...prev,
      ...updates,
    }))
  }, [])

  // Select a store and open detail panel
  const selectStore = useCallback((store) => {
    setSelectedStore(store)
    setDetailPanelOpen(true)
  }, [])

  // Close detail panel
  const closeDetailPanel = useCallback(() => {
    setDetailPanelOpen(false)
    setSelectedStore(null)
  }, [])

  // Clear optimization results
  const clearOptimization = useCallback(() => {
    setOptimizationResults(null)
  }, [])

  // Update map bounds (called when user pans/zooms)
  const updateMapBounds = useCallback((bounds) => {
    setMapBounds(bounds)
  }, [])

  // Toggle a specific partner brand filter
  const togglePartnerBrand = useCallback((brand) => {
    setPartnerBrandFilters(prev => ({
      ...prev,
      [brand]: !prev[brand]
    }))
  }, [])

  return {
    // State
    mode,
    layers,
    filters,
    optimizationParams,
    optimizationResults,
    selectedStore,
    detailPanelOpen,
    mapBounds,
    partnerBrandFilters,

    // Actions
    setMode,
    toggleLayer,
    setLayerVisibility,
    updateFilters,
    updateOptimizationParams,
    setOptimizationResults,
    selectStore,
    closeDetailPanel,
    clearOptimization,
    updateMapBounds,
    togglePartnerBrand,
  }
}
