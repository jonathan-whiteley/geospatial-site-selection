import React, { useEffect, useMemo, useRef } from 'react'
import { MapContainer, TileLayer, useMap, Pane, GeoJSON, CircleMarker, Circle, Popup } from 'react-leaflet'
import MarkerClusterGroup from './MarkerClusterGroup'
import { MapBoundsTracker } from './MapBoundsTracker'
import { MapLegend, SalesGradientLegend } from './MapLegend'
import { getSalesColor, formatSales } from '../../lib/utils'
import 'leaflet/dist/leaflet.css'

// Map center (Massachusetts)
const DEFAULT_CENTER = [42.4072, -71.3824]
const DEFAULT_ZOOM = 9

/**
 * Component to set up custom panes
 */
function MapPanes() {
  const map = useMap()

  useEffect(() => {
    // Create custom panes for z-index control
    if (!map.getPane('isochrones')) {
      map.createPane('isochrones')
      map.getPane('isochrones').style.zIndex = 400
    }
    if (!map.getPane('markers')) {
      map.createPane('markers')
      map.getPane('markers').style.zIndex = 450
    }
  }, [map])

  return null
}

/**
 * LCE Store isochrones (green)
 */
function IsochroneLayer({ isochrones }) {
  if (!isochrones || isochrones.length === 0) return null

  return (
    <>
      {isochrones.map((iso, idx) => {
        if (!iso.isochrone_geojson) return null
        try {
          const geojson = typeof iso.isochrone_geojson === 'string'
            ? JSON.parse(iso.isochrone_geojson)
            : iso.isochrone_geojson
          return (
            <GeoJSON
              key={`iso-${idx}`}
              data={geojson}
              pane="isochrones"
              interactive={false}
              style={{
                color: '#10b981',
                weight: 1.5,
                fillOpacity: 0.15,
                fillColor: '#10b981',
              }}
            />
          )
        } catch (e) {
          console.error('Failed to parse LCE isochrone:', e)
          return null
        }
      })}
    </>
  )
}

/**
 * Partner store isochrones (blue)
 */
function PartnerIsochroneLayer({ isochrones, visible }) {
  if (!visible || !isochrones || isochrones.length === 0) return null

  return (
    <>
      {isochrones.map((iso, idx) => {
        if (!iso.isochrone_geojson) return null
        try {
          const geojson = typeof iso.isochrone_geojson === 'string'
            ? JSON.parse(iso.isochrone_geojson)
            : iso.isochrone_geojson
          return (
            <GeoJSON
              key={`partner-iso-${idx}`}
              data={geojson}
              pane="isochrones"
              interactive={false}
              style={{
                color: '#3b82f6',
                weight: 1.5,
                fillOpacity: 0.15,
                fillColor: '#3b82f6',
              }}
            />
          )
        } catch (e) {
          console.error('Failed to parse partner isochrone:', e)
          return null
        }
      })}
    </>
  )
}


/**
 * Current stores markers (green) - with polished popup
 */
