import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.markercluster'
import { formatSales, getSalesColor } from '../../lib/utils'

/**
 * Custom MarkerClusterGroup component for react-leaflet
 * Shows total sales in cluster icons with gradient color based on sales
 */
export default function MarkerClusterGroup({ children, salesRange }) {
  const map = useMap()
  const clusterRef = useRef(null)
  const salesRangeRef = useRef(salesRange)

  // Keep salesRange ref updated
  useEffect(() => {
    salesRangeRef.current = salesRange
  }, [salesRange])

  useEffect(() => {
    // Create marker cluster group with custom icon function
    const cluster = L.markerClusterGroup({
      iconCreateFunction: (clusterObj) => {
        const markers = clusterObj.getAllChildMarkers()
        let totalSales = 0
        markers.forEach((m) => {
          // Get sales from marker options (predicted_annual_sales)
          const sales = m.options?.predicted_annual_sales || 0
          totalSales += sales
        })

        const formattedSales = formatSales(totalSales)
        const count = clusterObj.getChildCount()
        let size = 40
        if (count >= 50) {
          size = 60
        } else if (count >= 10) {
          size = 50
        }

        // Calculate gradient color based on total sales
        // Use a scaled range for clusters (they aggregate multiple candidates)
        const range = salesRangeRef.current || { min: 0, max: 1000000 }
        const clusterMin = range.min * 2  // Clusters have at least 2 markers
        const clusterMax = range.max * Math.max(count, 10)  // Scale max by count
        const bgColor = getSalesColor(totalSales, clusterMin, clusterMax)

        return L.divIcon({
          html: `<div class="cluster-sales" style="background: ${bgColor}; box-shadow: 0 3px 8px ${bgColor}66, 0 0 0 2px rgba(255,255,255,0.3);">${formattedSales}</div>`,
          className: 'sales-cluster-icon',
          iconSize: L.point(size, size),
        })
      },
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 50,
    })

    clusterRef.current = cluster
    map.addLayer(cluster)

    return () => {
      map.removeLayer(cluster)
    }
  }, [map])

  useEffect(() => {
    const cluster = clusterRef.current
    if (!cluster) return

    // Clear existing markers
    cluster.clearLayers()

    // Add children as markers
    // This is a simplified approach - children should be CircleMarkers
    // We need to convert them to regular markers for clustering
    if (children) {
      const childArray = Array.isArray(children) ? children : [children]
      childArray.forEach((child) => {
        if (child && child.props) {
          const { center, pathOptions, eventHandlers, children: popup } = child.props
          if (center) {
            // Create a regular marker instead of CircleMarker for clustering
            const marker = L.circleMarker(center, {
              ...pathOptions,
              radius: 8,
              predicted_annual_sales: child.props.pathOptions?.predicted_annual_sales ||
                extractSalesFromChild(child),
            })

            if (eventHandlers?.click) {
              marker.on('click', eventHandlers.click)
            }

            // Add popup if exists
            if (popup && popup.props?.children) {
              const popupContent = typeof popup.props.children === 'string'
                ? popup.props.children
                : renderPopupContent(popup.props.children)
              marker.bindPopup(popupContent, {
                className: 'modern-popup',
                minWidth: 180
              })
            }

            cluster.addLayer(marker)
          }
        }
      })
    }
  }, [children])

  // Don't render children directly - they're managed by the cluster
  return null
}

// Helper to extract sales from child props
function extractSalesFromChild(child) {
  // Try to find predicted_sales in various places
  const popup = child.props?.children
  if (popup?.props?.children) {
    const content = popup.props.children
    if (typeof content === 'object' && content.props?.children) {
      // Look for "Predicted Sales" text
      const text = JSON.stringify(content)
      const match = text.match(/predicted_annual_sales[^\d]*(\d+)/i)
      if (match) return parseInt(match[1], 10)
    }
  }
  return 0
}

// Helper to render popup content as HTML string
function renderPopupContent(content) {
  if (typeof content === 'string') return content
  if (typeof content === 'number') return String(content)
  if (!content) return ''

  // If it's a React element, convert to HTML
  if (content.props) {
    const { className, children } = content.props
    const tag = content.type || 'div'
    const tagName = typeof tag === 'string' ? tag : 'div'
    const classAttr = className ? ` class="${className}"` : ''

    // Recursively render children
    let innerContent = ''
    if (children) {
      if (Array.isArray(children)) {
        innerContent = children.map(c => renderPopupContent(c)).join('')
      } else {
        innerContent = renderPopupContent(children)
      }
    }

    return `<${tagName}${classAttr}>${innerContent}</${tagName}>`
  }

  // Handle arrays
  if (Array.isArray(content)) {
    return content.map(c => renderPopupContent(c)).join('')
  }

  return ''
}
