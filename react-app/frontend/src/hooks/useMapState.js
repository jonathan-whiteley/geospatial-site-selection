import { useState, useCallback } from 'react'

/**
 * Default layer visibility state
 */
const DEFAULT_LAYERS = {
  currentStores: true,
  h3Hexagons: true,
  candidates: false,
  candidateIsochrones: false,
  convenience: false,
  competitors: false,
}

/**
 * Default layer visibility for each mode
 */
const MODE_LAYERS = {
  current: {
    currentStores: true,
    h3Hexagons: true,
    candidates: false,
    candidateIsochrones: false,
    convenience: false,
    competitors: false,
  },
  expansion: {
    currentStores: true,
    h3Hexagons: true,
    candidates: true,
    candidateIsochrones: false,
    convenience: true,
    competitors: false,
  },
}

/**
 * Default filter values
 */
const DEFAULT_FILTERS = {
  minSales: 500000,
  maxSales: null,
  minPopulation: 5000,
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
  const [mode, setModeState] = useState('current')
  const [layers, setLayers] = useState(DEFAULT_LAYERS)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [optimizationParams, setOptimizationParams] = useState(DEFAULT_OPTIMIZATION_PARAMS)
  const [optimizationResults, setOptimizationResults] = useState(null)
  const [selectedStore, setSelectedStore] = useState(null)
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)

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

  return {
    // State
    mode,
    layers,
    filters,
    optimizationParams,
    optimizationResults,
    selectedStore,
    detailPanelOpen,

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
  }
}
