/**
 * Test ExportManager functionality for copy and export features
 */
import { ExportManager } from '../export-manager'

// Mock DOM APIs for testing
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn().mockResolvedValue(undefined),
  },
})

Object.assign(window, {
  isSecureContext: true,
})

// Mock document.createElement and related DOM methods
const mockLink = {
  href: '',
  download: '',
  style: { display: '' },
  click: jest.fn(),
}

const mockTextArea = {
  value: '',
  style: { position: '', left: '', top: '' },
  focus: jest.fn(),
  select: jest.fn(),
}

const originalCreateElement = document.createElement
const originalAppendChild = document.body.appendChild
const originalRemoveChild = document.body.removeChild
const originalExecCommand = document.execCommand

document.createElement = jest.fn((tagName: string) => {
  if (tagName === 'a') return mockLink as any
  if (tagName === 'textarea') return mockTextArea as any
  return originalCreateElement.call(document, tagName)
})

document.body.appendChild = jest.fn()
document.body.removeChild = jest.fn()
document.execCommand = jest.fn().mockReturnValue(true)

// Mock URL.createObjectURL and revokeObjectURL
Object.assign(global.URL, {
  createObjectURL: jest.fn().mockReturnValue('mock-url'),
  revokeObjectURL: jest.fn(),
})

// Mock Blob
global.Blob = jest.fn().mockImplementation((content, options) => ({
  content,
  options,
})) as any

describe('ExportManager Copy and Export Functionality', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('copyToClipboard', () => {
    it('should copy text to clipboard using modern API', async () => {
      const testContent = '# Test Markdown\n\nThis is test content'
      
      await ExportManager.copyToClipboard(testContent)
      
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(testContent)
    })

    it('should handle clipboard API errors gracefully', async () => {
      const testContent = '# Test Markdown'
      ;(navigator.clipboard.writeText as jest.Mock).mockRejectedValueOnce(new Error('Clipboard error'))
      
      await expect(ExportManager.copyToClipboard(testContent)).rejects.toThrow('复制到剪贴板失败')
    })
  })

  describe('exportMarkdown', () => {
    it('should create and download markdown file', async () => {
      const testContent = '# Test Markdown\n\nThis is test content'
      const filename = 'test-file.md'
      
      await ExportManager.exportMarkdown(testContent, filename)
      
      expect(global.Blob).toHaveBeenCalledWith([testContent], { type: 'text/markdown;charset=utf-8' })
      expect(global.URL.createObjectURL).toHaveBeenCalled()
      expect(document.createElement).toHaveBeenCalledWith('a')
      expect(mockLink.download).toBe(filename)
      expect(mockLink.click).toHaveBeenCalled()
      expect(global.URL.revokeObjectURL).toHaveBeenCalled()
    })

    it('should generate default filename if none provided', async () => {
      const testContent = '# Test Markdown'
      
      await ExportManager.exportMarkdown(testContent)
      
      expect(mockLink.download).toMatch(/^markdown-export-\d+\.md$/)
    })
  })

  describe('exportHtml', () => {
    it('should convert markdown to HTML and download', async () => {
      const testContent = '# Test Heading\n\n**Bold text**'
      const filename = 'test-file.html'
      
      await ExportManager.exportHtml(testContent, filename)
      
      expect(global.Blob).toHaveBeenCalledWith(
        expect.arrayContaining([expect.stringContaining('<!DOCTYPE html>')]),
        { type: 'text/html;charset=utf-8' }
      )
      expect(mockLink.download).toBe(filename)
      expect(mockLink.click).toHaveBeenCalled()
    })

    it('should convert basic markdown syntax to HTML', async () => {
      const testContent = '# Heading\n\n**Bold** and *italic*\n\n- List item'
      
      await ExportManager.exportHtml(testContent)
      
      const blobCall = (global.Blob as jest.Mock).mock.calls[0]
      const htmlContent = blobCall[0][0]
      
      expect(htmlContent).toContain('<h1>Heading</h1>')
      expect(htmlContent).toContain('<strong>Bold</strong>')
      expect(htmlContent).toContain('<em>italic</em>')
      expect(htmlContent).toContain('<li>List item</li>')
    })
  })

  describe('generateFilename', () => {
    it('should generate filename with task ID and timestamp for markdown', () => {
      const taskId = 'test-task-12345678'
      const filename = ExportManager.generateFilename(taskId, 'markdown')
      
      expect(filename).toMatch(/^task-test-tas-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.md$/)
    })

    it('should generate filename with task ID and timestamp for HTML', () => {
      const taskId = 'test-task-12345678'
      const filename = ExportManager.generateFilename(taskId, 'html')
      
      expect(filename).toMatch(/^task-test-tas-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.html$/)
    })

    it('should handle short task IDs', () => {
      const taskId = 'short'
      const filename = ExportManager.generateFilename(taskId, 'markdown')
      
      expect(filename).toMatch(/^task-short-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.md$/)
    })
  })

  describe('feature detection', () => {
    it('should detect clipboard support', () => {
      const isSupported = ExportManager.isClipboardSupported()
      expect(typeof isSupported).toBe('boolean')
    })

    it('should detect download support', () => {
      const isSupported = ExportManager.isDownloadSupported()
      expect(typeof isSupported).toBe('boolean')
    })
  })
})