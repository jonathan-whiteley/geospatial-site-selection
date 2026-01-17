import React from 'react'
import { cn } from '../../lib/utils'
import { SectionHeader } from '../layout/Sidebar'

/**
 * Checkbox control component
 */
function Checkbox({ id, label, checked, onChange, className }) {
  return (
    <div className={cn('flex items-center gap-2 cursor-pointer', className)}>
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-[18px] h-[18px] cursor-pointer accent-brand-orange"
      />
      <label htmlFor={id} className="text-sm text-gray-700 cursor-pointer">
        {label}
      </label>
    </div>
  )
}

/**
 * Layer toggle controls
 */
export function LayerToggles({ layers, onToggle }) {
  const layerConfig = [
    { key: 'candidates', label: 'Expansion Candidates' },
    { key: 'h3Hexagons', label: 'Demand Heatmap - H3' },
    { key: 'currentStores', label: 'Current Stores' },
    { key: 'candidateIsochrones', label: 'Candidate Trade Areas' },
    { key: 'convenience', label: 'Potential Partner Stores' },
    { key: 'competitors', label: 'Competitors' },
  ]

  return (
    <div>
      <SectionHeader noBorder>Layer Controls</SectionHeader>
      <div className="flex flex-col gap-3">
        {layerConfig.map(({ key, label }) => (
          <Checkbox
            key={key}
            id={`layer-${key}`}
            label={label}
            checked={layers[key] || false}
            onChange={() => onToggle(key)}
          />
        ))}
      </div>
    </div>
  )
}

export default LayerToggles
