import * as React from 'react'
import { Toggle } from './Toggle'
import { cn } from '../../lib/utils'

/**
 * LayerToggle - A toggle switch with icon and label for map layers
 */
function LayerToggle({
  icon,
  label,
  checked,
  onChange,
  disabled = false,
  className,
}) {
  return (
    <label
      className={cn(
        'flex items-center justify-between gap-3 py-2 px-1 rounded-md',
        'transition-colors cursor-pointer',
        disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50',
        className
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        {icon && (
          <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
            {icon}
          </span>
        )}
        <span className="text-sm text-gray-700 truncate">{label}</span>
      </div>
      <Toggle
        checked={checked}
        onCheckedChange={onChange}
        disabled={disabled}
      />
    </label>
  )
}

export { LayerToggle }
