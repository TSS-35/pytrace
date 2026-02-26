import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Dashboard } from '../../src/components/Dashboard'

vi.mock('axios')

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render main dashboard with all sections', () => {
    render(<Dashboard />)
    
    expect(screen.getByText(/Distributed Tracing Dashboard/i)).toBeInTheDocument()
    expect(screen.getByText(/Latency/i)).toBeInTheDocument()
    expect(screen.getByText(/Errors/i)).toBeInTheDocument()
  })

  it('should have navigation tabs for different views', () => {
    render(<Dashboard />)
    
    // Check for button elements instead of role="tab"
    const buttons = screen.getAllByRole('button')
    const tabButtons = buttons.filter(btn => 
      /Trace Explorer|Operations|Latency|Errors/.test(btn.textContent || '')
    )
    expect(tabButtons.length).toBeGreaterThanOrEqual(3)
  })

  it('should switch between tabs when clicked', async () => {
    const user = userEvent.setup()
    render(<Dashboard />)
    
    const latencyButton = screen.getByRole('button', { name: /Latency/i })
    await user.click(latencyButton)
    
    await waitFor(() => {
      expect(latencyButton).toHaveClass('active')
    })
  })

  it('should display responsive layout', () => {
    const { container } = render(<Dashboard />)
    
    // Check for main dashboard element
    expect(container.querySelector('.dashboard')).toBeInTheDocument()
  })

  it('should handle auto-refresh toggle', async () => {
    const user = userEvent.setup()
    render(<Dashboard />)
    
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).toBeChecked()
    
    await user.click(checkbox)
    expect(checkbox).not.toBeChecked()
  })

  it('should render all tab buttons', () => {
    render(<Dashboard />)
    
    // Check for all tab buttons exist
    expect(screen.getByRole('button', { name: /Trace Explorer/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Operations/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Latency/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Errors/i })).toBeInTheDocument()
  })
})
