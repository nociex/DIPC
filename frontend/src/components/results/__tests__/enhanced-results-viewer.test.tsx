import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EnhancedResultsViewer } from '../enhanced-results-viewer'
import { TaskStatus, TaskType } from '@/types'
import type { Task } from '@/types'

// Mock the toast hook
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}))

// Mock the i18n hook
jest.mock('@/lib/i18n/context', () => ({
  useI18n: () => ({
    t: (key: string, params?: any) => {
      // Simple mock translation function
      const translations: Record<string, string> = {
        'results.title': 'Processing Results',
        'results.noResults': 'No results available',
        'results.search.placeholder': 'Search in results...',
        'results.view.preview': 'Preview',
        'results.view.detailed': 'Detailed',
        'results.view.raw': 'Raw Data',
        'common.download': 'Download',
        'common.share': 'Share',
        'common.success': 'Success',
        'common.error': 'Error'
      }
      
      let result = translations[key] || key
      
      // Handle parameter substitution
      if (params) {
        Object.entries(params).forEach(([paramKey, value]) => {
          result = result.replace(`{{${paramKey}}}`, String(value))
        })
      }
      
      return result
    },
    language: 'en'
  })
}))

const mockTask: Task = {
  id: 'test-task-123',
  user_id: 'user-123',
  status: TaskStatus.COMPLETED,
  task_type: TaskType.DOCUMENT_PARSING,
  original_filename: 'test-document.pdf',
  options: {
    enable_vectorization: true,
    storage_policy: 'temporary' as any
  },
  results: {
    extracted_content: {
      title: 'Test Document',
      content: 'This is a test document with some content',
      metadata: {
        pages: 5,
        language: 'en'
      }
    },
    confidence_score: 0.95,
    processing_time: 2.5,
    entities: [
      { name: 'Test Entity', type: 'ORGANIZATION' },
      { name: 'Another Entity', type: 'PERSON' }
    ],
    numbers: [123, 456.78, 999],
    nested_array: [
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' }
    ]
  },
  actual_cost: 0.025,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:02:30Z',
  completed_at: '2024-01-01T10:02:30Z'
}

// Mock clipboard API globally
const mockWriteText = jest.fn().mockResolvedValue(undefined)
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: mockWriteText
  },
  writable: true
})

