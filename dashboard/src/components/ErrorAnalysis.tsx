import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { ErrorStats, ErrorDetail } from '../types'
import './ErrorAnalysis.css'

export function ErrorAnalysis() {
  const [errorStats, setErrorStats] = useState<ErrorStats | null>(null)
  const [recentErrors, setRecentErrors] = useState<ErrorDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadErrorData()
  }, [])

  const loadErrorData = async () => {
    try {
      setLoading(true)
      const [statsRes, errorsRes] = await Promise.all([
        api.getErrorStats(),
        api.getRecentErrors(20),
      ])
      setErrorStats(statsRes.data || null)
      setRecentErrors(Array.isArray(errorsRes.data) ? errorsRes.data : [])
      setError(null)
    } catch (err) {
      setError('Failed to load error data. Make sure the Flask server is running on http://localhost:5000')
      setErrorStats(null)
      setRecentErrors([])
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="error-analysis">Loading...</div>
  if (error) return <div className="error-analysis error">{error}</div>

  return (
    <div className="error-analysis">
      <h2>Error Analysis</h2>

      {errorStats && (
        <section className="error-stats">
          <h3>Error Summary</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <label>Total Errors</label>
              <span className="stat-value">{errorStats.totalErrors}</span>
            </div>
            <div className="stat-card">
              <label>Error Rate</label>
              <span className="stat-value">
                {(errorStats.errorRate * 100).toFixed(2)}%
              </span>
            </div>
            <div className="stat-card">
              <label>Unique Operations</label>
              <span className="stat-value">{errorStats.uniqueOperations}</span>
            </div>
          </div>
        </section>
      )}

      <section className="error-by-operation">
        <h3>Errors by Operation</h3>
        {errorStats?.errorsByOperation && Object.entries(errorStats.errorsByOperation).length > 0 ? (
          <table className="error-table">
            <thead>
              <tr>
                <th>Operation</th>
                <th>Error Count</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(errorStats.errorsByOperation).map(
                ([operation, count]) => (
                  <tr key={operation}>
                    <td>{operation}</td>
                    <td>{count}</td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        ) : (
          <div className="no-data">No errors found</div>
        )}
      </section>

      <section className="recent-errors">
        <h3>Recent Errors</h3>
        {recentErrors.length > 0 ? (
          <div className="errors-list">
            {recentErrors.map((err, index) => (
              <div key={index} className="error-item">
                <div className="error-header">
                  <span className="operation">{err.operationName}</span>
                  <span className="error-msg">{err.errorMessage}</span>
                </div>
                {err.stackTrace && (
                  <pre className="stack-trace">{err.stackTrace}</pre>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="no-data">No recent errors</div>
        )}
      </section>
    </div>
  )
}
