import { useState, useEffect } from 'react'
import { LatencyAnalysis } from './LatencyAnalysis'
import { TraceExplorer } from './TraceExplorer'
import { ErrorAnalysis } from './ErrorAnalysis'
import { OperationsDashboard } from './OperationsDashboard'
import { ErrorBoundary } from './ErrorBoundary'
import './Dashboard.css'

type Tab = 'traces' | 'operations' | 'latency' | 'errors'

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('traces')
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      // Trigger refresh by resetting component keys or via context
      // For now, just log that auto-refresh is enabled
    }, 30000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const tabs: { id: Tab; label: string }[] = [
    { id: 'traces', label: 'Trace Explorer' },
    { id: 'operations', label: 'Operations' },
    { id: 'latency', label: 'Latency' },
    { id: 'errors', label: 'Errors' },
  ]

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Distributed Tracing Dashboard</h1>
        <div className="header-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (30s)
          </label>
        </div>
      </header>

      <nav className="dashboard-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="dashboard-content">
        <ErrorBoundary>
          {activeTab === 'traces' && <TraceExplorer />}
          {activeTab === 'operations' && <OperationsDashboard />}
          {activeTab === 'latency' && <LatencyAnalysis />}
          {activeTab === 'errors' && <ErrorAnalysis />}
        </ErrorBoundary>
      </main>
    </div>
  )
}
