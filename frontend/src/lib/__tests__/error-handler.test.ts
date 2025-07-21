import { describe, it, expect, beforeEach, jest } from '@jest/globals'
import { errorHandler, ErrorType, ErrorSeverity, handleError, withErrorHandling } from '../error-handler'
import { ApiError } from '../api'
import { afterEach } from 'node:test'

// Mock the toast function
const mockToast = jest.fn()
jest.mock('@/components/ui/use-toast', () => ({
  toast: mockToast
}))

// Mock fetch for error reporting
global.fetch = jest.fn()

describe('Error Handler', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Reset error counts
    ;(errorHandler as any).errorCounts.clear()
  })

  describe('processError', () => {
    it('should process ApiError correctly', () => {
      const apiError = new ApiError(
        'VALIDATION_ERROR',
        'Invalid input provided',
        { field: 'email' },
        'req_123'
      )

      const processed = errorHandler.processError(apiError, {
        component: 'LoginForm',
        action: 'submit'
      })

      expect(processed.type).toBe(ErrorType.VALIDATION)
      expect(processed.severity).toBe(ErrorSeverity.LOW)
      expect(processed.title).toBe('Invalid Input')
      expect(processed.message).toBe('Please check your input and try again.')
      expect(processed.suggestions).toContain('Verify all required fields are filled')
      expect(processed.recoveryActions).toHaveLength(1)
      expect(processed.canRetry).toBe(false)
      expect(processed.shouldReport).toBe(false)
    })

    it('should process file too large error', () => {
      const apiError = new ApiError(
        'FILE_TOO_LARGE',
        'File exceeds maximum size',
        { maxSize: '10MB', actualSize: '15MB' }
      )

      const processed = errorHandler.processError(apiError)

      expect(processed.type).toBe(ErrorType.VALIDATION)
      expect(processed.severity).toBe(ErrorSeverity.MEDIUM)
      expect(processed.title).toBe('File Too Large')
      expect(processed.suggestions).toContain('Choose a smaller file')
    })

    it('should process cost limit exceeded error', () => {
      const apiError = new ApiError(
        'COST_LIMIT_EXCEEDED',
        'Processing cost exceeds limit',
        { estimatedCost: 15.50, limit: 10.00 }
      )

      const processed = errorHandler.processError(apiError)

      expect(processed.type).toBe(ErrorType.VALIDATION)
      expect(processed.severity).toBe(ErrorSeverity.HIGH)
      expect(processed.title).toBe('Cost Limit Exceeded')
      expect(processed.suggestions).toContain('Reduce the number of files')
    })

    it('should process network error', () => {
      const apiError = new ApiError(
        'NETWORK_ERROR',
        'Connection failed',
        { timeout: true }
      )

      const processed = errorHandler.processError(apiError)

      expect(processed.type).toBe(ErrorType.NETWORK)
      expect(processed.severity).toBe(ErrorSeverity.HIGH)
      expect(processed.title).toBe('Connection Problem')
      expect(processed.canRetry).toBe(true)
      expect(processed.shouldReport).toBe(true)
    })

    it('should process server error', () => {
      const apiError = new ApiError(
        'INTERNAL_SERVER_ERROR',
        'Internal server error',
        { code: 500 }
      )

      const processed = errorHandler.processError(apiError)

      expect(processed.type).toBe(ErrorType.SERVER)
      expect(processed.severity).toBe(ErrorSeverity.CRITICAL)
      expect(processed.title).toBe('Server Error')
      expect(processed.canRetry).toBe(true)
      expect(processed.shouldReport).toBe(true)
    })

    it('should process generic Error', () => {
      const error = new Error('Something went wrong')

      const processed = errorHandler.processError(error, {
        component: 'TaskList'
      })

      expect(processed.type).toBe(ErrorType.CLIENT)
      expect(processed.severity).toBe(ErrorSeverity.MEDIUM)
      expect(processed.title).toBe('Application Error')
      expect(processed.technicalMessage).toBe('Something went wrong')
      expect(processed.context?.component).toBe('TaskList')
    })

    it('should process unknown error', () => {
      const error = 'Unknown error string'

      const processed = errorHandler.processError(error)

      expect(processed.type).toBe(ErrorType.UNKNOWN)
      expect(processed.severity).toBe(ErrorSeverity.MEDIUM)
      expect(processed.title).toBe('Unknown Error')
      expect(processed.technicalMessage).toBe('Unknown error string')
      expect(processed.canRetry).toBe(false)
    })
  })

  describe('displayError', () => {
    it('should display error with toast', () => {
      const processedError = {
        id: 'err_123',
        type: ErrorType.VALIDATION,
        severity: ErrorSeverity.LOW,
        title: 'Test Error',
        message: 'Test message',
        suggestions: ['Test suggestion'],
        recoveryActions: [],
        timestamp: new Date(),
        canRetry: false,
        shouldReport: false
      }

      errorHandler.displayError(processedError)

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Test Error',
        description: 'Test message',
        variant: 'default',
        duration: 5000,
        action: undefined
      })
    })

    it('should use destructive variant for high severity errors', () => {
      const processedError = {
        id: 'err_123',
        type: ErrorType.SERVER,
        severity: ErrorSeverity.CRITICAL,
        title: 'Critical Error',
        message: 'Critical message',
        suggestions: [],
        recoveryActions: [],
        timestamp: new Date(),
        canRetry: false,
        shouldReport: true
      }

      errorHandler.displayError(processedError)

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Critical Error',
        description: 'Critical message',
        variant: 'destructive',
        duration: 0, // Don't auto-hide critical errors
        action: undefined
      })
    })

    it('should include recovery action in toast', () => {
      const mockAction = jest.fn()
      
      const processedError = {
        id: 'err_123',
        type: ErrorType.NETWORK,
        severity: ErrorSeverity.MEDIUM,
        title: 'Network Error',
        message: 'Connection failed',
        suggestions: [],
        recoveryActions: [{
          label: 'Retry',
          action: mockAction,
          type: 'primary' as const
        }],
        timestamp: new Date(),
        canRetry: true,
        shouldReport: true
      }

      errorHandler.displayError(processedError)

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Network Error',
        description: 'Connection failed',
        variant: 'default',
        duration: 7000,
        action: {
          altText: 'Retry',
          onClick: mockAction
        }
      })
    })
  })

  describe('handleError', () => {
    it('should process and display error', () => {
      const error = new ApiError('VALIDATION_ERROR', 'Invalid input')
      const context = { component: 'TestComponent' }

      const processed = errorHandler.handleError(error, context)

      expect(processed.type).toBe(ErrorType.VALIDATION)
      expect(processed.context).toBe(context)
      expect(mockToast).toHaveBeenCalled()
    })
  })

  describe('withRetry', () => {
    it('should succeed on first attempt', async () => {
      const operation = jest.fn().mockResolvedValue('success')

      const result = await errorHandler.withRetry(operation)

      expect(result).toBe('success')
      expect(operation).toHaveBeenCalledTimes(1)
    })

    it('should retry on retryable errors', async () => {
      const operation = jest.fn()
        .mockRejectedValueOnce(new ApiError('NETWORK_ERROR', 'Connection failed'))
        .mockRejectedValueOnce(new ApiError('NETWORK_ERROR', 'Connection failed'))
        .mockResolvedValue('success')

      const result = await errorHandler.withRetry(operation, undefined, 3)

      expect(result).toBe('success')
      expect(operation).toHaveBeenCalledTimes(3)
    })

    it('should not retry on non-retryable errors', async () => {
      const operation = jest.fn()
        .mockRejectedValue(new ApiError('VALIDATION_ERROR', 'Invalid input'))

      await expect(errorHandler.withRetry(operation)).rejects.toThrow('Invalid input')
      expect(operation).toHaveBeenCalledTimes(1)
    })

    it('should throw after max retries', async () => {
      const operation = jest.fn()
        .mockRejectedValue(new ApiError('NETWORK_ERROR', 'Connection failed'))

      await expect(errorHandler.withRetry(operation, undefined, 2)).rejects.toThrow('Connection failed')
      expect(operation).toHaveBeenCalledTimes(3) // Initial + 2 retries
    })
  })

  describe('convenience functions', () => {
    it('should handle error with handleError function', () => {
      const error = new Error('Test error')
      handleError(error, { component: 'TestComponent' })

      expect(mockToast).toHaveBeenCalled()
    })

    it('should wrap function with error handling', () => {
      const originalFn = jest.fn().mockImplementation(() => {
        throw new Error('Test error')
      })

      const wrappedFn = withErrorHandling(originalFn, { component: 'TestComponent' })

      expect(() => wrappedFn()).toThrow('Test error')
      expect(mockToast).toHaveBeenCalled()
    })

    it('should wrap async function with error handling', async () => {
      const originalFn = jest.fn().mockRejectedValue(new Error('Async error'))
      const wrappedFn = withErrorHandling(originalFn, { component: 'TestComponent' })

      await expect(wrappedFn()).rejects.toThrow('Async error')
      expect(mockToast).toHaveBeenCalled()
    })
  })

  describe('error reporting', () => {
    beforeEach(() => {
      // Mock production environment
      process.env.NODE_ENV = 'production'
    })

    afterEach(() => {
      process.env.NODE_ENV = 'test'
    })

    it('should report errors in production', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200
      } as Response)

      const error = new ApiError('INTERNAL_SERVER_ERROR', 'Server error')
      const processed = errorHandler.processError(error)

      errorHandler.displayError(processed)

      // Wait for async reporting
      await new Promise(resolve => setTimeout(resolve, 0))

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.stringContaining('INTERNAL_SERVER_ERROR')
      })
    })

    it('should not report validation errors', () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      
      const error = new ApiError('VALIDATION_ERROR', 'Invalid input')
      const processed = errorHandler.processError(error)

      errorHandler.displayError(processed)

      expect(mockFetch).not.toHaveBeenCalled()
    })
  })
})