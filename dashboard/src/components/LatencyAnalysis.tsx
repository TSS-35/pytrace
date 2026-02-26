import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { LatencyMetrics, OperationStats } from '../types'
import './LatencyAnalysis.css'

export function LatencyAnalysis() {
  const [metrics, setMetrics] = useState<LatencyMetrics | null>(null)
  const [slowest, setSlowest] = useState<OperationStats[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [metricsRes, slowestRes] = await Promise.all([
        api.getLatencyMetrics(),
        api.getLatencySlowest(10),
      ])
      setMetrics(metricsRes.data)
      setSlowest(slowestRes.data)
      setError(null)
    } catch (err) {
      setError('Failed to load latency data. Make sure the Flask server is running on http://localhost:5000')
      setMetrics(null)
      setSlowest([])
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const filteredSlowest = (slowest || []).filter(op =>
    op.name.toLowerCase().includes(filter.toLowerCase())
  )

  if (loading) return <div className="latency-analysis">Loading...</div>
  if (error) return <div className="latency-analysis error">{error}</div>

  return (
    <div className="latency-analysis">
      <h2>Latency Analysis</h2>

      <section className="metrics-grid">
        <h3>Duration Distribution</h3>
        <div className="percentiles">
          <div className="metric">
            <label>p50</label>
            <span>{metrics?.p50}ms</span>
          </div>
          <div className="metric">
            <label>p95</label>
            <span>{metrics?.p95}ms</span>
          </div>
          <div className="metric">
            <label>p99</label>
            <span>{metrics?.p99}ms</span>
          </div>
          <div className="metric">
            <label>Min</label>
            <span>{metrics?.min}ms</span>
          </div>
          <div className="metric">
            <label>Max</label>
            <span>{metrics?.max}ms</span>
          </div>
          <div className="metric">
            <label>Avg</label>
            <span>{metrics?.avg}ms</span>
          </div>
        </div>
      </section>

      <section className="slowest-operations">
        <h3>Slowest Operations</h3>
        <input
          type="text"
          placeholder="Filter operations"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="filter-input"
        />
        {filteredSlowest.length > 0 ? (
          <table className="operations-table">
            <thead>
              <tr>
                <th>Operation</th>
                <th>Duration (ms)</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              {filteredSlowest.map((op) => (
                <tr key={op.name}>
                  <td>{op.name}</td>
                  <td>{op.avgDuration.toFixed(2)}</td>
                  <td>{op.callCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="no-data">
            {filter ? 'No operations match filter' : 'No operations found'}
          </p>
        )}
      </section>
    </div>
  )
}
