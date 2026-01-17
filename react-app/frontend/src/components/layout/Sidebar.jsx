import React from 'react'
import { cn } from '../../lib/utils'

/**
 * Sidebar container with scrollable content
 */
export function Sidebar({ children, className }) {
  return (
    <aside
      className={cn(
        'w-80 bg-white border-r border-gray-200 overflow-y-auto',
        'h-full p-4',
        className
      )}
    >
      {children}
    </aside>
  )
}

/**
 * Mode tabs for switching between Overview, Detail, and Chat
 */
export function ModeTabs({ activeMode, onModeChange }) {
  const modes = [
    { id: 'current', label: 'Overview' },
    { id: 'expansion', label: 'Detail' },
    { id: 'chat', label: 'Chat' },
  ]

  return (
    <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
      {modes.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onModeChange(mode.id)}
          className={cn(
            'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
            activeMode === mode.id
              ? 'bg-brand-orange text-white'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-200'
          )}
        >
          {mode.label}
        </button>
      ))}
    </div>
  )
}

/**
 * Section header with optional border
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
 * Step indicator for workflow steps
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

/**
 * Divider line
 */
export function Divider() {
  return <hr className="border-gray-200 my-4" />
}
