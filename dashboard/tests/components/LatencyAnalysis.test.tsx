import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LatencyAnalysis } from '../../src/components/LatencyAnalysis'

vi.mock('../../src/api/client', () => ({
  api: {
    getLatencyMetrics: vi.fn(() => 
      Promise.resolve({
        data: {
          p50: 45,
          p95: 250,
          p99: 500,
          min: 10,
          max: 1000,
          avg: 75
        }
      })
    ),
    getLatencySlowest: vi.fn(() =>
      Promise.resolve({
        data: [
          { name: 'database_query', avgDuration: 450, callCount: 3 },
          { name: 'api_call', avgDuration: 250, callCount: 12 },
          { name: 'cache_lookup', avgDuration: 25, callCount: 45 }
        ]
      })
    ),
  }
}))

describe('LatencyAnalysis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render latency analysis component', async () => {
    render(<LatencyAnalysis />)
    
    await waitFor(() => {
      expect(screen.getByText(/Latency Analysis/i)).toBeInTheDocument()
    })
  })

  it('should render duration histogram', async () => {
    render(<LatencyAnalysis />)
    
    await waitFor(() => {
      expect(screen.getByText(/Duration Distribution/i)).toBeInTheDocument()
    })
  })

  it('should display percentile metrics (p50, p95, p99)', async () => {
    render(<LatencyAnalysis />)

    await waitFor(() => {
      // Get all elements with "p50" text - should be one with the label
      const p50Elements = screen.getAllByText(/p50/i)
      expect(p50Elements.length).toBeGreaterThan(0)
      
      // Check for specific percentile values
      expect(screen.getByText('45ms')).toBeInTheDocument()
      expect(screen.getByText('250ms')).toBeInTheDocument()
      expect(screen.getByText('500ms')).toBeInTheDocument()
    })
  })

  it('should render slowest operations list', async () => {
    render(<LatencyAnalysis />)

    await waitFor(() => {
      expect(screen.getByText('database_query')).toBeInTheDocument()
      expect(screen.getByText(/450/)).toBeInTheDocument()
    })
  })

  it('should allow filtering by operation name', async () => {
    const user = userEvent.setup()
    render(<LatencyAnalysis />)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Filter operations/i)).toBeInTheDocument()
    })
    
    const filterInput = screen.getByPlaceholderText(/Filter operations/i)
    await user.type(filterInput, 'database')
    
    await waitFor(() => {
      expect(screen.getByText('database_query')).toBeInTheDocument()
      expect(screen.queryByText('api_call')).not.toBeInTheDocument()
    })
  })
})
