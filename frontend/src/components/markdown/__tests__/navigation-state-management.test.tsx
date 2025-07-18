import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useRouter } from 'next/navigation'
import { MarkdownEditorContainer } from '../markdown-editor-container'
import type { Task } from '@/types'

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useParams: jest.fn(() => ({ taskId: 'test-task-123' }))
}))

jest.mock('@/lib/json-to-markdown', () => ({
  JsonToMarkdownConverter: {
    convert: jest.fn(() => ({
      markdown: '# Test Content\n\nThis is test content.',
      isTruncated: false,
      originalSize: 100,
      truncatedSize: 100,
      warnings: []
    }))
  }
}))

jest.mock('@/lib/export-manager', () => ({
  ExportManager: {
    copyToClipboard: jest.fn(),
    exportMarkdown: jest.fn(),
    exportHtml: jest.fn(),
    generateFilename: jest.fn(() => 'test-file.md'),
    isClipboardSupported: jest.fn(() => true)
  }
}))

jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}))

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

// Mock window.confirm
Object.defineProperty(window, 'confirm', {
  value: jest.fn(() => true)
})

// Mock beforeunload event
const addEventListenerSpy = jest.spyOn(window, 'addEventListener')
const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener')

const mockTask: Task = {
  id: 'test-task-123',
  task_type: 'document_parsing',
  status: 'completed',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T01:00:00Z',
  completed_at: '2024-01-01T01:00:00Z',
  results: {
    title: 'Test Document',
    content: 'This is test content'
  },
  actual_cost: 0.05
}

