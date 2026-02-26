import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Trace } from '../types'
import './TraceExplorer.css'

export function TraceExplorer() {
  const [traces, setTraces] = useState<Trace[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [operationFilter, setOperationFilter] = useState('')
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTraces()
  }, [])

  const loadTraces = async () => {
    try {
      setLoading(true)
      const res = await api.getTraces({ limit: 50 })
      setTraces(Array.isArray(res.data) ? res.data : [])
      setError(null)
    } catch (err) {
      setError('Failed to load traces. Make sure the Flask server is running on http://localhost:5000')
      setTraces([])
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const filteredTraces = (traces || []).filter((trace) => {
    const matchesSearch =
      !searchTerm ||
      trace.traceId.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesOp =
      !operationFilter ||
      trace.spans?.some((span) =>
        span.operationName.toLowerCase().includes(operationFilter.toLowerCase())
      )

    return matchesSearch && matchesOp
  })

  if (loading) return <div className="trace-explorer">Loading traces...</div>
  if (error) return <div className="trace-explorer error">{error}</div>

  return (
    <div className="trace-explorer">
      <h2>Trace Explorer</h2>

      <div className="filters">
        <input
          type="text"
          placeholder="Search trace ID"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        <input
          type="text"
          placeholder="Filter by operation"
          value={operationFilter}
          onChange={(e) => setOperationFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="traces-list">
        {filteredTraces.length === 0 ? (
          <div className="no-data">No traces found</div>
        ) : (
          filteredTraces.map((trace) => (
            <div key={trace.traceId} className="trace-item">
              <div
                className="trace-header"
                onClick={() =>
                  setExpandedTraceId(
                    expandedTraceId === trace.traceId ? null : trace.traceId
                  )
                }
              >
                <span className="toggle">
                  {expandedTraceId === trace.traceId ? '▼' : '▶'}
                </span>
                <span className="trace-id">{trace.traceId}</span>
                <span className="span-count">
                  {trace.spans?.length || 0} spans
                </span>
              </div>

              {expandedTraceId === trace.traceId && (
                <div className="trace-details">
                  {trace.spans?.map((span) => (
                    <div key={span.spanId} className="span-item">
                      <div className="span-header">
                        <span className="operation">{span.operationName}</span>
                        <span className="duration">{span.duration}ms</span>
                      </div>
                      {Object.keys(span.attributes || {}).length > 0 && (
                        <div className="attributes">
                          <strong>Attributes:</strong>
                          <pre>
                            {JSON.stringify(span.attributes, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
