import React from 'react'
import { cn } from '../../lib/utils'

/**
 * Main application layout with header, sidebar, KPI bar, and map container
 */
export function AppLayout({ children, sidebar, header, kpiBar }) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-gray-50">
      {/* Header */}
      {header}

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        {sidebar}

        {/* Map area with optional KPI bar */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* KPI Bar (above map) */}
          {kpiBar}

          {/* Map container */}
          <main className="flex-1 relative">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}

/**
 * Application header with Panda Express branding
 */
export function AppHeader({ logoSrc, totalStores, stateName = 'Massachusetts' }) {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm z-50">
      {/* Left side - Logo and title */}
      <div className="flex items-center gap-3">
        {logoSrc && (
          <img
            src={logoSrc}
            alt="Panda Express"
            className="h-10"
          />
        )}
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            <span className="text-brand-orange">SiteIQ</span> - AI Site Selection Platform
          </h1>
          <p className="text-xs text-gray-500">
            AI-powered expansion insights
          </p>
        </div>
      </div>

      {/* Right side - State and network status */}
      <div className="flex items-center gap-4">
        {/* Orange accent divider */}
        <div className="h-8 w-1 bg-brand-orange rounded-full opacity-30" />

        <div className="text-right">
          <p className="text-sm font-medium text-gray-700">
            {stateName}
          </p>
          <p className="text-xs text-gray-500">Current Network</p>
        </div>

        {/* Powered by badge */}
        <div className="hidden md:flex items-center gap-2 pl-4 border-l border-gray-200">
          <span className="text-xs text-gray-400">Powered by</span>
          <span className="text-xs font-medium text-gray-600">Databricks</span>
        </div>
      </div>
    </header>
  )
}
