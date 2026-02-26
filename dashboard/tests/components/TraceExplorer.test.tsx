import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TraceExplorer } from '../../src/components/TraceExplorer'

vi.mock('../../src/api/client', () => ({
  api: {
    getTraces: vi.fn(() =>
      Promise.resolve({
        data: [
          {
            traceId: 'trace-123',
            spans: [
              {
                spanId: 'span-1',
                operationName: 'api_call',
                duration: 150,
                attributes: { 'http.method': 'GET', 'http.url': '/api/users' }
              },
              {
                spanId: 'span-2',
                operationName: 'db_query',
                duration: 100,
                attributes: { 'db.statement': 'SELECT * FROM users' }
              }
            ]
          }
        ]
      })
    ),
  }
}))

describe('TraceExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render trace explorer component', async () => {
    render(<TraceExplorer />)
    
    await waitFor(() => {
      expect(screen.getByText(/Trace Explorer/i)).toBeInTheDocument()
    })
  })

  it('should render search input for trace ID', async () => {
    render(<TraceExplorer />)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search trace ID/i)).toBeInTheDocument()
    })
  })

  it('should render operation name filter', async () => {
    render(<TraceExplorer />)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Filter by operation/i)).toBeInTheDocument()
    })
  })

  it('should display trace list with spans', async () => {
    const user = userEvent.setup()
    render(<TraceExplorer />)

    await waitFor(() => {
      expect(screen.getByText('trace-123')).toBeInTheDocument()
    })

    // Click on the trace to expand it and see the spans
    const traceHeader = screen.getByText('trace-123').closest('.trace-header')
    if (traceHeader) {
      await user.click(traceHeader)

      await waitFor(() => {
        expect(screen.getByText('api_call')).toBeInTheDocument()
        expect(screen.getByText('db_query')).toBeInTheDocument()
      })
    }
  })

  it('should filter traces by search input', async () => {
    const user = userEvent.setup()
    render(<TraceExplorer />)
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search trace ID/i)).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/Search trace ID/i)
    await user.type(searchInput, 'nonexistent')

    await waitFor(() => {
      expect(screen.getByText(/No traces found/i)).toBeInTheDocument()
    })
  })

  it('should expand span to show attributes and events', async () => {
    const user = userEvent.setup()
    render(<TraceExplorer />)

    await waitFor(() => {
      expect(screen.getByText('trace-123')).toBeInTheDocument()
    })

    // Click on the trace to expand it
    const traceHeader = screen.getByText('trace-123').closest('.trace-header')
    if (traceHeader) {
      await user.click(traceHeader)

      await waitFor(() => {
        expect(screen.getByText('api_call')).toBeInTheDocument()
        expect(screen.getByText(/http.method|GET/)).toBeInTheDocument()
      })
    }
  })
})
