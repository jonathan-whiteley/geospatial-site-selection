import React from 'react'
import { cn } from '../../lib/utils'

/**
 * Main application layout with header, sidebar, and map container
 */
export function AppLayout({ children, sidebar, header }) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden">
      {/* Header */}
      {header}

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        {sidebar}

        {/* Map container */}
        <main className="flex-1 relative">
          {children}
        </main>
      </div>
    </div>
  )
}

/**
 * Application header with logo and title
 */
export function AppHeader({ logoSrc }) {
  return (
    <header className="h-16 bg-brand-orange flex items-center px-6 shadow-md z-50">
      {logoSrc && (
        <img
          src={logoSrc}
          alt="Logo"
          className="h-12 mr-4"
        />
      )}
      <h1 className="text-white text-xl font-semibold">
        Hunger Satisfaction Dashboard
      </h1>
      <span className="text-white/90 text-sm ml-4">
        Powered by Databricks
      </span>
    </header>
  )
}
