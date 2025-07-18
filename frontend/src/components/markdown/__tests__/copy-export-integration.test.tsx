/**
 * Integration test for copy and export functionality
 */
import { render, screen, fireEvent } from '@testing-library/react'
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

// Mock Radix UI dropdown menu
jest.mock('@radix-ui/react-dropdown-menu', () => ({
  Root: ({ children, onOpenChange }: any) => <div data-testid="dropdown-root">{children}</div>,
  Trigger: ({ children, asChild, ...props }: any) => {
    if (asChild) {
      return <div {...props}>{children}</div>
    }
    return <button {...props}>{children}</button>
  },
  Portal: ({ children }: any) => <div data-testid="dropdown-portal">{children}</div>,
  Content: ({ children, ...props }: any) => <div {...props} data-testid="dropdown-content">{children}</div>,
  Item: ({ children, onClick, ...props }: any) => (
    <div {...props} onClick={onClick} role="menuitem" style={{ cursor: 'pointer' }}>
      {children}
    </div>
  ),
  Group: ({ children }: any) => <div>{children}</div>,
  Label: ({ children }: any) => <div>{children}</div>,
  Separator: () => <hr />,
  Sub: ({ children }: any) => <div>{children}</div>,
  SubTrigger: ({ children }: any) => <div>{children}</div>,
  SubContent: ({ children }: any) => <div>{children}</div>,
  RadioGroup: ({ children }: any) => <div>{children}</div>,
  RadioItem: ({ children }: any) => <div>{children}</div>,
  CheckboxItem: ({ children }: any) => <div>{children}</div>,
}))

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

describe('Copy and Export Integration', () => {
  const mockOnBack = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render copy button', () => {
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    expect(screen.getByText('复制')).toBeInTheDocument()
  })

  it('should render export dropdown with both options', async () => {
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    // Find the export button
    const exportButton = screen.getByText('导出')
    expect(exportButton).toBeInTheDocument()
    
    // Click to open dropdown
    fireEvent.click(exportButton)
    
    // Wait for dropdown options to appear
    await screen.findByText('导出为 Markdown (.md)')
    await screen.findByText('导出为 HTML (.html)')
    
    // Check for dropdown options
    expect(screen.getByText('导出为 Markdown (.md)')).toBeInTheDocument()
    expect(screen.getByText('导出为 HTML (.html)')).toBeInTheDocument()
  })

  it('should call copy function when copy button is clicked', async () => {
    const { ExportManager } = require('@/lib/export-manager')
    
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    const copyButton = screen.getByText('复制')
    fireEvent.click(copyButton)
    
    expect(ExportManager.copyToClipboard).toHaveBeenCalled()
  })

  it('should call export markdown function when markdown export is clicked', async () => {
    const { ExportManager } = require('@/lib/export-manager')
    
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    // Open export dropdown
    const exportButton = screen.getByText('导出')
    fireEvent.click(exportButton)
    
    // Wait for and click markdown export option
    const markdownOption = await screen.findByText('导出为 Markdown (.md)')
    fireEvent.click(markdownOption)
    
    expect(ExportManager.exportMarkdown).toHaveBeenCalled()
  })

  it('should call export HTML function when HTML export is clicked', async () => {
    const { ExportManager } = require('@/lib/export-manager')
    
    render(<MarkdownEditorContainer task={mockTask} onBack={mockOnBack} />)
    
    // Open export dropdown
    const exportButton = screen.getByText('导出')
    fireEvent.click(exportButton)
    
    // Wait for and click HTML export option
    const htmlOption = await screen.findByText('导出为 HTML (.html)')
    fireEvent.click(htmlOption)
    
    expect(ExportManager.exportHtml).toHaveBeenCalled()
  })
})