function CurrentStoreMarkers({ stores, visible, onStoreClick }) {
  if (!visible || !stores || stores.length === 0) return null

  return (
    <>
      {stores.map((store, idx) => (
        <CircleMarker
          key={`store-${idx}`}
          center={[store.latitude, store.longitude]}
          pane="markers"
          radius={8}
          pathOptions={{
            fillColor: '#10b981',
            color: '#ffffff',
            weight: 2,
            fillOpacity: 0.9,
          }}
          eventHandlers={{
            click: () => onStoreClick?.(store),
          }}
        >
          <Popup className="modern-popup">
            <div className="popup-header">
              <div className="popup-dot green"></div>
              <div>
                <div className="popup-title">Store #{store.store_number}</div>
                <div className="popup-subtitle">{store.city}, {store.state}</div>
              </div>
            </div>
            {(store.annual_sales || store.predicted_annual_sales) > 0 && (
              <div className="popup-row">
                <span className="popup-label">Annual Sales</span>
                <span className="popup-value">
                  ${Math.round(store.annual_sales || store.predicted_annual_sales || 0).toLocaleString()}
                </span>
              </div>
            )}
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

/**
 * Candidate isochrones (2km radius circles) with sales-based gradient
 * Darker red = higher predicted sales
 */
function CandidateIsochroneLayer({ candidates, salesRange, visible }) {
  if (!visible || !candidates || candidates.length === 0) return null

  return (
    <>
      {candidates.map((candidate, idx) => {
        const fillColor = getSalesColor(
          candidate.predicted_annual_sales || 0,
          salesRange.min,
          salesRange.max
        )
        return (
          <Circle
            key={`cand-iso-${idx}`}
            center={[candidate.latitude, candidate.longitude]}
            pane="isochrones"
            radius={2000}
            interactive={false}
            pathOptions={{
              color: fillColor,
              fillColor: fillColor,
              fillOpacity: 0.35,
              weight: 1.5,
            }}
          />
        )
      })}
    </>
  )
}

/**
 * Candidate markers (red, with clustering) - polished popup
 */
function CandidateMarkers({ candidates, visible, onStoreClick }) {
  if (!visible || !candidates || candidates.length === 0) return null

  return (
    <MarkerClusterGroup>
      {candidates.map((candidate, idx) => (
        <CircleMarker
          key={`cand-${idx}`}
          center={[candidate.latitude, candidate.longitude]}
          pane="markers"
          radius={8}
          pathOptions={{
            fillColor: '#ef4444',
            color: '#ffffff',
            weight: 2,
            fillOpacity: 0.85,
            // Pass sales data for cluster aggregation
            predicted_annual_sales: candidate.predicted_annual_sales || 0,
          }}
          eventHandlers={{
            click: () => onStoreClick?.(candidate),
          }}
        >
          <Popup className="modern-popup">
            <div className="popup-header">
              <div className="popup-dot red"></div>
              <div>
                <div className="popup-title">Candidate Site</div>
                <div className="popup-subtitle">{candidate.city}, {candidate.state}</div>
              </div>
            </div>
            <div className="popup-row">
              <span className="popup-label">Predicted Sales</span>
              <span className="popup-value">
                ${Math.round(candidate.predicted_annual_sales || 0).toLocaleString()}
              </span>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MarkerClusterGroup>
  )
}

/**
 * Partner store markers (blue)
 */
function PartnerStoreMarkers({ stores, visible }) {
  if (!visible || !stores || stores.length === 0) return null

  return (
    <>
      {stores.map((store, idx) => (
        <CircleMarker
          key={`partner-${idx}`}
          center={[store.latitude, store.longitude]}
          pane="markers"
          radius={6}
          pathOptions={{
            fillColor: '#3b82f6',
            color: '#ffffff',
            weight: 2,
            fillOpacity: 0.9,
          }}
        >
          <Popup className="modern-popup">
            <div className="min-w-[150px]">
              <div className="font-semibold text-gray-900">{store.name}</div>
              <div className="text-xs text-blue-600 mt-1">Partner Store</div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

/**
 * Competitor markers (purple)
 */
function CompetitorMarkers({ competitors, visible }) {
  if (!visible || !competitors || competitors.length === 0) return null

  return (
    <>
      {competitors.map((comp, idx) => (
        <CircleMarker
          key={`comp-${idx}`}
          center={[comp.latitude, comp.longitude]}
          pane="markers"
          radius={6}
          pathOptions={{
            fillColor: '#a855f7',
            color: '#ffffff',
            weight: 2,
            fillOpacity: 0.85,
          }}
        >
          <Popup className="modern-popup">
            <div className="min-w-[150px]">
              <div className="font-semibold text-gray-900">{comp.name}</div>
              <div className="text-xs text-purple-600 mt-1">Competitor</div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

/**
 * Main geospatial map component
 */
export function GeospatialMap({
  networkData,
  candidates,
  layers,
  salesRange,
  onStoreClick,
  onBoundsChange,
}) {
  // Get current stores (from candidates' current_stores or network stores)
  const currentStores = useMemo(() => {
    return networkData?.stores || []
  }, [networkData])

  // Get partner stores (with fallback to deprecated convenienceStores)
  const partnerStores = useMemo(() => {
    return networkData?.partnerStores || networkData?.convenienceStores || []
  }, [networkData])

  // Get partner isochrones (with fallback to deprecated convenienceIsochrones)
  const partnerIsochrones = useMemo(() => {
    return networkData?.partnerIsochrones || networkData?.convenienceIsochrones || []
  }, [networkData])

  // Get competitors
  const competitors = useMemo(() => {
    return networkData?.competitors || []
  }, [networkData])

  // Show sales legend when candidates or candidate isochrones are visible
  const showSalesLegend = layers.candidates || layers.candidateIsochrones

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        className="w-full h-full"
        zoomControl={true}
      >
        <MapPanes />
        <MapBoundsTracker onBoundsChange={onBoundsChange} />

        {/* Light tile layer (CartoDB Positron) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          maxZoom={20}
        />

        {/* LCE Isochrones (always visible) */}
        <IsochroneLayer isochrones={networkData?.isochrones} />

        {/* Partner isochrones */}
        <PartnerIsochroneLayer
          isochrones={partnerIsochrones}
          visible={layers.partners}
        />

        {/* Candidate isochrones with sales gradient */}
        <CandidateIsochroneLayer
          candidates={candidates}
          salesRange={salesRange}
          visible={layers.candidateIsochrones}
        />

        {/* Current stores */}
        <CurrentStoreMarkers
          stores={currentStores}
          visible={layers.currentStores}
          onStoreClick={onStoreClick}
        />

        {/* Candidate markers */}
        <CandidateMarkers
          candidates={candidates}
          visible={layers.candidates}
          onStoreClick={onStoreClick}
        />

        {/* Partner stores */}
        <PartnerStoreMarkers
          stores={partnerStores}
          visible={layers.partners}
        />

        {/* Competitors */}
        <CompetitorMarkers
          competitors={competitors}
          visible={layers.competitors}
        />
      </MapContainer>

      {/* Map Legend */}
      <MapLegend />

      {/* Sales Gradient Legend */}
      {showSalesLegend && <SalesGradientLegend salesRange={salesRange} />}
    </div>
  )
}

export default GeospatialMap