describe('Navigation and State Management', () => {
  const mockPush = jest.fn()
  const mockOnBack = jest.fn()
  const mockOnUnsavedChanges = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useRouter as jest.Mock).mockReturnValue({
      push: mockPush
    })
    localStorageMock.getItem.mockReturnValue(null)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('Back Navigation', () => {
    it('should call onBack when back button is clicked without unsaved changes', () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      const backButton = screen.getByText('返回结果')
      fireEvent.click(backButton)

      expect(mockOnBack).toHaveBeenCalled()
    })

    it('should show confirmation dialog when back button is clicked with unsaved changes', async () => {
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false)
      
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      // Wait for component to initialize
      await waitFor(() => {
        expect(screen.getByText('返回结果')).toBeInTheDocument()
      })

      // Simulate making changes to trigger unsaved state
      const editor = screen.getByRole('textbox')
      fireEvent.change(editor, { target: { value: 'Modified content' } })

      // Wait for unsaved changes to be tracked
      await waitFor(() => {
        expect(mockOnUnsavedChanges).toHaveBeenCalledWith(true)
      })

      const backButton = screen.getByText('返回结果')
      fireEvent.click(backButton)

      expect(confirmSpy).toHaveBeenCalledWith(
        expect.stringContaining('您有未保存的更改，确定要离开吗？')
      )
      expect(mockOnBack).not.toHaveBeenCalled()

      confirmSpy.mockRestore()
    })

    it('should proceed with navigation when user confirms leaving with unsaved changes', async () => {
      const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true)
      
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      // Wait for component to initialize
      await waitFor(() => {
        expect(screen.getByText('返回结果')).toBeInTheDocument()
      })

      // Simulate making changes
      const editor = screen.getByRole('textbox')
      fireEvent.change(editor, { target: { value: 'Modified content' } })

      await waitFor(() => {
        expect(mockOnUnsavedChanges).toHaveBeenCalledWith(true)
      })

      const backButton = screen.getByText('返回结果')
      fireEvent.click(backButton)

      expect(confirmSpy).toHaveBeenCalled()
      expect(mockOnBack).toHaveBeenCalled()

      confirmSpy.mockRestore()
    })
  })

  describe('Unsaved Changes Tracking', () => {
    it('should track unsaved changes when content is modified', async () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('返回结果')).toBeInTheDocument()
      })

      // Initially no unsaved changes
      expect(mockOnUnsavedChanges).toHaveBeenCalledWith(false)

      // Modify content
      const editor = screen.getByRole('textbox')
      fireEvent.change(editor, { target: { value: 'Modified content' } })

      // Should track unsaved changes
      await waitFor(() => {
        expect(mockOnUnsavedChanges).toHaveBeenCalledWith(true)
      })
    })

    it('should clear unsaved changes after manual save', async () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('保存')).toBeInTheDocument()
      })

      // Modify content
      const editor = screen.getByRole('textbox')
      fireEvent.change(editor, { target: { value: 'Modified content' } })

      await waitFor(() => {
        expect(mockOnUnsavedChanges).toHaveBeenCalledWith(true)
      })

      // Save manually
      const saveButton = screen.getByText('保存')
      fireEvent.click(saveButton)

      // Should clear unsaved changes
      await waitFor(() => {
        expect(mockOnUnsavedChanges).toHaveBeenCalledWith(false)
      })
    })
  })

  describe('Page Unload Warning', () => {
    it('should add beforeunload event listener on mount', () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      expect(addEventListenerSpy).toHaveBeenCalledWith(
        'beforeunload',
        expect.any(Function)
      )
    })

    it('should remove beforeunload event listener on unmount', () => {
      const { unmount } = render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      unmount()

      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'beforeunload',
        expect.any(Function)
      )
    })
  })

  describe('Auto-save Functionality', () => {
    beforeEach(() => {
      jest.useFakeTimers()
    })

    afterEach(() => {
      jest.useRealTimers()
    })

    it('should auto-save content after delay', async () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('返回结果')).toBeInTheDocument()
      })

      // Modify content
      const editor = screen.getByRole('textbox')
      fireEvent.change(editor, { target: { value: 'Auto-save test content' } })

      // Fast-forward time to trigger auto-save
      jest.advanceTimersByTime(3000)

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          `markdown-editor-${mockTask.id}`,
          expect.stringContaining('Auto-save test content')
        )
      })
    })

    it('should debounce auto-save when content changes rapidly', async () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('返回结果')).toBeInTheDocument()
      })

      const editor = screen.getByRole('textbox')

      // Rapid changes
      fireEvent.change(editor, { target: { value: 'Change 1' } })
      jest.advanceTimersByTime(1000)
      
      fireEvent.change(editor, { target: { value: 'Change 2' } })
      jest.advanceTimersByTime(1000)
      
      fireEvent.change(editor, { target: { value: 'Change 3' } })
      jest.advanceTimersByTime(3000)

      // Should only save once after the last change
      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledTimes(1)
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          `markdown-editor-${mockTask.id}`,
          expect.stringContaining('Change 3')
        )
      })
    })
  })

  describe('Connection Status Monitoring', () => {
    it('should handle online/offline events', async () => {
      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      // Simulate going offline
      fireEvent(window, new Event('offline'))

      await waitFor(() => {
        expect(screen.getByText('离线')).toBeInTheDocument()
      })

      // Simulate going online
      fireEvent(window, new Event('online'))

      await waitFor(() => {
        expect(screen.queryByText('离线')).not.toBeInTheDocument()
      })
    })
  })

  describe('Local Storage Recovery', () => {
    it('should load saved content from localStorage on initialization', async () => {
      const savedContent = 'Previously saved content'
      const savedData = {
        taskId: mockTask.id,
        content: savedContent,
        timestamp: Date.now(),
        version: '1.0'
      }
      
      localStorageMock.getItem.mockReturnValue(JSON.stringify(savedData))

      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        const editor = screen.getByRole('textbox')
        expect(editor).toHaveValue(savedContent)
      })

      // Should indicate unsaved changes
      expect(mockOnUnsavedChanges).toHaveBeenCalledWith(true)
    })

    it('should ignore old localStorage data', async () => {
      const oldTimestamp = Date.now() - (25 * 60 * 60 * 1000) // 25 hours ago
      const oldData = {
        taskId: mockTask.id,
        content: 'Old content',
        timestamp: oldTimestamp,
        version: '1.0'
      }
      
      localStorageMock.getItem.mockReturnValue(JSON.stringify(oldData))

      render(
        <MarkdownEditorContainer
          task={mockTask}
          onBack={mockOnBack}
          onUnsavedChanges={mockOnUnsavedChanges}
        />
      )

      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith(
          `markdown-editor-${mockTask.id}`
        )
      })

      // Should not load old content
      await waitFor(() => {
        const editor = screen.getByRole('textbox')
        expect(editor).not.toHaveValue('Old content')
      })
    })
  })
})