import React from 'react'
import { cn } from '../../lib/utils'
import { StepIndicator } from '../layout/Sidebar'

/**
 * Slider control component
 */
function Slider({ label, value, min, max, step, onChange, formatValue }) {
  return (
    <div className="mb-4">
      <label className="block text-sm text-gray-700 mb-2 font-medium">
        {label}
      </label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-orange"
      />
      <div className="text-xs text-gray-500 mt-1">
        {formatValue ? formatValue(value) : value}
      </div>
    </div>
  )
}

/**
 * Filter sliders for expansion candidates
 */
export function FilterSliders({ filters, ranges, onChange }) {
  return (
    <div>
      <StepIndicator number={1} label="Refine" />

      <Slider
        label="Minimum Annual Sales"
        value={filters.minSales || ranges.sales.min}
        min={ranges.sales.min}
        max={ranges.sales.max}
        step={1000}
        onChange={(value) => onChange({ minSales: value })}
        formatValue={(v) => `$${v.toLocaleString()}`}
      />

      <Slider
        label="Minimum Population"
        value={filters.minPopulation || ranges.population.min}
        min={Math.round(ranges.population.min)}
        max={Math.round(ranges.population.max)}
        step={100}
        onChange={(value) => onChange({ minPopulation: Math.round(value) })}
        formatValue={(v) => Math.round(v).toLocaleString()}
      />
    </div>
  )
}

export default FilterSliders
