import { useEffect } from 'react'
import { useMap, useMapEvents } from 'react-leaflet'

/**
 * Component that tracks map bounds and reports changes to parent
 * Must be rendered inside a MapContainer
 */
export function MapBoundsTracker({ onBoundsChange }) {
  const map = useMap()

  // Report initial bounds on mount
  useEffect(() => {
    if (map && onBoundsChange) {
      onBoundsChange(map.getBounds())
    }
  }, [map, onBoundsChange])

  // Listen for map move/zoom events
  useMapEvents({
    moveend: () => {
      if (onBoundsChange) {
        onBoundsChange(map.getBounds())
      }
    },
    zoomend: () => {
      if (onBoundsChange) {
        onBoundsChange(map.getBounds())
      }
    },
  })

  return null
}

export default MapBoundsTracker
