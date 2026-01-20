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

/**
 * Format currency value (e.g., $1.2M, $500K, $1,234)
 */
export function formatCurrency(amount) {
  if (amount >= 1000000) {
    return '$' + (amount / 1000000).toFixed(1) + 'M'
  } else if (amount >= 1000) {
    return '$' + (amount / 1000).toFixed(0) + 'K'
  }
  return '$' + Math.round(amount).toLocaleString()
}

/**
 * Format percentage (e.g., 85.5%)
 */
export function formatPercent(value, decimals = 1) {
  return value.toFixed(decimals) + '%'
}

/**
 * Format population (e.g., 45.2K)
 */
export function formatPopulation(pop) {
  if (pop >= 1000000) {
    return (pop / 1000000).toFixed(1) + 'M'
  } else if (pop >= 1000) {
    return (pop / 1000).toFixed(1) + 'K'
  }
  return pop.toLocaleString()
}

/**
 * Check if a point is within Leaflet bounds
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {object} bounds - Leaflet bounds object with _southWest and _northEast
 * @returns {boolean}
 */
export function isPointInBounds(lat, lng, bounds) {
  if (!bounds || !bounds._southWest || !bounds._northEast) return true

  const sw = bounds._southWest
  const ne = bounds._northEast

  return (
    lat >= sw.lat &&
    lat <= ne.lat &&
    lng >= sw.lng &&
    lng <= ne.lng
  )
}

/**
 * Filter an array of locations by map viewport bounds
 * @param {Array} items - Array of items with latitude/longitude properties
 * @param {object} bounds - Leaflet bounds object
 * @returns {Array} - Filtered items within bounds
 */
export function filterByBounds(items, bounds) {
  if (!items || !Array.isArray(items)) return []
  if (!bounds) return items

  return items.filter(item =>
    isPointInBounds(item.latitude, item.longitude, bounds)
  )
}
