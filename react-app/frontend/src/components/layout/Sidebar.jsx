import React from 'react'
import { cn } from '../../lib/utils'
import {
  Eye, TrendingUp, BarChart3, Layers, SlidersHorizontal,
  Sparkles, Users, Store, Building2, MapPin, Building,
  Hexagon, Circle, DollarSign, Target, Download, Play, Loader2
} from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs'
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '../ui/Accordion'
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
 * Mode tabs for switching between Overview and Expansion
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
 * Expansion Metrics Section
 */
export function ExpansionMetricsSection({ candidates, visibleCandidates }) {
  const totalPredictedSales = candidates?.reduce((sum, c) => sum + (c.predicted_annual_sales || 0), 0) || 0
  const avgPredictedSales = candidates?.length > 0 ? totalPredictedSales / candidates.length : 0

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
          <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-red-500" />
              <span className="text-sm text-gray-700">Expansion Candidates</span>
            </div>
            <span className="font-bold text-red-600">{(candidates?.length || 0).toLocaleString()}</span>
          </div>

          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-blue-500" />
              <span className="text-sm text-gray-700">Total Predicted Sales</span>
            </div>
            <span className="font-bold text-blue-600">{formatCurrency(totalPredictedSales)}</span>
          </div>

          <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-purple-500" />
              <span className="text-sm text-gray-700">Avg Predicted Sales</span>
            </div>
            <span className="font-bold text-purple-600">{formatCurrency(avgPredictedSales)}</span>
          </div>

          {visibleCandidates && visibleCandidates.length !== candidates?.length && (
            <div className="pt-2 border-t border-gray-200 mt-2">
              <p className="text-xs text-gray-500 mb-2">Currently Visible</p>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Filtered Candidates</span>
                <span className="font-semibold text-gray-900">{visibleCandidates.length.toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}

/**
 * Partnership Recommendations Section
 */
export function PartnershipRecommendationsSection() {
  // Placeholder data - will be updated with actual partner data
  const recommendations = [
    {
      rank: 1,
      name: '7-Eleven',
      coverage: '342 locations',
      rationale: 'High store density in target areas, existing food service infrastructure, 24/7 operations align with late-night demand patterns.',
      color: 'blue',
      icon: Store,
    },
    {
      rank: 2,
      name: 'Walmart',
      coverage: '187 locations',
      rationale: 'High foot traffic, family-oriented demographics match LCE customer base, existing deli/food prep areas available.',
      color: 'emerald',
      icon: Building2,
    },
    {
      rank: 3,
      name: 'Open New Store',
      coverage: '89 high-potential locations',
      rationale: 'Locations with predicted sales above $1.5M and no existing partners within 3 miles. Higher investment but full brand control.',
      color: 'orange',
      icon: MapPin,
    },
  ]

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
          Top recommended fulfillment strategies for expansion
        </p>

        <div className="space-y-3">
          {recommendations.map((rec) => {
            const colors = colorClasses[rec.color]
            const Icon = rec.icon
            return (
              <Card key={rec.rank} className={cn('border-l-4 p-3', colors.border, colors.bg)}>
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold flex-shrink-0',
                    colors.badge
                  )}>
                    {rec.rank}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={cn('w-4 h-4', colors.icon)} />
                      <span className={cn('font-semibold', colors.title)}>{rec.name}</span>
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
          * Recommendations update based on visible map area and filters
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
              checked={layers.convenience}
              onChange={() => onToggle('convenience')}
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
 * Filters Section
 */
export function FiltersSection({ filters, ranges, onChange, hasActiveFilters }) {
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
              <span className="font-medium text-gray-900">{formatCurrency(filters.minSales || ranges.sales.min)}</span>
            </div>
            <input
              type="range"
              min={ranges.sales.min}
              max={ranges.sales.max}
              value={filters.minSales || ranges.sales.min}
              onChange={(e) => onChange({ ...filters, minSales: Number(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-orange"
            />
          </div>

          {/* Min Population Filter */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Min Population</span>
              <span className="font-medium text-gray-900">{formatPopulation(filters.minPopulation || ranges.population.min)}</span>
            </div>
            <input
              type="range"
              min={ranges.population.min}
              max={ranges.population.max}
              value={filters.minPopulation || ranges.population.min}
              onChange={(e) => onChange({ ...filters, minPopulation: Number(e.target.value) })}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-orange"
            />
          </div>

          <button
            onClick={() => onChange({ minSales: null, minPopulation: null })}
            className="w-full text-sm text-gray-500 hover:text-brand-orange transition-colors py-1"
          >
            Reset Filters
          </button>
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
