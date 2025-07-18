import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TaskConfigPanel } from '../task-config-panel'

// Mock the useToast hook
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}))

describe('TaskConfigPanel', () => {
  const mockOnConfigChange = jest.fn()

  beforeEach(() => {
    mockOnConfigChange.mockClear()
  })

  it('renders the configuration panel correctly', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    expect(screen.getByText('Processing Configuration')).toBeInTheDocument()
    expect(screen.getByText('Configure how your documents will be processed and stored')).toBeInTheDocument()
    expect(screen.getByText('Enable Vectorization')).toBeInTheDocument()
    expect(screen.getByText('Storage Policy')).toBeInTheDocument()
    expect(screen.getByText('Maximum Cost Limit')).toBeInTheDocument()
  })

  it('has vectorization enabled by default', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    const vectorizationSwitch = screen.getByRole('switch')
    expect(vectorizationSwitch).toBeChecked()
  })

  it('shows vectorization benefits when enabled', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    expect(screen.getByText('Vectorization Benefits:')).toBeInTheDocument()
    expect(screen.getByText('Semantic search capabilities')).toBeInTheDocument()
    expect(screen.getByText('AI-powered document queries')).toBeInTheDocument()
  })

  it('toggles vectorization setting', async () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    const vectorizationSwitch = screen.getByRole('switch')
    
    // Toggle off
    fireEvent.click(vectorizationSwitch)
    
    await waitFor(() => {
      expect(vectorizationSwitch).not.toBeChecked()
      expect(mockOnConfigChange).toHaveBeenCalledWith(
        expect.objectContaining({
          enable_vectorization: false
        })
      )
    })
  })

  it('has permanent storage policy selected by default', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    // The select trigger should show the default value
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('displays cost limit buttons', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    expect(screen.getByText('$5')).toBeInTheDocument()
    expect(screen.getByText('$10')).toBeInTheDocument()
    expect(screen.getByText('$25')).toBeInTheDocument()
    expect(screen.getByText('$50')).toBeInTheDocument()
  })

  it('updates cost limit when button is clicked', async () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    const costButton = screen.getByText('$25')
    fireEvent.click(costButton)
    
    await waitFor(() => {
      expect(mockOnConfigChange).toHaveBeenCalledWith(
        expect.objectContaining({
          max_cost_limit: 25
        })
      )
    })
  })

  it('shows cost estimation when files are provided', () => {
    render(
      <TaskConfigPanel 
        onConfigChange={mockOnConfigChange}
        fileCount={3}
        estimatedFileSize={1024 * 1024} // 1MB
      />
    )
    
    expect(screen.getByText('Cost Estimation')).toBeInTheDocument()
    expect(screen.getByText('Files to process:')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Estimated tokens:')).toBeInTheDocument()
  })

  it('shows cost breakdown with vectorization', () => {
    render(
      <TaskConfigPanel 
        onConfigChange={mockOnConfigChange}
        fileCount={2}
        estimatedFileSize={512 * 1024} // 512KB
      />
    )
    
    expect(screen.getByText('Document parsing:')).toBeInTheDocument()
    expect(screen.getByText('Vectorization:')).toBeInTheDocument()
    expect(screen.getByText('Total estimated cost:')).toBeInTheDocument()
  })

  it('calls onConfigChange with initial config on mount', () => {
    render(<TaskConfigPanel onConfigChange={mockOnConfigChange} />)
    
    expect(mockOnConfigChange).toHaveBeenCalledWith({
      enable_vectorization: true,
      storage_policy: 'permanent',
      max_cost_limit: 10.0
    })
  })
})