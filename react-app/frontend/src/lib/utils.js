import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge class names with Tailwind CSS conflict resolution
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

/**
 * Format sales value for display (e.g., $5.2M)
 */
export function formatSales(sales) {
  if (sales >= 1000000) {
    return '$' + (sales / 1000000).toFixed(1) + 'M'
  } else if (sales >= 1000) {
    return '$' + (sales / 1000).toFixed(0) + 'K'
  }
  return '$' + Math.round(sales)
}

/**
 * Get sales-based color gradient (white to red)
 */
export function getSalesColor(sales, minSales, maxSales) {
  const ratio = Math.max(0, Math.min(1, (sales - minSales) / (maxSales - minSales || 1)))
  const r = 255
  const g = Math.round(255 * (1 - ratio))
  const b = Math.round(255 * (1 - ratio))
  return `rgb(${r}, ${g}, ${b})`
}

/**
 * Calculate distance in miles between two coordinates (Haversine formula)
 */
export function distanceMiles(lat1, lon1, lat2, lon2) {
  const R = 3959 // Earth's radius in miles
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
           Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
           Math.sin(dLon/2) * Math.sin(dLon/2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
  return R * c
}

/**
 * Snap value to nearest available in grid
 */
export function snapToGrid(value, grid) {
  return grid.reduce((prev, curr) =>
    Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
  )
}

/**
 * Format a number with commas
 */
export function formatNumber(num) {
  return Math.round(num).toLocaleString()
}
