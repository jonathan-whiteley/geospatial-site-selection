import React from 'react'
import { Building2, MapPin, Store, Building, Users } from 'lucide-react'
import { formatSales } from '../../lib/utils'

/**
 * Legend item component
 */
function LegendItem({ color, label, icon: Icon, haze, crosshair }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {crosshair ? (
        <svg width="10" height="10" viewBox="-5 -5 10 10" className="flex-shrink-0">
          <line x1="-4" y1="0" x2="4" y2="0" stroke={color} strokeWidth="1.5" opacity="0.7"/>
          <line x1="0" y1="-4" x2="0" y2="4" stroke={color} strokeWidth="1.5" opacity="0.7"/>
        </svg>
      ) : (
        <span
          className={`${haze ? 'w-2 h-2' : 'w-2.5 h-2.5'} rounded-full flex-shrink-0`}
          style={{
            backgroundColor: color,
            border: haze ? 'none' : '1.5px solid white',
            opacity: haze ? 0.75 : 1,
            boxShadow: haze ? 'none' : '0 1px 2px rgba(0,0,0,0.1)',
            marginLeft: haze ? '1px' : '0',
            marginRight: haze ? '1px' : '0',
          }}
        />
      )}
      {Icon && <Icon className="w-3 h-3 text-gray-400" />}
      <span className="text-gray-600">{label}</span>
    </div>
  )
}

/**
 * Gradient legend item for H3 heatmap
 */
function GradientLegendItem({ label }) {
  return (
    <div className="flex items-center gap-2.5 text-sm">
      <span
        className="w-3.5 h-3.5 rounded-sm shadow-sm flex-shrink-0"
        style={{
          background: 'linear-gradient(135deg, #fff 0%, #fca5a5 50%, #ef4444 100%)',
          border: '1.5px solid #ef4444',
        }}
      />
      <span className="text-gray-600">{label}</span>
    </div>
  )
}

/**
 * Map legend showing layer colors - modernized with glassmorphism
 */
export function MapLegend() {
  const items = [
    {
      label: 'Current Stores',
      color: '#10b981',
      icon: Building2,
    },
    {
      label: 'Customer Locations',
      color: '#374151',
      haze: true,
      icon: Users,
    },
    {
      label: 'Expansion Candidates',
      color: '#ef4444',
      icon: MapPin,
    },
    {
      label: 'Partner Stores',
      color: '#3b82f6',
      icon: Store,
    },
    {
      label: 'Competitors',
      color: '#a855f7',
      icon: Building,
    },
  ]

  return (
    <div className="absolute top-4 right-4 glass-panel rounded-md shadow-glass p-2.5 z-[500]">
      <h4 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
        <span className="w-0.5 h-3 bg-brand-orange rounded-full" />
        Map Layers
      </h4>
      <div className="space-y-1.5">
        {items.map((item, idx) =>
          item.gradient ? (
            <GradientLegendItem key={idx} label={item.label} />
          ) : (
            <LegendItem
              key={idx}
              color={item.color}
              label={item.label}
              icon={item.icon}
              haze={item.haze}
              crosshair={item.crosshair}
            />
          )
        )}
      </div>
    </div>
  )
}

/**
 * Sales gradient legend - modernized
 */
export function SalesGradientLegend({ salesRange }) {
  return (
    <div className="absolute bottom-6 right-4 glass-panel rounded-lg shadow-glass p-3 z-[500] min-w-[200px]">
      <div className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-2">
        <span className="w-1 h-3 bg-red-500 rounded-full" />
        Predicted Annual Sales
      </div>
      <div
        className="h-3 rounded-md mb-1.5 shadow-inner"
        style={{
          background: 'linear-gradient(to right, rgb(255, 255, 255), rgb(254, 202, 202), rgb(252, 165, 165), rgb(248, 113, 113), rgb(239, 68, 68))',
          border: '1px solid #e5e7eb',
        }}
      />
      <div className="flex justify-between text-[10px] text-gray-500 font-medium">
        <span>{formatSales(salesRange.min)}</span>
        <span className="text-gray-400">|</span>
        <span>{formatSales(salesRange.max)}</span>
      </div>
    </div>
  )
}
