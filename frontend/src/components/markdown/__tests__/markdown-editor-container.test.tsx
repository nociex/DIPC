/**
 * Tests for MarkdownEditorContainer component
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MarkdownEditorContainer } from '../markdown-editor-container'
import type { Task } from '@/types'

// Mock the toast hook
jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}))

// Mock ExportManager
jest.mock('@/lib/export-manager', () => ({
  ExportManager: {
    copyToClipboard: jest.fn().mockResolvedValue(undefined),
    exportMarkdown: jest.fn().mockResolvedValue(undefined),
    exportHtml: jest.fn().mockResolvedValue(undefined),
    generateFilename: jest.fn().mockReturnValue('test-file.md'),
    isClipboardSupported: jest.fn().mockReturnValue(true),
    isDownloadSupported: jest.fn().mockReturnValue(true)
  }
}))

// Mock JsonToMarkdownConverter
jest.mock('@/lib/json-to-markdown', () => ({
  JsonToMarkdownConverter: {
    convert: jest.fn().mockReturnValue({
      markdown: '# Test Content\n\nThis is test content',
      isTruncated: false,
      originalSize: 100,
      truncatedSize: 100,
      warnings: []
    })
  }
}))

// Mock react-markdown
jest.mock('react-markdown', () => {
  return function MockReactMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown-preview">{children}</div>
  }
})

// Mock remark-gfm
jest.mock('remark-gfm', () => () => {})

const mockTask: Task = {
  id: 'test-task-123',
  task_type: 'document_parsing',
  status: 'completed',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  results: {
    title: 'Test Document',
    content: 'This is test content'
  }
}

describe('MarkdownEditorContainer', () => {
  const mockOnBack = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render the markdown editor container', () => {
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    expect(screen.getByText('Markdown编辑器')).toBeInTheDocument()
    expect(screen.getByText(/Document Parsing/)).toBeInTheDocument()
  })

  it('should render copy and export buttons', () => {
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    expect(screen.getByText('复制')).toBeInTheDocument()
    expect(screen.getByText('导出')).toBeInTheDocument()
  })

  it('should call onBack when back button is clicked', () => {
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    const backButton = screen.getByText('返回结果')
    fireEvent.click(backButton)
    
    expect(mockOnBack).toHaveBeenCalled()
  })
})