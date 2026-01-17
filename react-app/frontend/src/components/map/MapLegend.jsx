import React from 'react'
import { formatSales } from '../../lib/utils'

/**
 * Map legend showing marker colors
 */
export function MapLegend() {
  const items = [
    {
      label: 'Expansion Candidates',
      color: '#ef4444',
      borderColor: '#dc2626',
    },
    {
      label: 'Demand Heatmap - H3',
      gradient: true,
      borderColor: '#dc2626',
    },
    {
      label: 'Current Stores',
      color: '#34d399',
      borderColor: '#10b981',
    },
    {
      label: 'Potential Partner Stores',
      color: '#60a5fa',
      borderColor: '#3b82f6',
    },
    {
      label: 'Competitors',
      color: '#a855f7',
      borderColor: '#9333ea',
    },
  ]

  return (
    <div className="absolute top-6 right-6 bg-white p-4 rounded-lg border border-gray-200 shadow-md z-[500]">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">Map Legend</h4>
      <div className="space-y-2">
        {items.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm text-gray-700">
            <span
              className="w-3 h-3 rounded-full border-2"
              style={{
                background: item.gradient
                  ? 'linear-gradient(135deg, #fff 0%, #ff6666 50%, #ff0000 100%)'
                  : item.color,
                borderColor: item.borderColor,
              }}
            />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Sales gradient legend
 */
export function SalesGradientLegend({ salesRange }) {
  return (
    <div className="absolute bottom-8 right-6 bg-white p-3 rounded-lg border border-gray-200 shadow-md z-[500] min-w-[180px]">
      <div className="text-xs font-semibold text-gray-700 mb-2">
        Predicted Annual Sales
      </div>
      <div
        className="h-3 rounded border border-gray-200 mb-1"
        style={{
          background: 'linear-gradient(to right, rgb(255, 255, 255), rgb(255, 200, 200), rgb(255, 100, 100), rgb(255, 0, 0))',
        }}
      />
      <div className="flex justify-between text-[10px] text-gray-500">
        <span>{formatSales(salesRange.min)}</span>
        <span>{formatSales(salesRange.max)}</span>
      </div>
    </div>
  )
}
