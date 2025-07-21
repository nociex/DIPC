/**
 * Simple tests for ExportManager functionality
 */
import { ExportManager } from '../export-manager'

describe('ExportManager Basic Tests', () => {
  describe('generateFilename', () => {
    it('should generate markdown filename with task ID and timestamp', () => {
      const taskId = '12345678-abcd-efgh'
      const filename = ExportManager.generateFilename(taskId, 'markdown')
      
      expect(filename).toMatch(/^task-12345678-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.md$/)
    })

    it('should generate HTML filename with task ID and timestamp', () => {
      const taskId = '12345678-abcd-efgh'
      const filename = ExportManager.generateFilename(taskId, 'html')
      
      expect(filename).toMatch(/^task-12345678-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.html$/)
    })

    it('should handle short task IDs', () => {
      const taskId = '123'
      const filename = ExportManager.generateFilename(taskId, 'markdown')
      
      expect(filename).toMatch(/^task-123-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.md$/)
    })
  })

  describe('isClipboardSupported', () => {
    it('should return a boolean', () => {
      const result = ExportManager.isClipboardSupported()
      expect(typeof result).toBe('boolean')
    })
  })

  describe('isDownloadSupported', () => {
    it('should return a boolean', () => {
      const result = ExportManager.isDownloadSupported()
      expect(typeof result).toBe('boolean')
    })
  })
})