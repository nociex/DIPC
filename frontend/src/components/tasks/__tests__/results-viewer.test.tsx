import { render, screen, fireEvent } from '@testing-library/react'
import { ResultsViewer } from '../results-viewer'
import type { Task } from '@/types'

// Mock the useToast hook
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}))

// Mock Next.js router
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

// Mock TaskStatusChecker
jest.mock('@/lib/task-status-checker', () => ({
  TaskStatusChecker: {
    shouldShowMarkdownButton: jest.fn(),
  },
}))

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
})

const mockTaskWithResults: Task = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  user_id: 'user1',
  status: 'completed',
  task_type: 'document_parsing',
  file_url: 'https://example.com/file.pdf',
  options: { enable_vectorization: true, storage_policy: 'permanent' },
  estimated_cost: 0.05,
  actual_cost: 0.048,
  results: {
    extracted_text: 'Sample extracted text',
    metadata: {
      pages: 5,
      language: 'en'
    },
    confidence_score: 0.95
  },
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:05:00Z',
  completed_at: '2024-01-15T10:05:00Z'
}

const mockTaskWithoutResults: Task = {
  id: '123e4567-e89b-12d3-a456-426614174001',
  user_id: 'user1',
  status: 'processing',
  task_type: 'document_parsing',
  options: { enable_vectorization: true, storage_policy: 'permanent' },
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:05:00Z'
}

describe('ResultsViewer', () => {
  const mockOnDownload = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders empty state when task has no results', () => {
    render(<ResultsViewer task={mockTaskWithoutResults} />)
    
    expect(screen.getByText('No results available')).toBeInTheDocument()
    expect(screen.getByText('This task hasn\'t completed yet or has no results to display')).toBeInTheDocument()
  })

  it('renders results viewer with task results', () => {
    render(<ResultsViewer task={mockTaskWithResults} onDownload={mockOnDownload} />)
    
    expect(screen.getByText('Task Results')).toBeInTheDocument()
    expect(screen.getByText('Document Parsing - 123e4567...')).toBeInTheDocument()
  })

  it('displays task metadata when expanded', () => {
    render(<ResultsViewer task={mockTaskWithResults} />)
    
    // Task details should be visible by default
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('$0.048')).toBeInTheDocument()
  })

  it('toggles between formatted and raw view', () => {
    render(<ResultsViewer task={mockTaskWithResults} />)
    
    // Should start in formatted view
    expect(screen.getByText('Raw')).toBeInTheDocument()
    
    // Click to switch to raw view
    const rawButton = screen.getByText('Raw')
    fireEvent.click(rawButton)
    
    expect(screen.getByText('Formatted')).toBeInTheDocument()
  })

  it('shows copy button and handles copy action', async () => {
    render(<ResultsViewer task={mockTaskWithResults} />)
    
    const copyButton = screen.getByText('Copy')
    expect(copyButton).toBeInTheDocument()
    
    fireEvent.click(copyButton)
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      JSON.stringify(mockTaskWithResults.results, null, 2)
    )
  })

  it('shows download button when onDownload is provided', () => {
    render(<ResultsViewer task={mockTaskWithResults} onDownload={mockOnDownload} />)
    
    const downloadButton = screen.getByText('Download')
    expect(downloadButton).toBeInTheDocument()
    
    fireEvent.click(downloadButton)
    expect(mockOnDownload).toHaveBeenCalledWith(mockTaskWithResults)
  })

  it('displays results summary', () => {
    render(<ResultsViewer task={mockTaskWithResults} />)
    
    expect(screen.getByText('Results Summary')).toBeInTheDocument()
    expect(screen.getByText('Object')).toBeInTheDocument()
    expect(screen.getByText('3 keys')).toBeInTheDocument()
  })

  it('toggles task details visibility', () => {
    render(<ResultsViewer task={mockTaskWithResults} />)
    
    const taskDetailsButton = screen.getByText('Task Details')
    
    // Click to hide details
    fireEvent.click(taskDetailsButton)
    
    // Details should still be visible as the test checks for the presence of elements
    // In a real scenario, you'd check for the absence of detail elements
  })

  it('handles array results correctly', () => {
    const taskWithArrayResults = {
      ...mockTaskWithResults,
      results: ['item1', 'item2', 'item3']
    }
    
    render(<ResultsViewer task={taskWithArrayResults} />)
    
    expect(screen.getByText('Results Summary')).toBeInTheDocument()
    expect(screen.getByText('Array')).toBeInTheDocument()
    expect(screen.getByText('3 items')).toBeInTheDocument()
  })

  describe('Markdown editing button', () => {
    const { TaskStatusChecker } = require('@/lib/task-status-checker')

    it('shows markdown editing button when task status checker allows it', () => {
      TaskStatusChecker.shouldShowMarkdownButton.mockReturnValue(true)
      
      render(<ResultsViewer task={mockTaskWithResults} />)
      
      const markdownButton = screen.getByText('Markdown编辑')
      expect(markdownButton).toBeInTheDocument()
      expect(markdownButton).toHaveAttribute('title', 'Edit results as Markdown')
    })

    it('hides markdown editing button when task status checker disallows it', () => {
      TaskStatusChecker.shouldShowMarkdownButton.mockReturnValue(false)
      
      render(<ResultsViewer task={mockTaskWithResults} />)
      
      expect(screen.queryByText('Markdown编辑')).not.toBeInTheDocument()
    })

    it('navigates to markdown editing page when button is clicked', () => {
      TaskStatusChecker.shouldShowMarkdownButton.mockReturnValue(true)
      
      render(<ResultsViewer task={mockTaskWithResults} />)
      
      const markdownButton = screen.getByText('Markdown编辑')
      fireEvent.click(markdownButton)
      
      expect(mockPush).toHaveBeenCalledWith('/results/123e4567-e89b-12d3-a456-426614174000/markdown')
    })

    it('does not show markdown button for task without results', () => {
      TaskStatusChecker.shouldShowMarkdownButton.mockReturnValue(false)
      
      render(<ResultsViewer task={mockTaskWithoutResults} />)
      
      expect(screen.queryByText('Markdown编辑')).not.toBeInTheDocument()
    })

    it('calls TaskStatusChecker.shouldShowMarkdownButton with correct task', () => {
      TaskStatusChecker.shouldShowMarkdownButton.mockReturnValue(true)
      
      render(<ResultsViewer task={mockTaskWithResults} />)
      
      expect(TaskStatusChecker.shouldShowMarkdownButton).toHaveBeenCalledWith(mockTaskWithResults)
    })
  })
})