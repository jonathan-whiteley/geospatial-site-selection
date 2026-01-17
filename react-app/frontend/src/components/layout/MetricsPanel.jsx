import React from 'react'
import { cn } from '../../lib/utils'
import { formatSales, formatNumber } from '../../lib/utils'
import { SectionHeader } from './Sidebar'

/**
 * Metrics card component
 */
export function MetricCard({ label, value, highlight = false, className }) {
  return (
    <div
      className={cn(
        'p-3 rounded-lg border',
        highlight
          ? 'bg-gradient-to-br from-blue-500 to-blue-400 border-blue-600 shadow-md'
          : 'bg-white border-gray-200',
        className
      )}
    >
      <div
        className={cn(
          'text-xs uppercase tracking-wide',
          highlight ? 'text-white/90' : 'text-gray-500'
        )}
      >
        {label}
      </div>
      <div
        className={cn(
          'text-xl font-semibold mt-1',
          highlight ? 'text-white' : 'text-brand-orange'
        )}
      >
        {value}
      </div>
    </div>
  )
}

/**
 * Grid container for metrics
 */
export function MetricsGrid({ children, className }) {
  return (
    <div className={cn('grid grid-cols-2 gap-3 my-4', className)}>
      {children}
    </div>
  )
}

/**
 * Current Network metrics panel
 */
export function CurrentNetworkMetrics({ networkData, expansionData, visibleCandidates }) {
  const storeCount = networkData?.stores?.length || 0
  const totalAnnualSales = networkData?.stores?.reduce(
    (sum, s) => sum + (s.annual_sales || 0),
    0
  ) || 0
  const convenienceCount = networkData?.convenienceStores?.length || 0
  const competitorCount = networkData?.competitors?.length || 0

  // Expansion metrics
  const candidateCount = visibleCandidates?.length || 0
  const totalRevenue = visibleCandidates?.reduce(
    (sum, c) => sum + (c.predicted_annual_sales || 0),
    0
  ) || 0
  const partnershipCount = visibleCandidates?.filter(
    c => c.fulfillment_strategy === 'partner'
  ).length || 0
  const partnershipRate = candidateCount > 0
    ? (partnershipCount / candidateCount * 100)
    : 0
  const partnershipRevenue = visibleCandidates
    ?.filter(c => c.within_convenience_isochrone || c.fulfillment_strategy === 'partner')
    .reduce((sum, c) => sum + (c.predicted_annual_sales || 0), 0) || 0

  return (
    <div className="mt-6">
      <SectionHeader>Current Stores Metrics</SectionHeader>
      <MetricsGrid>
        <MetricCard label="Current Stores" value={storeCount} />
        <MetricCard label="Total Annual Sales" value={formatSales(totalAnnualSales)} />
        <MetricCard label="Potential Partner Stores" value={convenienceCount} />
        <MetricCard label="Competitor Stores" value={competitorCount} />
      </MetricsGrid>

      {candidateCount > 0 && (
        <>
          <SectionHeader className="mt-6">Expansion Metrics</SectionHeader>
          <MetricsGrid>
            <MetricCard label="Expansion Candidates" value={formatNumber(candidateCount)} />
            <MetricCard
              label="% Partnership Opportunity"
              value={`${partnershipRate.toFixed(0)}%`}
              highlight
            />
            <MetricCard label="Total Revenue Potential" value={formatSales(totalRevenue)} />
            <MetricCard label="Partnership Revenue Potential" value={formatSales(partnershipRevenue)} />
          </MetricsGrid>
        </>
      )}
    </div>
  )
}

/**
 * Expansion mode metrics panel
 */
export function ExpansionMetrics({ visibleCandidates }) {
  const candidateCount = visibleCandidates?.length || 0
  const totalRevenue = visibleCandidates?.reduce(
    (sum, c) => sum + (c.predicted_annual_sales || 0),
    0
  ) || 0
  const partnershipCount = visibleCandidates?.filter(
    c => c.fulfillment_strategy === 'partner'
  ).length || 0
  const partnershipRate = candidateCount > 0
    ? (partnershipCount / candidateCount * 100)
    : 0
  const partnershipRevenue = visibleCandidates
    ?.filter(c => c.within_convenience_isochrone || c.fulfillment_strategy === 'partner')
    .reduce((sum, c) => sum + (c.predicted_annual_sales || 0), 0) || 0

  return (
    <div className="mt-6">
      <SectionHeader>Expansion Metrics</SectionHeader>
      <MetricsGrid>
        <MetricCard label="Expansion Candidates" value={formatNumber(candidateCount)} />
        <MetricCard
          label="% Partnership Opportunity"
          value={`${partnershipRate.toFixed(0)}%`}
          highlight
        />
        <MetricCard label="Total Revenue Potential" value={formatSales(totalRevenue)} />
        <MetricCard label="Partnership Revenue Potential" value={formatSales(partnershipRevenue)} />
      </MetricsGrid>
    </div>
  )
}
