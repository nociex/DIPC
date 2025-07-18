import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MarkdownToolbar, type FormatType } from '../markdown-toolbar'

// Mock the textarea element for testing
const createMockTextarea = (value = '', selectionStart = 0, selectionEnd = 0) => {
  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.selectionStart = selectionStart
  textarea.selectionEnd = selectionEnd
  
  // Mock the dispatchEvent method
  textarea.dispatchEvent = jest.fn()
  
  return textarea
}

describe('MarkdownToolbar', () => {
  const mockOnFormat = jest.fn()
  
  beforeEach(() => {
    mockOnFormat.mockClear()
    // Clear any focused elements
    document.body.focus()
  })

  afterEach(() => {
    // Clean up any event listeners
    document.removeEventListener('keydown', jest.fn())
  })

  it('renders all toolbar buttons', () => {
    render(<MarkdownToolbar onFormat={mockOnFormat} />)
    
    // Check for all format buttons
    expect(screen.getByTitle(/加粗.*Ctrl\+B/)).toBeInTheDocument()
    expect(screen.getByTitle(/斜体.*Ctrl\+I/)).toBeInTheDocument()
    expect(screen.getByTitle(/一级标题.*Ctrl\+1/)).toBeInTheDocument()
    expect(screen.getByTitle(/二级标题.*Ctrl\+2/)).toBeInTheDocument()
    expect(screen.getByTitle(/三级标题.*Ctrl\+3/)).toBeInTheDocument()
    expect(screen.getByTitle(/无序列表.*Ctrl\+U/)).toBeInTheDocument()
    expect(screen.getByTitle(/有序列表.*Ctrl\+O/)).toBeInTheDocument()
    expect(screen.getByTitle(/链接.*Ctrl\+K/)).toBeInTheDocument()
    expect(screen.getByTitle(/代码.*Ctrl\+`/)).toBeInTheDocument()
    expect(screen.getByTitle(/引用.*Ctrl\+Q/)).toBeInTheDocument()
  })

  it('calls onFormat when buttons are clicked', async () => {
    const user = userEvent.setup()
    render(<MarkdownToolbar onFormat={mockOnFormat} />)
    
    const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
    await user.click(boldButton)
    
    expect(mockOnFormat).toHaveBeenCalledWith('bold', '')
  })

  it('is disabled when disabled prop is true', () => {
    render(<MarkdownToolbar onFormat={mockOnFormat} disabled={true} />)
    
    const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
    expect(boldButton).toBeDisabled()
  })

  it('applies custom className', () => {
    const { container } = render(
      <MarkdownToolbar onFormat={mockOnFormat} className="custom-class" />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })

  describe('Text formatting with textarea interaction', () => {
    beforeEach(() => {
      // Mock document.activeElement
      Object.defineProperty(document, 'activeElement', {
        writable: true,
        value: null
      })
    })

    it('formats selected text in textarea', async () => {
      const user = userEvent.setup()
      const textarea = createMockTextarea('Hello world', 0, 5) // Select "Hello"
      
      // Mock document.activeElement to return our textarea
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
      await user.click(boldButton)
      
      // Check that the textarea value was updated
      expect(textarea.value).toBe('**Hello** world')
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '**Hello**')
    })

    it('inserts placeholder text when no text is selected', async () => {
      const user = userEvent.setup()
      const textarea = createMockTextarea('Hello world', 5, 5) // Cursor at position 5
      
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
      await user.click(boldButton)
      
      expect(textarea.value).toBe('Hello**加粗文本** world')
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '**加粗文本**')
    })

    it('handles different format types correctly', async () => {
      const user = userEvent.setup()
      const textarea = createMockTextarea('test', 0, 4)
      
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      // Test italic formatting
      const italicButton = screen.getByTitle(/斜体.*Ctrl\+I/)
      await user.click(italicButton)
      expect(textarea.value).toBe('*test*')
      
      // Reset textarea
      textarea.value = 'test'
      textarea.selectionStart = 0
      textarea.selectionEnd = 4
      
      // Test heading formatting
      const h1Button = screen.getByTitle(/一级标题.*Ctrl\+1/)
      await user.click(h1Button)
      expect(textarea.value).toBe('# test')
      
      // Reset textarea
      textarea.value = 'test'
      textarea.selectionStart = 0
      textarea.selectionEnd = 4
      
      // Test link formatting
      const linkButton = screen.getByTitle(/链接.*Ctrl\+K/)
      await user.click(linkButton)
      expect(textarea.value).toBe('[test](url)')
    })
  })

  describe('Keyboard shortcuts', () => {
    it('handles Ctrl+B for bold formatting', () => {
      const textarea = createMockTextarea('Hello', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      // Simulate Ctrl+B keydown
      fireEvent.keyDown(document, { key: 'b', ctrlKey: true })
      
      expect(textarea.value).toBe('**Hello**')
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '**Hello**')
    })

    it('handles Ctrl+I for italic formatting', () => {
      const textarea = createMockTextarea('Hello', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: 'i', ctrlKey: true })
      
      expect(textarea.value).toBe('*Hello*')
      expect(mockOnFormat).toHaveBeenCalledWith('italic', '*Hello*')
    })

    it('handles Ctrl+1,2,3 for heading formatting', () => {
      const textarea = createMockTextarea('Title', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      // Test H1
      fireEvent.keyDown(document, { key: '1', ctrlKey: true })
      expect(textarea.value).toBe('# Title')
      
      // Reset
      textarea.value = 'Title'
      textarea.selectionStart = 0
      textarea.selectionEnd = 5
      
      // Test H2
      fireEvent.keyDown(document, { key: '2', ctrlKey: true })
      expect(textarea.value).toBe('## Title')
      
      // Reset
      textarea.value = 'Title'
      textarea.selectionStart = 0
      textarea.selectionEnd = 5
      
      // Test H3
      fireEvent.keyDown(document, { key: '3', ctrlKey: true })
      expect(textarea.value).toBe('### Title')
    })

    it('handles Ctrl+K for link formatting', () => {
      const textarea = createMockTextarea('link text', 0, 9)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: 'k', ctrlKey: true })
      
      expect(textarea.value).toBe('[link text](url)')
      expect(mockOnFormat).toHaveBeenCalledWith('link', '[link text](url)')
    })

    it('handles Ctrl+` for code formatting', () => {
      const textarea = createMockTextarea('code', 0, 4)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: '`', ctrlKey: true })
      
      expect(textarea.value).toBe('`code`')
      expect(mockOnFormat).toHaveBeenCalledWith('code', '`code`')
    })

    it('handles Ctrl+U for unordered list', () => {
      const textarea = createMockTextarea('item', 0, 4)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: 'u', ctrlKey: true })
      
      expect(textarea.value).toBe('- item')
      expect(mockOnFormat).toHaveBeenCalledWith('unordered-list', '- item')
    })

    it('handles Ctrl+O for ordered list', () => {
      const textarea = createMockTextarea('item', 0, 4)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: 'o', ctrlKey: true })
      
      expect(textarea.value).toBe('1. item')
      expect(mockOnFormat).toHaveBeenCalledWith('ordered-list', '1. item')
    })

    it('handles Ctrl+Q for quote formatting', () => {
      const textarea = createMockTextarea('quote', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      fireEvent.keyDown(document, { key: 'q', ctrlKey: true })
      
      expect(textarea.value).toBe('> quote')
      expect(mockOnFormat).toHaveBeenCalledWith('quote', '> quote')
    })

    it('supports Cmd key on Mac (metaKey)', () => {
      const textarea = createMockTextarea('Hello', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      // Simulate Cmd+B on Mac
      fireEvent.keyDown(document, { key: 'b', metaKey: true })
      
      expect(textarea.value).toBe('**Hello**')
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '**Hello**')
    })

    it('prevents default behavior for handled shortcuts', () => {
      const textarea = createMockTextarea('test', 0, 4)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const event = new KeyboardEvent('keydown', { key: 'b', ctrlKey: true })
      const preventDefaultSpy = jest.spyOn(event, 'preventDefault')
      
      fireEvent(document, event)
      
      expect(preventDefaultSpy).toHaveBeenCalled()
    })

    it('ignores shortcuts when disabled', () => {
      const textarea = createMockTextarea('Hello', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} disabled={true} />)
      
      fireEvent.keyDown(document, { key: 'b', ctrlKey: true })
      
      // Should not format when disabled
      expect(textarea.value).toBe('Hello')
      expect(mockOnFormat).not.toHaveBeenCalled()
    })

    it('ignores non-shortcut key combinations', () => {
      const textarea = createMockTextarea('Hello', 0, 5)
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      // Test key without Ctrl/Cmd
      fireEvent.keyDown(document, { key: 'b' })
      expect(textarea.value).toBe('Hello')
      
      // Test Ctrl with unhandled key
      fireEvent.keyDown(document, { key: 'x', ctrlKey: true })
      expect(textarea.value).toBe('Hello')
      
      expect(mockOnFormat).not.toHaveBeenCalled()
    })
  })

  describe('Edge cases', () => {
    it('handles case when no textarea is focused', async () => {
      const user = userEvent.setup()
      
      // No active element
      Object.defineProperty(document, 'activeElement', {
        value: null,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
      await user.click(boldButton)
      
      // Should still call onFormat with empty text
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '')
    })

    it('handles case when active element is not a textarea', async () => {
      const user = userEvent.setup()
      
      // Active element is a div, not textarea
      const div = document.createElement('div')
      Object.defineProperty(document, 'activeElement', {
        value: div,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
      await user.click(boldButton)
      
      // Should still call onFormat with empty text
      expect(mockOnFormat).toHaveBeenCalledWith('bold', '')
    })

    it('handles cursor positioning correctly', async () => {
      const user = userEvent.setup()
      const textarea = createMockTextarea('Hello world', 6, 6) // Cursor after "Hello "
      
      Object.defineProperty(document, 'activeElement', {
        value: textarea,
        writable: true
      })
      
      render(<MarkdownToolbar onFormat={mockOnFormat} />)
      
      const boldButton = screen.getByTitle(/加粗.*Ctrl\+B/)
      await user.click(boldButton)
      
      expect(textarea.value).toBe('Hello **加粗文本**world')
      
      // Check cursor positioning (should be after the inserted text)
      await waitFor(() => {
        expect(textarea.selectionStart).toBe(12) // After "Hello **加粗文本**" (actual position)
        expect(textarea.selectionEnd).toBe(12)
      })
    })
  })

  describe('Format type coverage', () => {
    const formatTests: Array<{
      type: FormatType
      input: string
      expected: string
      selection: [number, number]
      titlePattern: string
    }> = [
      { type: 'bold', input: 'text', expected: '**text**', selection: [0, 4], titlePattern: '加粗 (Ctrl+B)' },
      { type: 'italic', input: 'text', expected: '*text*', selection: [0, 4], titlePattern: '斜体 (Ctrl+I)' },
      { type: 'heading1', input: 'title', expected: '# title', selection: [0, 5], titlePattern: '一级标题 (Ctrl+1)' },
      { type: 'heading2', input: 'title', expected: '## title', selection: [0, 5], titlePattern: '二级标题 (Ctrl+2)' },
      { type: 'heading3', input: 'title', expected: '### title', selection: [0, 5], titlePattern: '三级标题 (Ctrl+3)' },
      { type: 'unordered-list', input: 'item', expected: '- item', selection: [0, 4], titlePattern: '无序列表 (Ctrl+U)' },
      { type: 'ordered-list', input: 'item', expected: '1. item', selection: [0, 4], titlePattern: '有序列表 (Ctrl+O)' },
      { type: 'link', input: 'link', expected: '[link](url)', selection: [0, 4], titlePattern: '链接 (Ctrl+K)' },
      { type: 'code', input: 'code', expected: '`code`', selection: [0, 4], titlePattern: '代码 (Ctrl+`)' },
      { type: 'quote', input: 'quote', expected: '> quote', selection: [0, 5], titlePattern: '引用 (Ctrl+Q)' }
    ]

    formatTests.forEach(({ type, input, expected, selection, titlePattern }) => {
      it(`formats ${type} correctly`, async () => {
        const user = userEvent.setup()
        const textarea = createMockTextarea(input, selection[0], selection[1])
        
        Object.defineProperty(document, 'activeElement', {
          value: textarea,
          writable: true
        })
        
        render(<MarkdownToolbar onFormat={mockOnFormat} />)
        
        const button = screen.getByTitle(titlePattern)
        await user.click(button)
        
        expect(textarea.value).toBe(expected)
        expect(mockOnFormat).toHaveBeenCalledWith(type, expected)
      })
    })
  })
})