describe('EnhancedResultsViewer', () => {
  beforeEach(() => {
    // Reset clipboard mock
    mockWriteText.mockClear()
  })

  it('renders task results with basic information', () => {
    render(<EnhancedResultsViewer task={mockTask} />)
    
    expect(screen.getByText('Processing Results')).toBeInTheDocument()
    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
    expect(screen.getByText('document_parsing')).toBeInTheDocument()
  })

  it('displays no results message when task has no results', () => {
    const taskWithoutResults = { ...mockTask, results: undefined }
    render(<EnhancedResultsViewer task={taskWithoutResults} />)
    
    expect(screen.getByText('No results available')).toBeInTheDocument()
  })

  it('switches between view modes correctly', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    // Should start in preview mode
    expect(screen.getByRole('tab', { selected: true })).toHaveTextContent('Preview')
    
    // Switch to detailed view
    await user.click(screen.getByRole('tab', { name: 'Detailed' }))
    expect(screen.getByText('Results Analysis')).toBeInTheDocument()
    expect(screen.getByText('Data Type:')).toBeInTheDocument()
    
    // Switch to raw view
    await user.click(screen.getByRole('tab', { name: 'Raw Data' }))
    expect(screen.getByText(/"extracted_content"/)).toBeInTheDocument()
  })

  it('performs search functionality correctly', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    const searchInput = screen.getByPlaceholderText('Search in results...')
    
    // Search for "Test"
    await user.type(searchInput, 'Test')
    
    await waitFor(() => {
      expect(screen.getByText('Search Results')).toBeInTheDocument()
      expect(screen.getByText(/result.*found/)).toBeInTheDocument()
    })
  })

  it('filters search results by type', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    // First search for something
    const searchInput = screen.getByPlaceholderText('Search in results...')
    await user.type(searchInput, 'Test')
    
    // Then filter by text type
    const filterSelect = screen.getByRole('combobox')
    await user.click(filterSelect)
    await user.click(screen.getByText('Text'))
    
    await waitFor(() => {
      expect(screen.getByText('Search Results')).toBeInTheDocument()
    })
  })

  it('expands and collapses JSON sections', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    // Find an expandable section
    const expandButton = screen.getAllByRole('button').find(button => 
      button.textContent?.includes('keys') || button.textContent?.includes('items')
    )
    
    if (expandButton) {
      await user.click(expandButton)
      // The section should toggle its expanded state
    }
  })

  it('copies results to clipboard', async () => {
    const user = userEvent.setup()
    
    render(<EnhancedResultsViewer task={mockTask} />)
    
    const copyButton = screen.getByRole('button', { name: /copy/i })
    await user.click(copyButton)
    
    expect(mockWriteText).toHaveBeenCalledWith(
      JSON.stringify(mockTask.results, null, 2)
    )
  })

  it('toggles fullscreen mode', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    const fullscreenButton = screen.getByRole('button', { name: '' }) // Maximize icon
    await user.click(fullscreenButton)
    
    // Check if the component has fullscreen classes
    const card = screen.getByRole('tabpanel').closest('.fixed')
    expect(card).toBeInTheDocument()
  })

  it('calls onDownload when download button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnDownload = jest.fn()
    
    render(
      <EnhancedResultsViewer task={mockTask} onDownload={mockOnDownload} />
    )
    
    const downloadButton = screen.getByRole('button', { name: /download/i })
    await user.click(downloadButton)
    
    expect(mockOnDownload).toHaveBeenCalledWith(mockTask)
  })

  it('calls onShare when share button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnShare = jest.fn()
    
    render(
      <EnhancedResultsViewer task={mockTask} onShare={mockOnShare} />
    )
    
    const shareButton = screen.getByRole('button', { name: /share/i })
    await user.click(shareButton)
    
    expect(mockOnShare).toHaveBeenCalledWith(mockTask)
  })

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup()
    const mockOnClose = jest.fn()
    
    render(
      <EnhancedResultsViewer task={mockTask} onClose={mockOnClose} />
    )
    
    const closeButton = screen.getByRole('button', { name: '×' })
    await user.click(closeButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('handles path clicks in JSON viewer', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    // Search for something first to make path buttons visible
    const searchInput = screen.getByPlaceholderText('Search in results...')
    await user.type(searchInput, 'extracted_content')
    
    await waitFor(() => {
      const pathButton = screen.getByText('extracted_content')
      if (pathButton) {
        fireEvent.click(pathButton)
        expect(searchInput).toHaveValue('extracted_content')
      }
    })
  })

  it('displays task metadata in detailed view', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    // Switch to detailed view
    await user.click(screen.getByRole('tab', { name: 'Detailed' }))
    
    expect(screen.getByText('Status:')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('Cost:')).toBeInTheDocument()
    expect(screen.getByText('$0.025')).toBeInTheDocument()
  })

  it('shows search results count correctly', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    const searchInput = screen.getByPlaceholderText('Search in results...')
    await user.type(searchInput, 'Test')
    
    await waitFor(() => {
      expect(screen.getByText(/\d+ result.*found/)).toBeInTheDocument()
    })
  })

  it('highlights search terms in JSON viewer', async () => {
    const user = userEvent.setup()
    render(<EnhancedResultsViewer task={mockTask} />)
    
    const searchInput = screen.getByPlaceholderText('Search in results...')
    await user.type(searchInput, 'Test')
    
    await waitFor(() => {
      const highlightedElements = screen.getAllByText('Test')
      expect(highlightedElements.length).toBeGreaterThan(0)
    })
  })
})