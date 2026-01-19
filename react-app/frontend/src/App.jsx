import React, { useMemo, useCallback } from 'react'
import { AppLayout, AppHeader } from './components/layout/AppLayout'
import {
  Sidebar,
  ModeTabs,
  MapLayersSection,
  ExpansionMetricsSection,
  PartnershipRecommendationsSection,
  FiltersSection,
  OptimizationSection,
} from './components/layout/Sidebar'
import { CurrentNetworkKPIs } from './components/layout/CurrentNetworkKPIs'
import { GeospatialMap } from './components/map/GeospatialMap'
import { DetailPanel } from './components/panels/DetailPanel'
import { Accordion } from './components/ui/Accordion'
import { useMapState } from './hooks/useMapState'
import { useStoreData } from './hooks/useStoreData'
import { useOptimization } from './hooks/useOptimization'

// Logo path
const LOGO_SRC = '/logo.png'

/**
 * Loading spinner component
 */
function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-brand-orange" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  )
}

/**
 * Error display component
 */
function ErrorDisplay({ error }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 p-8">
      <div className="text-red-500 text-5xl">⚠</div>
      <p className="text-lg font-medium text-gray-900">Failed to load data</p>
      <p className="text-sm text-gray-500 text-center max-w-md">{error}</p>
    </div>
  )
}

/**
 * Main App component
 */
