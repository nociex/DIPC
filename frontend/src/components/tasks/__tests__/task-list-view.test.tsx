import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TaskListView } from '../task-list-view'
import type { Task } from '@/types'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { it } from 'node:test'
import { beforeEach } from 'node:test'
import { describe } from 'node:test'

// Mock the useToast hook
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}))

const mockTasks: Task[] = [
  {
    id: '123e4567-e89b-12d3-a456-426614174000',
    user_id: 'user1',
    status: 'completed',
    task_type: 'document_parsing',
    file_url: 'https://example.com/file.pdf',
    options: { enable_vectorization: true, storage_policy: 'permanent' },
    estimated_cost: 0.05,
    actual_cost: 0.048,
    results: { extracted_text: 'Sample text' },
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:05:00Z',
    completed_at: '2024-01-15T10:05:00Z'
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174001',
    user_id: 'user1',
    status: 'processing',
    task_type: 'archive_processing',
    file_url: 'https://example.com/archive.zip',
    options: { enable_vectorization: false, storage_policy: 'temporary' },
    estimated_cost: 0.12,
    created_at: '2024-01-15T10:10:00Z',
    updated_at: '2024-01-15T10:12:00Z'
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174002',
    user_id: 'user1',
    status: 'failed',
    task_type: 'document_parsing',
    options: { enable_vectorization: true, storage_policy: 'permanent' },
    error_message: 'Failed to parse document: Invalid format',
    created_at: '2024-01-15T09:00:00Z',
    updated_at: '2024-01-15T09:02:00Z'
  }
]

describe('TaskListView', () => {
  const mockOnRefresh = jest.fn()
  const mockOnViewResults = jest.fn()
  const mockOnDownloadResults = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders empty state when no tasks', () => {
    render(<TaskListView tasks={[]} />)
    
    expect(screen.getByText('No tasks yet')).toBeInTheDocument()
    expect(screen.getByText('Upload some documents to get started')).toBeInTheDocument()
  })

  it('renders task list with tasks', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
        onViewResults={mockOnViewResults}
        onDownloadResults={mockOnDownloadResults}
      />
    )
    
    expect(screen.getByText('Task Monitor')).toBeInTheDocument()
    expect(screen.getAllByText('Document Parsing')).toHaveLength(2) // Two document parsing tasks
    expect(screen.getByText('Archive Processing')).toBeInTheDocument()
  })

  it('displays task statistics', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    expect(screen.getByText('1 completed')).toBeInTheDocument()
    expect(screen.getByText('1 processing')).toBeInTheDocument()
    expect(screen.getByText('1 failed')).toBeInTheDocument()
  })

  it('shows task status badges correctly', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('displays task details', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    // Check for task IDs (truncated) - there should be multiple
    expect(screen.getAllByText(/ID: 123e4567\.\.\./)).toHaveLength(3)
    
    // Check for costs
    expect(screen.getByText('$0.050')).toBeInTheDocument()
    expect(screen.getByText('$0.048')).toBeInTheDocument()
  })

  it('shows error messages for failed tasks', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    expect(screen.getByText('Error:')).toBeInTheDocument()
    expect(screen.getByText('Failed to parse document: Invalid format')).toBeInTheDocument()
  })

  it('shows action buttons for completed tasks', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onViewResults={mockOnViewResults}
        onDownloadResults={mockOnDownloadResults}
      />
    )
    
    const viewButtons = screen.getAllByText('View')
    const downloadButtons = screen.getAllByText('Download')
    
    expect(viewButtons).toHaveLength(1) // Only completed task should have buttons
    expect(downloadButtons).toHaveLength(1)
  })

  it('calls onViewResults when view button is clicked', async () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onViewResults={mockOnViewResults}
        onDownloadResults={mockOnDownloadResults}
      />
    )
    
    const viewButton = screen.getByText('View')
    fireEvent.click(viewButton)
    
    expect(mockOnViewResults).toHaveBeenCalledWith(mockTasks[0])
  })

  it('calls onDownloadResults when download button is clicked', async () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onViewResults={mockOnViewResults}
        onDownloadResults={mockOnDownloadResults}
      />
    )
    
    const downloadButton = screen.getByText('Download')
    fireEvent.click(downloadButton)
    
    expect(mockOnDownloadResults).toHaveBeenCalledWith(mockTasks[0])
  })

  it('calls onRefresh when refresh button is clicked', async () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    const refreshButton = screen.getByText('Refresh')
    fireEvent.click(refreshButton)
    
    expect(mockOnRefresh).toHaveBeenCalled()
  })

  it('shows progress for processing tasks', () => {
    render(
      <TaskListView 
        tasks={mockTasks}
        onRefresh={mockOnRefresh}
      />
    )
    
    expect(screen.getByText('Processing... 25%')).toBeInTheDocument()
  })
})