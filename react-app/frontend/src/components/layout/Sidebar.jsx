import { cn } from '../../lib/utils'
import {
  Eye, TrendingUp, BarChart3, Layers, SlidersHorizontal,
  Sparkles, Users, Store, Building2, MapPin, Building,
  Hexagon, Circle, DollarSign, Download, Play, Loader2
} from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '../ui/Tabs'
import { AccordionItem, AccordionTrigger, AccordionContent } from '../ui/Accordion'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { LayerToggle } from '../ui/LayerToggle'
import { formatCurrency, formatPopulation } from '../../lib/utils'

/**
 * Sidebar container
 */
export function Sidebar({ children, className }) {
  return (
    <aside
      className={cn(
        'w-80 bg-white border-r border-gray-200 flex flex-col h-full',
        className
      )}
    >
      {children}
    </aside>
  )
}

/**
 * Static header for Expansion Planning mode (replaces ModeTabs)
 */
export function ExpansionHeader() {
  return (
    <div className="p-4 border-b border-gray-100">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-brand-orange" />
        <h2 className="text-lg font-semibold text-gray-900">Expansion Planning</h2>
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Analyze candidates and partnership opportunities
      </p>
    </div>
  )
}

/**
 * Mode tabs for switching between Overview and Expansion (deprecated, kept for compatibility)
 */
export function ModeTabs({ activeMode, onModeChange }) {
  return (
    <div className="p-3 border-b border-gray-100">
      <Tabs value={activeMode} onValueChange={onModeChange} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="current">
            <Eye className="w-4 h-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="expansion">
            <TrendingUp className="w-4 h-4 mr-2" />
            Expansion
          </TabsTrigger>
        </TabsList>
      </Tabs>
    </div>
  )
}

/**
 * Expansion Metrics Section - Shows viewport-based counts
 */