function App() {
  // Load store data
  const {
    networkData,
    expansionData,
    salesRange,
    populationRange,
    loading: dataLoading,
    error: dataError,
  } = useStoreData()

  // Map state management
  const {
    mode,
    layers,
    filters,
    optimizationParams,
    optimizationResults,
    selectedStore,
    detailPanelOpen,
    setMode,
    toggleLayer,
    updateFilters,
    updateOptimizationParams,
    setOptimizationResults,
    selectStore,
    closeDetailPanel,
    clearOptimization,
  } = useMapState()

  // Optimization hook
  const {
    runOptimization,
    loading: optimizationLoading,
  } = useOptimization(expansionData, setOptimizationResults)

  // Filter candidates based on current filters
  const filteredCandidates = useMemo(() => {
    let candidates = expansionData.candidates || []

    if (filters.minSales) {
      candidates = candidates.filter(c => (c.predicted_annual_sales || 0) >= filters.minSales)
    }
    if (filters.minPopulation) {
      candidates = candidates.filter(c => (c.population || 0) >= filters.minPopulation)
    }

    return candidates
  }, [expansionData.candidates, filters])

  // Get visible candidates (filtered or optimized)
  const visibleCandidates = useMemo(() => {
    if (optimizationResults && optimizationResults.length > 0) {
      return optimizationResults
    }
    return filteredCandidates
  }, [optimizationResults, filteredCandidates])

  // Check if filters are active
  const hasActiveFilters = filters.minSales || filters.minPopulation

  // Handle optimization run
  const handleRunOptimization = useCallback(async () => {
    await runOptimization(optimizationParams)
  }, [runOptimization, optimizationParams])

  // Handle CSV export
  const handleExport = useCallback(() => {
    const candidates = visibleCandidates
    if (!candidates || candidates.length === 0) {
      alert('No candidates to export. Please adjust filters or run optimization first.')
      return
    }

    const columns = [
      { key: 'store_number', label: 'H3 Cell ID' },
      { key: 'fulfillment_strategy', label: 'Fulfillment Strategy' },
      { key: 'city', label: 'City' },
      { key: 'state', label: 'State' },
      { key: 'predicted_annual_sales', label: 'Predicted Annual Sales' },
      { key: 'population', label: 'Population' },
      { key: 'total_poi_count', label: 'Total POI Count' },
      { key: 'min_distance_to_existing', label: 'Min Distance to Existing (mi)' },
      { key: 'nearest_existing_store', label: 'Nearest Existing Store' },
      { key: 'within_convenience_isochrone', label: 'Within Partner Store Trade Area' },
      { key: 'convenience_store_name', label: 'Partner Store Name' },
      { key: 'convenience_city', label: 'Partner Store City' },
      { key: 'convenience_drive_time', label: 'Partner Store Drive Time (min)' },
      { key: 'center_lat', label: 'Center Latitude' },
      { key: 'center_lon', label: 'Center Longitude' },
    ]

    const csvRows = [columns.map(c => c.label).join(',')]
    candidates.forEach(candidate => {
      const row = columns.map(col => {
        let value = candidate[col.key]
        if (value === null || value === undefined) return ''
        if (typeof value === 'boolean') return value ? 'Yes' : 'No'
        if (typeof value === 'number') {
          return col.key.includes('sales') || col.key === 'population' || col.key === 'total_poi_count'
            ? Math.round(value)
            : value.toFixed(2)
        }
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`
        }
        return value
      })
      csvRows.push(row.join(','))
    })

    const csvContent = csvRows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
    const filename = optimizationResults
      ? `expansion_recommendations_optimized_${timestamp}.csv`
      : `expansion_recommendations_filtered_${timestamp}.csv`

    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [visibleCandidates, optimizationResults])

  // Total current stores count for header
  const totalStores = networkData?.stores?.length || 0

  // Determine which accordion sections to open by default
  const defaultAccordionValues = mode === 'expansion'
    ? ['layers', 'metrics', 'filters', 'optimization']
    : ['layers', 'metrics']

  // Show loading state
  if (dataLoading) {
    return (
      <AppLayout
        header={<AppHeader logoSrc={LOGO_SRC} totalStores={0} />}
        sidebar={
          <Sidebar>
            <ModeTabs activeMode={mode} onModeChange={setMode} />
            <div className="flex-1 flex items-center justify-center">
              <LoadingSpinner message="Loading store data..." />
            </div>
          </Sidebar>
        }
      >
        <LoadingSpinner message="Initializing map..." />
      </AppLayout>
    )
  }

  // Show error state
  if (dataError) {
    return (
      <AppLayout
        header={<AppHeader logoSrc={LOGO_SRC} totalStores={0} />}
        sidebar={
          <Sidebar>
            <ModeTabs activeMode={mode} onModeChange={setMode} />
            <div className="p-4">
              <ErrorDisplay error={dataError} />
            </div>
          </Sidebar>
        }
      >
        <ErrorDisplay error={dataError} />
      </AppLayout>
    )
  }

  return (
    <AppLayout
      header={<AppHeader logoSrc={LOGO_SRC} totalStores={totalStores} />}
      kpiBar={
        <CurrentNetworkKPIs
          networkData={networkData}
          expansionData={expansionData}
        />
      }
      sidebar={
        <Sidebar>
          <ModeTabs activeMode={mode} onModeChange={setMode} />

          {/* Scrollable accordion content */}
          <div className="flex-1 overflow-y-auto">
            <Accordion
              type="multiple"
              defaultValue={defaultAccordionValues}
              className="w-full"
            >
              {/* Map Layers */}
              <MapLayersSection
                layers={layers}
                onToggle={toggleLayer}
              />

              {/* Expansion Metrics (always visible) */}
              <ExpansionMetricsSection
                candidates={expansionData.candidates}
                visibleCandidates={visibleCandidates}
              />

              {/* Partnership Recommendations */}
              <PartnershipRecommendationsSection />

              {/* Filters (expansion mode) */}
              {mode === 'expansion' && (
                <FiltersSection
                  filters={filters}
                  ranges={{
                    sales: salesRange,
                    population: populationRange,
                  }}
                  onChange={updateFilters}
                  hasActiveFilters={hasActiveFilters}
                />
              )}

              {/* Optimization (expansion mode) */}
              {mode === 'expansion' && (
                <OptimizationSection
                  params={optimizationParams}
                  onChange={updateOptimizationParams}
                  onRun={handleRunOptimization}
                  onClear={clearOptimization}
                  onExport={handleExport}
                  hasResults={optimizationResults && optimizationResults.length > 0}
                  loading={optimizationLoading}
                />
              )}
            </Accordion>
          </div>
        </Sidebar>
      }
    >
      <GeospatialMap
        networkData={networkData}
        candidates={visibleCandidates}
        layers={layers}
        salesRange={salesRange}
        onStoreClick={selectStore}
      />

      <DetailPanel
        store={selectedStore}
        isOpen={detailPanelOpen}
        onClose={closeDetailPanel}
        mode={mode}
      />
    </AppLayout>
  )
}

export default App
