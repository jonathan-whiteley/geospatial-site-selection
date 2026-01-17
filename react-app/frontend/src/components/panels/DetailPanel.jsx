import React from 'react'
import { X } from 'lucide-react'
import { cn, formatNumber } from '../../lib/utils'

/**
 * Stat card component
 */
function StatCard({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 mb-2">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-base font-semibold text-gray-700">{value}</div>
    </div>
  )
}

/**
 * Metric row component
 */
function MetricRow({ label, value }) {
  return (
    <div className="flex justify-between items-center mb-3">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-700">{value}</span>
    </div>
  )
}

/**
 * Recommendation card component
 */
function RecommendationCard({ isPartner, storeData }) {
  if (isPartner) {
    return (
      <div className="bg-gradient-to-br from-blue-100 to-blue-200 border-2 border-blue-500 rounded-xl p-4 my-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-900 mb-2">
          Fulfillment Recommendation
        </div>
        <div className="text-lg font-bold text-blue-900 mb-3 flex items-center gap-2">
          Partner with Convenience Store
        </div>
        <div className="text-sm text-blue-800 mb-3 leading-relaxed">
          This location falls within a 5-minute drive time of an existing convenience store,
          making it an ideal partnership opportunity.
        </div>
        <div className="bg-white/60 rounded-lg p-3 space-y-2">
          <RecommendationDetail label="Partner Store" value={storeData.convenience_store_name || '7-Eleven'} />
          <RecommendationDetail label="Location" value={storeData.convenience_city || 'N/A'} />
          <RecommendationDetail label="Drive Time" value={`${storeData.convenience_drive_time || 5} minutes`} />
          <RecommendationDetail label="Strategy" value="Micro-fulfillment" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-amber-100 to-amber-200 border-2 border-amber-500 rounded-xl p-4 my-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-amber-900 mb-2">
        Fulfillment Recommendation
      </div>
      <div className="text-lg font-bold text-amber-900 mb-3 flex items-center gap-2">
        Open New Store
      </div>
      <div className="text-sm text-amber-800 mb-3 leading-relaxed">
        This location is not within a 5-minute drive time of any existing convenience stores.
        Building a new store would provide optimal market coverage and customer access.
      </div>
      <div className="bg-white/60 rounded-lg p-3 space-y-2">
        <RecommendationDetail label="Strategy" value="New Build" />
        <RecommendationDetail label="Nearest LCE Store" value={`#${storeData.nearest_existing_store || 'N/A'}`} />
        <RecommendationDetail
          label="Distance"
          value={storeData.min_distance_to_existing
            ? `${storeData.min_distance_to_existing.toFixed(1)} miles`
            : 'N/A'
          }
        />
        <RecommendationDetail label="Opportunity" value="Capture untapped market" />
      </div>
    </div>
  )
}

/**
 * Recommendation detail row
 */
function RecommendationDetail({ label, value }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-500 font-medium">{label}</span>
      <span className="text-gray-700 font-semibold">{value}</span>
    </div>
  )
}

/**
 * Detail panel component with slide animation
 */
export function DetailPanel({ store, isOpen, onClose, mode }) {
  if (!store) return null

  const isExpansionCandidate = store.predicted_annual_sales !== undefined
  const showFulfillmentRecommendation = isExpansionCandidate && mode === 'expansion'
  const isPartner = store.fulfillment_strategy === 'partner' || store.within_convenience_isochrone

  return (
    <div
      className={cn(
        'fixed right-0 top-16 w-96 h-[calc(100vh-64px)]',
        'bg-white border-l border-gray-200 shadow-xl',
        'transform transition-transform duration-300 ease-out z-[1001]',
        'overflow-y-auto',
        isOpen ? 'translate-x-0' : 'translate-x-full'
      )}
    >
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 p-4 z-10">
        <div className="text-xs text-gray-500 uppercase tracking-wide">
          Store Details
        </div>
        <div className="text-xl text-brand-orange font-semibold mt-1">
          Store #{store.store_number || 'N/A'}
        </div>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X size={24} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Location */}
        <div className="border-b border-gray-200 pb-4 mb-4">
          <StatCard
            label="Location"
            value={`${store.city || 'N/A'}, ${store.state || 'N/A'}`}
          />
        </div>

        {/* Metrics */}
        <div className="border-b border-gray-200 pb-4 mb-4">
          {/* Annual Sales (for current stores) */}
          {store.annual_sales > 0 && (
            <MetricRow
              label="Annual Sales"
              value={`$${(store.annual_sales || 0).toLocaleString()}`}
            />
          )}

          {/* POI Count */}
          {store.total_poi_count !== undefined && (
            <MetricRow
              label="POI Count"
              value={formatNumber(store.total_poi_count || 0)}
            />
          )}

          {/* Population */}
          <MetricRow
            label="Population"
            value={formatNumber(store.population || 0)}
          />

          {/* Predicted Sales (for expansion candidates) */}
          {isExpansionCandidate && (
            <MetricRow
              label="Predicted Sales"
              value={`$${(store.predicted_annual_sales || 0).toLocaleString()}`}
            />
          )}
        </div>

        {/* Fulfillment Recommendation */}
        {showFulfillmentRecommendation && (
          <RecommendationCard isPartner={isPartner} storeData={store} />
        )}
      </div>
    </div>
  )
}

export default DetailPanel
