import React, { useState } from 'react'
import { cn } from '../../lib/utils'
import { StepIndicator, Divider } from '../layout/Sidebar'
import { PARAM_GRID } from '../../hooks/useMapState'

/**
 * Select control component
 */
function Select({ label, value, options, onChange }) {
  return (
    <div className="mb-4">
      <label className="block text-sm text-gray-700 mb-2 font-medium">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={cn(
          'w-full px-3 py-2 border border-gray-200 rounded-md text-sm',
          'bg-white cursor-pointer',
          'focus:outline-none focus:ring-2 focus:ring-brand-orange/20 focus:border-brand-orange'
        )}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

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
 * Button component
 */
function Button({ children, onClick, variant = 'primary', disabled, className }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full py-3 rounded-md text-sm font-semibold transition-all',
        variant === 'primary' && 'bg-brand-orange text-white hover:bg-brand-orange-dark',
        variant === 'secondary' && 'bg-white text-brand-orange border border-brand-orange hover:bg-brand-orange hover:text-white',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {children}
    </button>
  )
}

/**
 * Optimization controls
 */
export function OptimizationControls({
  params,
  onChange,
  onRun,
  onClear,
  onExport,
  hasResults,
  loading,
}) {
  const maxStoreOptions = PARAM_GRID.maxStores.map((v) => ({
    value: v,
    label: `${v} stores`,
  }))

  return (
    <div>
      <Divider />
      <StepIndicator number={2} label="Optimize" />

      <Select
        label="Maximum New Stores"
        value={params.maxStores}
        options={maxStoreOptions}
        onChange={(value) => onChange({ maxStores: value })}
      />

      <Slider
        label="Min Distance Between New (miles)"
        value={params.minDistNew}
        min={1}
        max={3}
        step={0.5}
        onChange={(value) => onChange({ minDistNew: value })}
        formatValue={(v) => `${v} mi`}
      />

      <Slider
        label="Min Distance from Existing (miles)"
        value={params.minDistExisting}
        min={1}
        max={3}
        step={0.5}
        onChange={(value) => onChange({ minDistExisting: value })}
        formatValue={(v) => `${v} mi`}
      />

      <div className="mt-4 space-y-2">
        <Button onClick={onRun} disabled={loading}>
          {loading ? 'Running...' : 'Run Optimization'}
        </Button>

        {hasResults && (
          <Button variant="secondary" onClick={onClear}>
            Clear Results
          </Button>
        )}

        <Button variant="secondary" onClick={onExport}>
          Download
        </Button>
      </div>
    </div>
  )
}

export default OptimizationControls
