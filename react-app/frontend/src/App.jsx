import React, { useMemo, useCallback } from 'react'
import { AppLayout, AppHeader } from './components/layout/AppLayout'
import { Sidebar, ModeTabs, Divider } from './components/layout/Sidebar'
import { CurrentNetworkMetrics, ExpansionMetrics } from './components/layout/MetricsPanel'
import { GeospatialMap } from './components/map/GeospatialMap'
import { DetailPanel } from './components/panels/DetailPanel'
import { LayerToggles } from './components/controls/LayerToggles'
import { FilterSliders } from './components/controls/FilterSliders'
import { OptimizationControls } from './components/controls/OptimizationControls'
import { useMapState } from './hooks/useMapState'
import { useStoreData } from './hooks/useStoreData'
import { useOptimization } from './hooks/useOptimization'

// Logo path
const LOGO_SRC = '/logo.png'

/**
 * Chat mode placeholder
 */
function ChatPlaceholder() {
  return (
    <div className="text-center py-10">
      <div className="text-5xl mb-4">Chat</div>
      <div className="text-base text-gray-500 mb-2">Chat Assistant</div>
      <div className="text-sm text-gray-400">Coming soon...</div>
    </div>
  )
}

/**
 * Loading spinner
 */
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-brand-orange" />
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
    optimizationCache,
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

    // Apply filters
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

    // Define columns
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

    // Build CSV
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

    // Download
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

    console.log(`Exported ${candidates.length} candidates to ${filename}`)
  }, [visibleCandidates, optimizationResults])

  // Render sidebar content based on mode
  const renderSidebarContent = () => {
    if (mode === 'chat') {
      return <ChatPlaceholder />
    }

    return (
      <>
        <LayerToggles layers={layers} onToggle={toggleLayer} />

        {mode === 'expansion' && (
          <>
            <Divider />
            <FilterSliders
              filters={filters}
              ranges={{
                sales: salesRange,
                population: populationRange,
              }}
              onChange={updateFilters}
            />
            <OptimizationControls
              params={optimizationParams}
              onChange={updateOptimizationParams}
              onRun={handleRunOptimization}
              onClear={clearOptimization}
              onExport={handleExport}
              hasResults={optimizationResults && optimizationResults.length > 0}
              loading={optimizationLoading}
            />
          </>
        )}

        {mode === 'current' ? (
          <CurrentNetworkMetrics
            networkData={networkData}
            expansionData={expansionData}
            visibleCandidates={visibleCandidates}
          />
        ) : mode === 'expansion' ? (
          <ExpansionMetrics visibleCandidates={visibleCandidates} />
        ) : null}
      </>
    )
  }

  // Show loading state
  if (dataLoading) {
    return (
      <AppLayout
        header={<AppHeader logoSrc={LOGO_SRC} />}
        sidebar={
          <Sidebar>
            <ModeTabs activeMode={mode} onModeChange={setMode} />
            <LoadingSpinner />
          </Sidebar>
        }
      >
        <LoadingSpinner />
      </AppLayout>
    )
  }

  // Show error state
  if (dataError) {
    return (
      <AppLayout
        header={<AppHeader logoSrc={LOGO_SRC} />}
        sidebar={
          <Sidebar>
            <ModeTabs activeMode={mode} onModeChange={setMode} />
            <div className="text-red-500 p-4">
              Error loading data: {dataError}
            </div>
          </Sidebar>
        }
      >
        <div className="flex items-center justify-center h-full text-red-500">
          Failed to load map data
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout
      header={<AppHeader logoSrc={LOGO_SRC} />}
      sidebar={
        <Sidebar>
          <ModeTabs activeMode={mode} onModeChange={setMode} />
          {renderSidebarContent()}
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
