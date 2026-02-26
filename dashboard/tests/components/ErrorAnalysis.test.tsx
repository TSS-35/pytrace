import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ErrorAnalysis } from '../../src/components/ErrorAnalysis'

vi.mock('../../src/api/client', () => ({
  api: {
    getErrorStats: vi.fn(() =>
      Promise.resolve({
        data: {
          totalErrors: 100,
          errorRate: 0.05,
          uniqueOperations: 3,
          errorsByOperation: {
            database_query: 50,
            api_call: 30,
            cache_lookup: 20
          }
        }
      })
    ),
    getRecentErrors: vi.fn(() =>
      Promise.resolve({
        data: [
          {
            operationName: 'database_query',
            errorMessage: 'Connection timeout',
            stackTrace: 'Error: Connection timeout\n  at ...'
          },
          {
            operationName: 'api_call',
            errorMessage: 'Unauthorized',
            stackTrace: 'Error: Unauthorized\n  at ...'
          }
        ]
      })
    ),
  }
}))

describe('ErrorAnalysis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render error analysis component', async () => {
    render(<ErrorAnalysis />)
    
    await waitFor(() => {
      expect(screen.getByText(/Error Analysis/i)).toBeInTheDocument()
    })
  })

  it('should display error rate over time', async () => {
    render(<ErrorAnalysis />)
    
    await waitFor(() => {
      expect(screen.getByText(/Error Summary/i)).toBeInTheDocument()
    })
  })

  it('should show error count by operation', async () => {
    render(<ErrorAnalysis />)

    await waitFor(() => {
      // Get all elements with "database_query" text
      const elements = screen.getAllByText('database_query')
      expect(elements.length).toBeGreaterThan(0)
      
      // Check for the count in the table
      expect(screen.getByText('50')).toBeInTheDocument()
    })
  })

  it('should display recent errors with messages', async () => {
    render(<ErrorAnalysis />)

    await waitFor(() => {
      expect(screen.getByText('Connection timeout')).toBeInTheDocument()
      expect(screen.getByText('Unauthorized')).toBeInTheDocument()
    })
  })

  it('should calculate and display error rates', async () => {
    render(<ErrorAnalysis />)

    await waitFor(() => {
      expect(screen.getByText(/Error Rate/i)).toBeInTheDocument()
      expect(screen.getByText(/5.00%/)).toBeInTheDocument()
    })
  })
})
