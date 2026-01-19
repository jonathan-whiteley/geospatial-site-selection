import * as React from 'react'
import { cn } from '../../lib/utils'

/**
 * MetricCard - Display a KPI metric with label, value, and optional icon/trend
 */
function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  trendDirection,
  className,
  variant = 'default',
  size = 'default',
}) {
  const variants = {
    default: 'bg-white border border-gray-200',
    emerald: 'bg-emerald-50 border-l-4 border-l-emerald-500 border-y border-r border-gray-200',
    blue: 'bg-blue-50 border-l-4 border-l-blue-500 border-y border-r border-gray-200',
    purple: 'bg-purple-50 border-l-4 border-l-purple-500 border-y border-r border-gray-200',
    amber: 'bg-amber-50 border-l-4 border-l-amber-500 border-y border-r border-gray-200',
    orange: 'bg-orange-50 border-l-4 border-l-brand-orange border-y border-r border-gray-200',
    red: 'bg-red-50 border-l-4 border-l-red-500 border-y border-r border-gray-200',
  }

  const sizes = {
    small: 'p-2',
    default: 'p-3',
    large: 'p-4',
  }

  const valueColors = {
    default: 'text-gray-900',
    emerald: 'text-emerald-700',
    blue: 'text-blue-700',
    purple: 'text-purple-700',
    amber: 'text-amber-700',
    orange: 'text-brand-orange',
    red: 'text-red-700',
  }

  return (
    <div
      className={cn(
        'rounded-lg shadow-sm',
        variants[variant],
        sizes[size],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className={cn(
            'font-bold truncate',
            size === 'small' ? 'text-lg' : 'text-xl',
            valueColors[variant]
          )}>
            {value}
          </p>
          <p className={cn(
            'text-gray-500 truncate',
            size === 'small' ? 'text-xs' : 'text-sm'
          )}>
            {label}
          </p>
          {trend && (
            <p className={cn(
              'text-xs mt-1',
              trendDirection === 'up' ? 'text-emerald-600' : 'text-red-600'
            )}>
              {trendDirection === 'up' ? '↑' : '↓'} {trend}
            </p>
          )}
        </div>
        {Icon && (
          <div className={cn(
            'flex-shrink-0 ml-2',
            variant === 'default' ? 'text-gray-400' : valueColors[variant]
          )}>
            <Icon className={size === 'small' ? 'w-4 h-4' : 'w-5 h-5'} />
          </div>
        )}
      </div>
    </div>
  )
}

export { MetricCard }
