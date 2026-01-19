import React, { useMemo } from 'react'
import { Building2, DollarSign, Target, TrendingUp } from 'lucide-react'
import { Card } from '../ui/Card'
import { formatCurrency } from '../../lib/utils'
import { cn } from '../../lib/utils'

/**
 * KPI Card component
 */
function KPICard({ label, value, subtext, icon: Icon, iconBg, iconColor, borderColor }) {
  return (
    <Card className={cn(
      'flex items-center justify-between p-4 border-l-4',
      borderColor
    )}>
      <div className="min-w-0 flex-1">
        <p className="text-2xl font-bold text-gray-900 truncate">{value}</p>
        <p className="text-sm text-gray-500 truncate">{label}</p>
        {subtext && (
          <p className="text-xs text-gray-400 mt-0.5 truncate">{subtext}</p>
        )}
      </div>
      <div className={cn('p-3 rounded-lg flex-shrink-0 ml-3', iconBg)}>
        <Icon className={cn('w-5 h-5', iconColor)} />
      </div>
    </Card>
  )
}

/**
 * Current Network KPIs - displayed above the map
 */
export function CurrentNetworkKPIs({ networkData, expansionData }) {
  // Calculate metrics
  const metrics = useMemo(() => {
    const currentStores = networkData?.stores || []
    const candidates = expansionData?.candidates || []

    // Total current stores
    const totalStores = currentStores.length

    // Total current store sales (using population as proxy if no sales data)
    // In real implementation, this would come from actual sales data
    const totalCurrentSales = currentStores.reduce((sum, store) => {
      return sum + (store.annual_sales || store.predicted_annual_sales || 0)
    }, 0)

    // Total candidate predicted sales
    const totalCandidateSales = candidates.reduce((sum, c) => {
      return sum + (c.predicted_annual_sales || 0)
    }, 0)

    // Hunger Satisfaction Coverage
    const totalPotentialMarket = totalCurrentSales + totalCandidateSales
    const hungerSatisfactionCoverage = totalPotentialMarket > 0
      ? ((totalCurrentSales / totalPotentialMarket) * 100).toFixed(1)
      : 0

    // Average store sales
    const avgStoreSales = totalStores > 0
      ? totalCurrentSales / totalStores
      : 0

    return {
      totalStores,
      totalCurrentSales,
      hungerSatisfactionCoverage,
      avgStoreSales,
    }
  }, [networkData, expansionData])

  const kpis = [
    {
      label: 'Current Stores',
      value: metrics.totalStores.toLocaleString(),
      icon: Building2,
      iconBg: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
      borderColor: 'border-l-emerald-500',
    },
    {
      label: 'Total Annual Sales',
      value: formatCurrency(metrics.totalCurrentSales),
      icon: DollarSign,
      iconBg: 'bg-blue-50',
      iconColor: 'text-blue-600',
      borderColor: 'border-l-blue-500',
    },
    {
      label: 'Hunger Satisfaction',
      value: `${metrics.hungerSatisfactionCoverage}%`,
      subtext: 'Current / Total Market',
      icon: Target,
      iconBg: 'bg-orange-50',
      iconColor: 'text-brand-orange',
      borderColor: 'border-l-brand-orange',
    },
    {
      label: 'Avg Store Sales',
      value: formatCurrency(metrics.avgStoreSales),
      icon: TrendingUp,
      iconBg: 'bg-purple-50',
      iconColor: 'text-purple-600',
      borderColor: 'border-l-purple-500',
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4 p-4 bg-gray-50/80 border-b border-gray-200">
      {kpis.map((kpi) => (
        <KPICard
          key={kpi.label}
          label={kpi.label}
          value={kpi.value}
          subtext={kpi.subtext}
          icon={kpi.icon}
          iconBg={kpi.iconBg}
          iconColor={kpi.iconColor}
          borderColor={kpi.borderColor}
        />
      ))}
    </div>
  )
}

export default CurrentNetworkKPIs
