import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { OperationStats } from '../types'
import './OperationsDashboard.css'

type SortField = 'name' | 'duration' | 'count' | 'errorRate'
type SortOrder = 'asc' | 'desc'

export function OperationsDashboard() {
  const [operations, setOperations] = useState<OperationStats[]>([])
  const [filter, setFilter] = useState('')
  const [sortField, setSortField] = useState<SortField>('duration')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadOperations()
  }, [])

  const loadOperations = async () => {
    try {
      setLoading(true)
      const res = await api.getOperations()
      setOperations(Array.isArray(res.data) ? res.data : [])
      setError(null)
    } catch (err) {
      setError('Failed to load operations. Make sure the Flask server is running on http://localhost:5000')
      setOperations([])
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const filteredOperations = operations.filter((op) =>
    op.name.toLowerCase().includes(filter.toLowerCase())
  )

  const sortedOperations = [...filteredOperations].sort((a, b) => {
    let aVal: number | string = 0
    let bVal: number | string = 0

    if (sortField === 'name') {
      aVal = a.name
      bVal = b.name
    } else if (sortField === 'duration') {
      aVal = a.avgDuration
      bVal = b.avgDuration
    } else if (sortField === 'count') {
      aVal = a.callCount
      bVal = b.callCount
    } else if (sortField === 'errorRate') {
      aVal = a.errorRate || 0
      bVal = b.errorRate || 0
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  if (loading) return <div className="operations-dashboard">Loading...</div>
  if (error) return <div className="operations-dashboard error">{error}</div>

  return (
    <div className="operations-dashboard">
      <h2>Operations Dashboard</h2>

      <input
        type="text"
        placeholder="Filter operations"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="filter-input"
      />

      {sortedOperations.length === 0 ? (
        <div className="no-data">No operations found</div>
      ) : (
        <table className="operations-table">
          <thead>
            <tr>
              <th
                className={`sortable ${sortField === 'name' ? 'active' : ''}`}
                onClick={() => handleSort('name')}
              >
                Operation Name
                {sortField === 'name' && (
                  <span className="sort-icon">
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                className={`sortable ${
                  sortField === 'duration' ? 'active' : ''
                }`}
                onClick={() => handleSort('duration')}
              >
                Avg Duration (ms)
                {sortField === 'duration' && (
                  <span className="sort-icon">
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                className={`sortable ${sortField === 'count' ? 'active' : ''}`}
                onClick={() => handleSort('count')}
              >
                Call Count
                {sortField === 'count' && (
                  <span className="sort-icon">
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
              <th
                className={`sortable ${
                  sortField === 'errorRate' ? 'active' : ''
                }`}
                onClick={() => handleSort('errorRate')}
              >
                Error Rate
                {sortField === 'errorRate' && (
                  <span className="sort-icon">
                    {sortOrder === 'asc' ? '↑' : '↓'}
                  </span>
                )}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedOperations.map((op) => (
              <tr key={op.name}>
                <td>{op.name}</td>
                <td>{op.avgDuration.toFixed(2)}</td>
                <td>{op.callCount}</td>
                <td>
                  <span
                    className={
                      (op.errorRate || 0) > 0.05 ? 'error-rate high' : 'error-rate'
                    }
                  >
                    {((op.errorRate || 0) * 100).toFixed(2)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
