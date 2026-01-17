import React, { useEffect, useMemo, useRef } from 'react'
import { MapContainer, TileLayer, useMap, Pane, GeoJSON, CircleMarker, Circle, Popup } from 'react-leaflet'
import MarkerClusterGroup from './MarkerClusterGroup'
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
 * Convenience store isochrones (blue)
 */
function ConvenienceIsochroneLayer({ isochrones, visible }) {
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
              key={`conv-iso-${idx}`}
              data={geojson}
              pane="isochrones"
              style={{
                color: '#3b82f6',
                weight: 1.5,
                fillOpacity: 0.15,
                fillColor: '#3b82f6',
              }}
            />
          )
        } catch (e) {
          console.error('Failed to parse convenience isochrone:', e)
          return null
        }
      })}
    </>
  )
}

/**
 * H3 Hexagon layer with sales-based gradient
 */
function H3HexagonLayer({ candidates, salesRange, visible, onStoreClick }) {
  if (!visible || !candidates || candidates.length === 0) return null

  return (
    <>
      {candidates.map((candidate, idx) => {
        if (!candidate.geometry_geojson) return null
        try {
          const geojson = typeof candidate.geometry_geojson === 'string'
            ? JSON.parse(candidate.geometry_geojson)
            : candidate.geometry_geojson
          const fillColor = getSalesColor(
            candidate.predicted_annual_sales || 0,
            salesRange.min,
            salesRange.max
          )
          return (
            <GeoJSON
              key={`hex-${idx}`}
              data={geojson}
              pane="isochrones"
              style={{
                color: '#dc2626',
                weight: 1.5,
                fillColor,
                fillOpacity: 0.7,
              }}
              eventHandlers={{
                click: () => onStoreClick?.(candidate),
              }}
            >
              <Popup>
                <div>
                  <strong>H3 Cell: {candidate.store_number}</strong><br />
                  <strong>Predicted Sales:</strong> ${(candidate.predicted_annual_sales || 0).toLocaleString()}<br />
                  <strong>Population:</strong> {Math.round(candidate.population || 0).toLocaleString()}
                </div>
              </Popup>
            </GeoJSON>
          )
        } catch (e) {
          console.error('Error rendering H3 hexagon:', e)
          return null
        }
      })}
    </>
  )
}

/**
 * Current stores markers (green)
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
            color: '#065f46',
            weight: 2,
            fillOpacity: 0.9,
          }}
          eventHandlers={{
            click: () => onStoreClick?.(store),
          }}
        >
          <Popup>
            <div>
              <strong>Store #{store.store_number}</strong><br />
              {store.city}, {store.state}<br />
              <hr style={{ margin: '5px 0' }} />
              <strong>Population:</strong> {Math.round(store.population || 0).toLocaleString()}<br />
              <strong>POI Count:</strong> {(store.total_poi_count || 0).toLocaleString()}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}

/**
 * Candidate isochrones (2km radius circles)
 */
function CandidateIsochroneLayer({ candidates, visible }) {
  if (!visible || !candidates || candidates.length === 0) return null

  return (
    <>
      {candidates.map((candidate, idx) => (
        <Circle
          key={`cand-iso-${idx}`}
          center={[candidate.latitude, candidate.longitude]}
          pane="isochrones"
          radius={2000}
          pathOptions={{
            color: '#fca5a5',
            fillColor: '#ef4444',
            fillOpacity: 0.15,
            weight: 1.5,
          }}
        />
      ))}
    </>
  )
}

/**
 * Candidate markers (red, with clustering)
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
            color: '#dc2626',
            weight: 2,
            fillOpacity: 0.8,
          }}
          eventHandlers={{
            click: () => onStoreClick?.(candidate),
          }}
        >
          <Popup>
            <div>
              <strong>Expansion Location {candidate.store_number}</strong><br />
              <strong>Predicted Sales:</strong> ${(candidate.predicted_annual_sales || 0).toLocaleString()}<br />
              <strong>Population:</strong> {Math.round(candidate.population || 0).toLocaleString()}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MarkerClusterGroup>
  )
}

/**
 * Convenience store markers (blue)
 */
function ConvenienceStoreMarkers({ stores, visible }) {
  if (!visible || !stores || stores.length === 0) return null

  return (
    <>
      {stores.map((store, idx) => (
        <CircleMarker
          key={`conv-${idx}`}
          center={[store.latitude, store.longitude]}
          pane="markers"
          radius={5}
          pathOptions={{
            fillColor: '#3b82f6',
            color: '#1e3a8a',
            weight: 2,
            fillOpacity: 0.9,
          }}
        >
          <Popup>
            <strong>{store.name}</strong>
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
          radius={5}
          pathOptions={{
            fillColor: '#a855f7',
            color: '#9333ea',
            weight: 2,
            fillOpacity: 0.7,
          }}
        >
          <Popup>
            <strong>{comp.name}</strong>
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
}) {
  // Get current stores (from candidates' current_stores or network stores)
  const currentStores = useMemo(() => {
    return networkData?.stores || []
  }, [networkData])

  // Get convenience stores
  const convenienceStores = useMemo(() => {
    return networkData?.convenienceStores || []
  }, [networkData])

  // Get competitors
  const competitors = useMemo(() => {
    return networkData?.competitors || []
  }, [networkData])

  // Show sales legend when candidates or H3 hexagons are visible
  const showSalesLegend = layers.candidates || layers.h3Hexagons

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        className="w-full h-full"
        zoomControl={true}
      >
        <MapPanes />

        {/* Dark tile layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
          maxZoom={20}
        />

        {/* LCE Isochrones (always visible) */}
        <IsochroneLayer isochrones={networkData?.isochrones} />

        {/* Convenience isochrones */}
        <ConvenienceIsochroneLayer
          isochrones={networkData?.convenienceIsochrones}
          visible={layers.convenience}
        />

        {/* Candidate isochrones */}
        <CandidateIsochroneLayer
          candidates={candidates}
          visible={layers.candidateIsochrones}
        />

        {/* H3 Hexagons */}
        <H3HexagonLayer
          candidates={candidates}
          salesRange={salesRange}
          visible={layers.h3Hexagons}
          onStoreClick={onStoreClick}
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

        {/* Convenience stores */}
        <ConvenienceStoreMarkers
          stores={convenienceStores}
          visible={layers.convenience}
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