export function ExpansionMetricsSection({ candidates, viewportCandidates, visibleCandidates, hasActiveFilters }) {
  // Calculate metrics for viewport candidates
  const viewportCount = viewportCandidates?.length || 0
  const visibleCount = visibleCandidates?.length || 0
  const totalCount = candidates?.length || 0

  const visiblePredictedSales = visibleCandidates?.reduce((sum, c) => sum + (c.predicted_annual_sales || 0), 0) || 0
  const avgPredictedSales = visibleCount > 0 ? visiblePredictedSales / visibleCount : 0

  // Calculate 5-min hunger satisfaction with partner (candidates within partner isochrone / total)
  const candidatesWithPartner = visibleCandidates?.filter(c =>
    c.within_convenience_isochrone || c.fulfillment_strategy === 'partner'
  ).length || 0
  const partnerCoveragePercent = visibleCount > 0
    ? ((candidatesWithPartner / visibleCount) * 100).toFixed(1)
    : '0.0'

  return (
    <AccordionItem value="metrics">
      <AccordionTrigger>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-brand-orange" />
          <span className="font-medium">Expansion Metrics</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-3">
          {/* Candidates in View */}
          <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-red-500" />
              <div className="flex flex-col">
                <span className="text-sm text-gray-700">Candidates in View</span>
                {hasActiveFilters && (
                  <span className="text-xs text-gray-500">
                    {viewportCount.toLocaleString()} before filters
                  </span>
                )}
              </div>
            </div>
            <span className="font-bold text-red-600">{visibleCount.toLocaleString()}</span>
          </div>

          {/* Total Predicted Sales (for visible candidates) */}
          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-blue-500" />
              <span className="text-sm text-gray-700">Total Predicted Sales</span>
            </div>
            <span className="font-bold text-blue-600">{formatCurrency(visiblePredictedSales)}</span>
          </div>

          {/* Average Predicted Sales */}
          <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-purple-500" />
              <span className="text-sm text-gray-700">Avg Predicted Sales</span>
            </div>
            <span className="font-bold text-purple-600">{formatCurrency(avgPredictedSales)}</span>
          </div>

          {/* 5-min Hunger Satisfaction with Partner */}
          <div className="flex justify-between items-center p-3 bg-emerald-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Store className="w-4 h-4 text-emerald-500" />
              <div className="flex flex-col">
                <span className="text-sm text-gray-700">5-min Partner Coverage</span>
                <span className="text-xs text-gray-500">
                  {candidatesWithPartner.toLocaleString()} of {visibleCount.toLocaleString()} candidates
                </span>
              </div>
            </div>
            <span className="font-bold text-emerald-600">{partnerCoveragePercent}%</span>
          </div>

          {/* Global context */}
          <div className="pt-2 border-t border-gray-200 mt-2">
            <p className="text-xs text-gray-400">
              {totalCount.toLocaleString()} total candidates across all regions
            </p>
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Partnership Recommendations Section - Calculates recommendations dynamically
 */
export function PartnershipRecommendationsSection({ partnerStores = [], candidates = [] }) {
  // Group partners by brand name
  const partnersByBrand = partnerStores.reduce((acc, store) => {
    const brand = store.name || 'Unknown'
    if (!acc[brand]) {
      acc[brand] = []
    }
    acc[brand].push(store)
    return acc
  }, {})

  // Sort brands by count and get top 2
  const sortedBrands = Object.entries(partnersByBrand)
    .sort(([, a], [, b]) => b.length - a.length)
    .slice(0, 2)

  // Count candidates without partner coverage (potential new store locations)
  const candidatesWithoutPartner = candidates.filter(c => !c.within_convenience_isochrone).length

  // Build dynamic recommendations
  const recommendations = []
  const colors = ['blue', 'emerald', 'orange']
  const icons = [Store, Building2, MapPin]

  sortedBrands.forEach(([brand, stores], idx) => {
    recommendations.push({
      rank: idx + 1,
      name: brand,
      coverage: `${stores.length} location${stores.length !== 1 ? 's' : ''} in view`,
      rationale: `Partner stores within current viewport. Consider co-location opportunities for rapid market entry.`,
      color: colors[idx],
      icon: icons[idx],
    })
  })

  // Always add "Open New Store" option
  recommendations.push({
    rank: recommendations.length + 1,
    name: 'Open New Store',
    coverage: `${candidatesWithoutPartner} high-potential location${candidatesWithoutPartner !== 1 ? 's' : ''}`,
    rationale: 'Candidates outside existing partner trade areas. Higher investment but full brand control and market presence.',
    color: 'orange',
    icon: MapPin,
  })

  const colorClasses = {
    blue: {
      border: 'border-l-blue-500',
      bg: 'bg-blue-50/50',
      badge: 'bg-blue-500',
      icon: 'text-blue-600',
      title: 'text-blue-900',
    },
    emerald: {
      border: 'border-l-emerald-500',
      bg: 'bg-emerald-50/50',
      badge: 'bg-emerald-500',
      icon: 'text-emerald-600',
      title: 'text-emerald-900',
    },
    orange: {
      border: 'border-l-brand-orange',
      bg: 'bg-orange-50/50',
      badge: 'bg-brand-orange',
      icon: 'text-brand-orange',
      title: 'text-orange-900',
    },
  }

  const totalPartners = partnerStores.length

  return (
    <AccordionItem value="recommendations">
      <AccordionTrigger>
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-brand-orange" />
          <span className="font-medium">Partnership Recommendations</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <p className="text-xs text-gray-500 mb-3">
          {totalPartners > 0
            ? `${totalPartners} partner store${totalPartners !== 1 ? 's' : ''} in current view`
            : 'Pan/zoom to see partner stores'}
        </p>

        <div className="space-y-3">
          {recommendations.map((rec) => {
            const recColors = colorClasses[rec.color]
            const Icon = rec.icon
            return (
              <Card key={rec.rank} className={cn('border-l-4 p-3', recColors.border, recColors.bg)}>
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold flex-shrink-0',
                    recColors.badge
                  )}>
                    {rec.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={cn('w-4 h-4', recColors.icon)} />
                      <span className={cn('font-semibold', recColors.title)}>{rec.name}</span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">
                      <strong>Coverage:</strong> {rec.coverage}
                    </p>
                    <p className="text-xs text-gray-500">
                      <strong>Rationale:</strong> {rec.rationale}
                    </p>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <p className="text-xs text-gray-400 mt-4 italic">
          * Updates based on visible map area
        </p>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Map Layers Section
 */
export function MapLayersSection({ layers, onToggle }) {
  return (
    <AccordionItem value="layers">
      <AccordionTrigger>
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-brand-orange" />
          <span className="font-medium">Map Layers</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4">
          {/* Network Layers */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Network
            </p>
            <LayerToggle
              icon={<Building2 className="w-4 h-4 text-emerald-600" />}
              label="Current Stores"
              checked={layers.currentStores}
              onChange={() => onToggle('currentStores')}
            />
            <LayerToggle
              icon={<MapPin className="w-4 h-4 text-red-500" />}
              label="Expansion Candidates"
              checked={layers.candidates}
              onChange={() => onToggle('candidates')}
            />
          </div>

          {/* Analysis Layers */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Analysis
            </p>
            <LayerToggle
              icon={<Hexagon className="w-4 h-4 text-amber-500" />}
              label="Demand Heatmap (H3)"
              checked={layers.h3Hexagons}
              onChange={() => onToggle('h3Hexagons')}
            />
            <LayerToggle
              icon={<Circle className="w-4 h-4 text-red-400" />}
              label="Candidate Trade Areas"
              checked={layers.candidateIsochrones}
              onChange={() => onToggle('candidateIsochrones')}
            />
          </div>

          {/* Partners & Competition */}
          <div className="space-y-1">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Partners & Competition
            </p>
            <LayerToggle
              icon={<Store className="w-4 h-4 text-blue-500" />}
              label="Partner Stores"
              checked={layers.partners}
              onChange={() => onToggle('partners')}
            />
            <LayerToggle
              icon={<Building className="w-4 h-4 text-purple-500" />}
              label="Competitors"
              checked={layers.competitors}
              onChange={() => onToggle('competitors')}
            />
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Filters Section - Handles null filter values (no filter active)
 */
export function FiltersSection({ filters, ranges, onChange, hasActiveFilters }) {
  const salesFilterActive = filters.minSales !== null
  const populationFilterActive = filters.minPopulation !== null

  return (
    <AccordionItem value="filters">
      <AccordionTrigger>
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-brand-orange" />
          <span className="font-medium">Filters</span>
          {hasActiveFilters && (
            <Badge variant="secondary" className="ml-2 bg-brand-orange/10 text-brand-orange text-xs">
              Active
            </Badge>
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4">
          {/* Min Sales Filter */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Min Predicted Sales</span>
              <span className={cn(
                'font-medium',
                salesFilterActive ? 'text-gray-900' : 'text-gray-400 italic'
              )}>
                {salesFilterActive ? formatCurrency(filters.minSales) : 'Not set'}
              </span>
            </div>
            <input
              type="range"
              min={ranges.sales.min}
              max={ranges.sales.max}
              value={filters.minSales ?? ranges.sales.min}
              onChange={(e) => onChange({ ...filters, minSales: Number(e.target.value) })}
              className={cn(
                'w-full h-2 rounded-lg appearance-none cursor-pointer',
                salesFilterActive ? 'bg-brand-orange/20 accent-brand-orange' : 'bg-gray-200 accent-gray-400'
              )}
            />
          </div>

          {/* Min Population Filter */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Min Population</span>
              <span className={cn(
                'font-medium',
                populationFilterActive ? 'text-gray-900' : 'text-gray-400 italic'
              )}>
                {populationFilterActive ? formatPopulation(filters.minPopulation) : 'Not set'}
              </span>
            </div>
            <input
              type="range"
              min={ranges.population.min}
              max={ranges.population.max}
              value={filters.minPopulation ?? ranges.population.min}
              onChange={(e) => onChange({ ...filters, minPopulation: Number(e.target.value) })}
              className={cn(
                'w-full h-2 rounded-lg appearance-none cursor-pointer',
                populationFilterActive ? 'bg-brand-orange/20 accent-brand-orange' : 'bg-gray-200 accent-gray-400'
              )}
            />
          </div>

          {hasActiveFilters && (
            <button
              onClick={() => onChange({ minSales: null, minPopulation: null })}
              className="w-full text-sm text-gray-500 hover:text-brand-orange transition-colors py-2 border border-gray-200 rounded-lg hover:border-brand-orange"
            >
              Reset Filters
            </button>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Optimization Section
 */
export function OptimizationSection({
  params,
  onChange,
  onRun,
  onClear,
  onExport,
  hasResults,
  loading,
}) {
  return (
    <AccordionItem value="optimization">
      <AccordionTrigger>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-brand-orange" />
          <span className="font-medium">Optimization</span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4">
          {/* Max New Stores */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-2 block">
              Max New Stores
            </label>
            <select
              value={params.maxStores}
              onChange={(e) => onChange({ ...params, maxStores: Number(e.target.value) })}
              className="w-full p-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-orange/50"
            >
              <option value={10}>10 stores</option>
              <option value={50}>50 stores</option>
              <option value={100}>100 stores</option>
            </select>
          </div>

          {/* Min Distance Between New */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Min Distance Between New</span>
              <span className="font-medium text-gray-900">{params.minDistanceBetween} mi</span>
            </div>
            <input
              type="range"
              min={1}
              max={3}
              step={0.5}
              value={params.minDistanceBetween}
              onChange={(e) => onChange({ ...params, minDistanceBetween: Number(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-orange"
            />
          </div>

          {/* Min Distance from Existing */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Min Distance from Existing</span>
              <span className="font-medium text-gray-900">{params.minDistanceFromExisting} mi</span>
            </div>
            <input
              type="range"
              min={1}
              max={3}
              step={0.5}
              value={params.minDistanceFromExisting}
              onChange={(e) => onChange({ ...params, minDistanceFromExisting: Number(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-orange"
            />
          </div>

          {/* Action Buttons */}
          <div className="space-y-2 pt-2">
            <button
              onClick={onRun}
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Optimization
                </>
              )}
            </button>

            {hasResults && (
              <>
                <button onClick={onClear} className="btn-secondary w-full">
                  Clear Results
                </button>
                <button onClick={onExport} className="btn-outline-orange w-full">
                  <Download className="w-4 h-4" />
                  Download CSV
                </button>
              </>
            )}
          </div>
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Divider line
 */
export function Divider() {
  return <hr className="border-gray-200 my-4" />
}

/**
 * Section header (legacy support)
 */
export function SectionHeader({ children, className, noBorder }) {
  return (
    <h3
      className={cn(
        'text-xs font-semibold text-gray-500 uppercase tracking-wide',
        'mt-6 mb-3 pt-4',
        !noBorder && 'border-t border-gray-200',
        'first:mt-0 first:pt-0 first:border-0',
        className
      )}
    >
      {children}
    </h3>
  )
}

/**
 * Step indicator (legacy support)
 */
export function StepIndicator({ number, label }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-gray-50 to-gray-100 border-l-4 border-brand-orange rounded-lg my-4">
      <div className="flex items-center justify-center w-8 h-8 bg-brand-orange text-white font-bold rounded-full">
        {number}
      </div>
      <span className="text-sm font-semibold text-gray-700">
        {label}
      </span>
    </div>
  )
}
