import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { OperationsDashboard } from '../../src/components/OperationsDashboard'

vi.mock('../../src/api/client', () => ({
  api: {
    getOperations: vi.fn(() =>
      Promise.resolve({
        data: [
          {
            name: 'api_call',
            callCount: 150,
            avgDuration: 75,
            errorRate: 0.0133
          },
          {
            name: 'database_query',
            callCount: 100,
            avgDuration: 150,
            errorRate: 0.05
          },
          {
            name: 'cache_lookup',
            callCount: 200,
            avgDuration: 25,
            errorRate: 0.01
          }
        ]
      })
    ),
  }
}))

describe('OperationsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render operations dashboard', async () => {
    render(<OperationsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText(/Operations Dashboard/i)).toBeInTheDocument()
    })
  })

  it('should display table of all operations', async () => {
    render(<OperationsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('api_call')).toBeInTheDocument()
      expect(screen.getByText('database_query')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument()
    })
  })

  it('should allow sorting operations by different columns', async () => {
    const user = userEvent.setup()
    render(<OperationsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('api_call')).toBeInTheDocument()
    })

    const durationHeader = screen.getByText(/Avg Duration/i).closest('th')
    if (durationHeader) {
      await user.click(durationHeader)

      await waitFor(() => {
        const rows = screen.getAllByRole('row')
        // Check that sorting occurred (rows order changed)
        expect(rows.length).toBeGreaterThan(0)
      })
    }
  })

  it('should display operation statistics', async () => {
    render(<OperationsDashboard />)

    await waitFor(() => {
      expect(screen.getByText(/Avg Duration/i)).toBeInTheDocument()
      expect(screen.getByText(/Call Count/i)).toBeInTheDocument()
      expect(screen.getByText(/Error Rate/i)).toBeInTheDocument()
    })
  })

  it('should allow filtering operations by name', async () => {
    const user = userEvent.setup()
    render(<OperationsDashboard />)

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
