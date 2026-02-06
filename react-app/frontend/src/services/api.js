import axios from 'axios'

// API client with /api prefix
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================
// Health
// ============================================

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

// ============================================
// Consolidated Initial Load (Phase 1 Performance)
// ============================================

/**
 * Load all initial app data in a single request.
 * Replaces 3 parallel API calls with 1, eliminating duplicate queries.
 */
export async function getInitialData() {
  const response = await api.get('/init')
  return response.data
}

// ============================================
// Stores
// ============================================

export async function getCurrentStores() {
  const response = await api.get('/stores/current')
  return response.data
}

export async function getStoreIsochrones() {
  const response = await api.get('/stores/isochrones')
  return response.data
}

export async function getPartnerIsochrones() {
  const response = await api.get('/stores/partners')
  return response.data
}

export async function getPartnerStores() {
  const response = await api.get('/stores/partners/stores')
  return response.data
}

// Backward compatibility aliases (deprecated)
export const getConvenienceIsochrones = getPartnerIsochrones
export const getConvenienceStores = getPartnerStores

export async function getCompetitors() {
  const response = await api.get('/stores/competitors')
  return response.data
}

export async function getFullNetwork() {
  const response = await api.get('/stores/network')
  return response.data
}

// ============================================
// Expansion
// ============================================

export async function getExpansionCandidates(filters = {}) {
  const params = new URLSearchParams()
  if (filters.minSales) params.append('min_sales', filters.minSales)
  if (filters.maxSales) params.append('max_sales', filters.maxSales)
  if (filters.minPopulation) params.append('min_population', filters.minPopulation)
  if (filters.maxPopulation) params.append('max_population', filters.maxPopulation)
  if (filters.fulfillmentStrategy) params.append('fulfillment_strategy', filters.fulfillmentStrategy)

  const response = await api.get(`/expansion/candidates?${params.toString()}`)
  return response.data
}

export async function getExpansionData() {
  const response = await api.get('/expansion/data')
  return response.data
}

// ============================================
// Optimization
// ============================================

export async function getOptimizationResults() {
  const response = await api.get('/optimization/results')
  return response.data
}

export async function lookupOptimization(params) {
  const response = await api.post('/optimization/lookup', {
    max_stores: params.maxStores,
    min_dist_new: params.minDistNew,
    min_dist_existing: params.minDistExisting,
  })
  return response.data
}

// ============================================
// Metrics
// ============================================

export async function getNetworkMetrics() {
  const response = await api.get('/metrics/network')
  return response.data
}

export default api
