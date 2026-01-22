import React from 'react'
import { X, MapPin, DollarSign, Users, Building2, Store, Building } from 'lucide-react'
import { cn, formatNumber, formatCurrency } from '../../lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'

/**
 * Metric card for detail panel
 */
function MetricCard({ label, value, icon: Icon }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-3">
      {Icon && <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />}
      <div className="min-w-0">
        <div className="text-xs text-gray-500">{label}</div>
        <div className="text-sm font-semibold text-gray-700 truncate">{value}</div>
      </div>
    </div>
  )
}

/**
 * Partner strategy recommendation card
 */
function PartnerStrategyCard({ storeData }) {
  return (
    <Card className="border-l-4 border-l-blue-500 bg-blue-50/50">
      <CardContent className="py-4">
        <div className="flex items-center gap-2 mb-3">
          <Store className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-blue-900">Partner Strategy</span>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          Partner with <strong>{storeData.convenience_store_name || '7-Eleven'}</strong> in{' '}
          {storeData.convenience_city || 'nearby location'}
        </p>
        <div className="bg-white/60 rounded-lg p-3 space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Drive Time</span>
            <span className="font-semibold text-gray-700">{storeData.convenience_drive_time || 5} min</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Strategy</span>
            <span className="font-semibold text-gray-700">Micro-fulfillment</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          <strong>Rationale:</strong> Existing foot traffic and infrastructure reduces setup costs.
          Ideal for quick market entry with lower capital investment.
        </p>
      </CardContent>
    </Card>
  )
}

/**
 * New build strategy recommendation card
 */
function NewBuildStrategyCard({ storeData }) {
  return (
    <Card className="border-l-4 border-l-brand-orange bg-orange-50/50">
      <CardContent className="py-4">
        <div className="flex items-center gap-2 mb-3">
          <Building className="w-5 h-5 text-brand-orange" />
          <span className="font-semibold text-orange-900">New Build Strategy</span>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          {storeData.min_distance_to_existing
            ? `${storeData.min_distance_to_existing.toFixed(1)} miles`
            : 'No LCE stores'
          } to nearest existing location
        </p>
        <div className="bg-white/60 rounded-lg p-3 space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Nearest Store</span>
            <span className="font-semibold text-gray-700">#{storeData.nearest_existing_store || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Strategy</span>
            <span className="font-semibold text-gray-700">Standalone Build</span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-3">
          <strong>Rationale:</strong> High predicted sales of {formatCurrency(storeData.predicted_annual_sales || 0)} justifies
          standalone investment. Full brand control and optimal customer experience.
        </p>
      </CardContent>
    </Card>
  )
}

/**
 * Detail panel component - slides from LEFT
 */
export function DetailPanel({ store, isOpen, onClose, mode }) {
  if (!store) return null

  const isExpansionCandidate = store.predicted_annual_sales !== undefined
  const showFulfillmentRecommendation = isExpansionCandidate && mode === 'expansion'
  const isPartner = store.fulfillment_strategy === 'partner' || store.within_convenience_isochrone

  return (
    <div
      className={cn(
        'fixed left-0 top-16 w-96 h-[calc(100vh-64px)]',
        'bg-white border-r border-gray-200 shadow-xl',
        'transform transition-transform duration-300 ease-out z-[1001]',
        'flex flex-col',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      {/* Header with orange accent */}
      <div className="sticky top-0 bg-white border-b border-l-4 border-l-brand-orange px-4 py-4 z-10">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-sm font-medium text-gray-500">Store Details</h2>
            <p className="text-xl text-brand-orange font-semibold mt-0.5">
              #{store.store_number || 'N/A'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-400 hover:text-gray-600" />
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Location */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Location
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-semibold text-gray-900">
              {store.city || 'N/A'}, {store.state || 'N/A'}
            </p>
          </CardContent>
        </Card>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          {isExpansionCandidate && (
            <MetricCard
              label="Predicted Sales"
              value={formatCurrency(store.predicted_annual_sales || 0)}
              icon={DollarSign}
            />
          )}

          {store.annual_sales > 0 && (
            <MetricCard
              label="Annual Sales"
              value={formatCurrency(store.annual_sales || 0)}
              icon={DollarSign}
            />
          )}

          <MetricCard
            label="Population"
            value={formatNumber(store.population || 0)}
            icon={Users}
          />

          {store.total_poi_count !== undefined && (
            <MetricCard
              label="POI Count"
              value={formatNumber(store.total_poi_count || 0)}
              icon={Building2}
            />
          )}
        </div>

        {/* Fulfillment Strategy */}
        {showFulfillmentRecommendation && (
          <div className="space-y-3">
            <h3 className="font-medium text-gray-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-brand-orange" />
              Fulfillment Strategy
            </h3>

            {isPartner ? (
              <PartnerStrategyCard storeData={store} />
            ) : (
              <NewBuildStrategyCard storeData={store} />
            )}
          </div>
        )}

        {/* Additional info for non-expansion mode */}
        {!showFulfillmentRecommendation && store.total_poi_count !== undefined && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Store Trade Area
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                This store serves a population of {formatNumber(store.population || 0)} with{' '}
                {formatNumber(store.total_poi_count || 0)} points of interest in the trade area within 5 minute drive time.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default DetailPanel
