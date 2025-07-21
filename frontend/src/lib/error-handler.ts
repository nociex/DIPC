import React from 'react'
import { ApiError } from './api'
import { toast } from '@/components/ui/use-toast'

// Error types for better categorization
export enum ErrorType {
  NETWORK = 'network',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  NOT_FOUND = 'not_found',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown'
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface ErrorContext {
  component?: string
  action?: string
  userId?: string
  sessionId?: string
  metadata?: Record<string, any>
}

export interface ProcessedError {
  id: string
  type: ErrorType
  severity: ErrorSeverity
  title: string
  message: string
  technicalMessage?: string
  suggestions: string[]
  recoveryActions: RecoveryAction[]
  context?: ErrorContext
  timestamp: Date
  canRetry: boolean
  shouldReport: boolean
}

export interface RecoveryAction {
  label: string
  action: () => void | Promise<void>
  type: 'primary' | 'secondary' | 'destructive'
  icon?: string
}

class ErrorHandler {
  private errorCounts = new Map<string, number>()
  private maxRetries = 3
  private reportingEnabled = process.env.NODE_ENV === 'production'

  /**
   * Process and categorize errors for user-friendly display
   */
  processError(error: unknown, context?: ErrorContext): ProcessedError {
    const errorId = this.generateErrorId()
    const timestamp = new Date()

    // Handle different error types
    if (error instanceof ApiError) {
      return this.processApiError(error, errorId, timestamp, context)
    }

    if (error instanceof Error) {
      return this.processGenericError(error, errorId, timestamp, context)
    }

    // Handle unknown error types
    return this.processUnknownError(error, errorId, timestamp, context)
  }

  private processApiError(
    error: ApiError, 
    errorId: string, 
    timestamp: Date, 
    context?: ErrorContext
  ): ProcessedError {
    const errorKey = `${error.errorCode}_${context?.component || 'unknown'}`
    const retryCount = this.errorCounts.get(errorKey) || 0
    
    const baseError: Partial<ProcessedError> = {
      id: errorId,
      timestamp,
      context,
      canRetry: retryCount < this.maxRetries && this.isRetryableError(error),
      shouldReport: this.shouldReportError(error),
      technicalMessage: error.errorMessage
    }

    switch (error.errorCode) {
      case 'VALIDATION_ERROR':
        return {
          ...baseError,
          type: ErrorType.VALIDATION,
          severity: ErrorSeverity.LOW,
          title: 'Invalid Input',
          message: 'Please check your input and try again.',
          suggestions: [
            'Verify all required fields are filled',
            'Check file formats and sizes',
            'Ensure data meets the specified requirements'
          ],
          recoveryActions: this.getValidationRecoveryActions(context)
        } as ProcessedError

      case 'FILE_TOO_LARGE':
        return {
          ...baseError,
          type: ErrorType.VALIDATION,
          severity: ErrorSeverity.MEDIUM,
          title: 'File Too Large',
          message: 'The selected file exceeds the maximum size limit.',
          suggestions: [
            'Choose a smaller file',
            'Compress the file before uploading',
            'Split large files into smaller parts'
          ],
          recoveryActions: this.getFileErrorRecoveryActions(context)
        } as ProcessedError

      case 'COST_LIMIT_EXCEEDED':
        return {
          ...baseError,
          type: ErrorType.VALIDATION,
          severity: ErrorSeverity.HIGH,
          title: 'Cost Limit Exceeded',
          message: 'The estimated processing cost exceeds your limit.',
          suggestions: [
            'Reduce the number of files',
            'Disable vectorization to lower costs',
            'Increase your cost limit in settings'
          ],
          recoveryActions: this.getCostLimitRecoveryActions(context)
        } as ProcessedError

      case 'TASK_NOT_FOUND':
        return {
          ...baseError,
          type: ErrorType.NOT_FOUND,
          severity: ErrorSeverity.MEDIUM,
          title: 'Task Not Found',
          message: 'The requested task could not be found.',
          suggestions: [
            'Check if the task ID is correct',
            'The task may have been deleted',
            'Try refreshing the page'
          ],
          recoveryActions: this.getNotFoundRecoveryActions(context)
        } as ProcessedError

      case 'NETWORK_ERROR':
        return {
          ...baseError,
          type: ErrorType.NETWORK,
          severity: ErrorSeverity.HIGH,
          title: 'Connection Problem',
          message: 'Unable to connect to the server. Please check your internet connection.',
          suggestions: [
            'Check your internet connection',
            'Try refreshing the page',
            'Wait a moment and try again'
          ],
          recoveryActions: this.getNetworkErrorRecoveryActions(context)
        } as ProcessedError

      case 'INTERNAL_SERVER_ERROR':
        return {
          ...baseError,
          type: ErrorType.SERVER,
          severity: ErrorSeverity.CRITICAL,
          title: 'Server Error',
          message: 'An unexpected server error occurred. Our team has been notified.',
          suggestions: [
            'Try again in a few minutes',
            'Contact support if the problem persists',
            'Check our status page for known issues'
          ],
          recoveryActions: this.getServerErrorRecoveryActions(context)
        } as ProcessedError

      default:
        return {
          ...baseError,
          type: ErrorType.UNKNOWN,
          severity: ErrorSeverity.MEDIUM,
          title: 'Unexpected Error',
          message: error.errorMessage || 'An unexpected error occurred.',
          suggestions: [
            'Try refreshing the page',
            'Clear your browser cache',
            'Contact support if the problem persists'
          ],
          recoveryActions: this.getGenericRecoveryActions(context)
        } as ProcessedError
    }
  }

  private processGenericError(
    error: Error, 
    errorId: string, 
    timestamp: Date, 
    context?: ErrorContext
  ): ProcessedError {
    return {
      id: errorId,
      type: ErrorType.CLIENT,
      severity: ErrorSeverity.MEDIUM,
      title: 'Application Error',
      message: 'An error occurred in the application.',
      technicalMessage: error.message,
      suggestions: [
        'Try refreshing the page',
        'Clear your browser cache',
        'Update your browser to the latest version'
      ],
      recoveryActions: this.getGenericRecoveryActions(context),
      context,
      timestamp,
      canRetry: true,
      shouldReport: true
    }
  }

  private processUnknownError(
    error: unknown, 
    errorId: string, 
    timestamp: Date, 
    context?: ErrorContext
  ): ProcessedError {
    return {
      id: errorId,
      type: ErrorType.UNKNOWN,
      severity: ErrorSeverity.MEDIUM,
      title: 'Unknown Error',
      message: 'An unknown error occurred.',
      technicalMessage: String(error),
      suggestions: [
        'Try refreshing the page',
        'Contact support with the error ID'
      ],
      recoveryActions: this.getGenericRecoveryActions(context),
      context,
      timestamp,
      canRetry: false,
      shouldReport: true
    }
  }

  /**
   * Display error to user with appropriate UI
   */
  displayError(processedError: ProcessedError, options?: {
    showToast?: boolean
    showModal?: boolean
    autoHide?: boolean
  }) {
    const { showToast = true, autoHide = true } = options || {}

    if (showToast) {
      toast({
        title: processedError.title,
        description: processedError.message,
        variant: this.getToastVariant(processedError.severity),
        duration: autoHide ? this.getToastDuration(processedError.severity) : undefined,
        // Note: Recovery actions disabled for now due to ToastAction component requirements
      })
    }

    // Log error for debugging
    this.logError(processedError)

    // Report error if needed
    if (processedError.shouldReport) {
      this.reportError(processedError)
    }
  }

  /**
   * Handle errors with automatic processing and display
   */
  handleError(error: unknown, context?: ErrorContext, options?: {
    showToast?: boolean
    showModal?: boolean
    autoHide?: boolean
  }) {
    const processedError = this.processError(error, context)
    this.displayError(processedError, options)
    return processedError
  }

  /**
   * Retry an operation with error handling
   */
  async withRetry<T>(
    operation: () => Promise<T>,
    context?: ErrorContext,
    maxRetries: number = this.maxRetries
  ): Promise<T> {
    let lastError: unknown
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation()
      } catch (error) {
        lastError = error
        
        if (attempt === maxRetries) {
          break
        }

        // Check if error is retryable
        if (error instanceof ApiError && !this.isRetryableError(error)) {
          break
        }

        // Wait before retry with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }

    // All retries failed, handle the error
    throw lastError
  }

  // Recovery action generators
  private getValidationRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Review Input',
        action: () => {
          // Focus on first invalid field or scroll to form
          const firstInvalidField = document.querySelector('[aria-invalid="true"]') as HTMLElement
          if (firstInvalidField) {
            firstInvalidField.focus()
          }
        },
        type: 'primary'
      }
    ]
  }

  private getFileErrorRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Choose Different File',
        action: () => {
          // Trigger file picker
          const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
          if (fileInput) {
            fileInput.click()
          }
        },
        type: 'primary'
      }
    ]
  }

  private getCostLimitRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Adjust Settings',
        action: () => {
          // Navigate to settings or open settings modal
          window.location.hash = '#settings'
        },
        type: 'primary'
      }
    ]
  }

  private getNotFoundRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Go Back',
        action: () => window.history.back(),
        type: 'secondary'
      },
      {
        label: 'Go Home',
        action: () => { window.location.href = '/' },
        type: 'primary'
      }
    ]
  }

  private getNetworkErrorRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Retry',
        action: () => window.location.reload(),
        type: 'primary'
      },
      {
        label: 'Check Connection',
        action: () => {
          // Open network diagnostics or show connection status
          if (navigator.onLine) {
            toast({
              title: 'Connection Status',
              description: 'You appear to be online. The issue may be with our servers.',
            })
          } else {
            toast({
              title: 'No Internet Connection',
              description: 'Please check your internet connection and try again.',
              variant: 'destructive'
            })
          }
        },
        type: 'secondary'
      }
    ]
  }

  private getServerErrorRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Try Again Later',
        action: () => {
          toast({
            title: 'We\'ll try again in a few minutes',
            description: 'The page will automatically refresh when the server is available.',
          })
          // Set up automatic retry
          setTimeout(() => window.location.reload(), 300000) // 5 minutes
        },
        type: 'primary'
      }
    ]
  }

  private getGenericRecoveryActions(context?: ErrorContext): RecoveryAction[] {
    return [
      {
        label: 'Refresh Page',
        action: () => window.location.reload(),
        type: 'primary'
      },
      {
        label: 'Go Home',
        action: () => { window.location.href = '/' },
        type: 'secondary'
      }
    ]
  }

  // Helper methods
  private generateErrorId(): string {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private isRetryableError(error: ApiError): boolean {
    const retryableCodes = [
      'NETWORK_ERROR',
      'INTERNAL_SERVER_ERROR',
      'SERVICE_UNAVAILABLE',
      'TIMEOUT'
    ]
    return retryableCodes.includes(error.errorCode)
  }

  private shouldReportError(error: ApiError): boolean {
    const nonReportableCodes = [
      'VALIDATION_ERROR',
      'AUTHENTICATION_ERROR',
      'AUTHORIZATION_ERROR'
    ]
    return !nonReportableCodes.includes(error.errorCode)
  }

  private getToastVariant(severity: ErrorSeverity): 'default' | 'destructive' {
    return severity === ErrorSeverity.CRITICAL || severity === ErrorSeverity.HIGH 
      ? 'destructive' 
      : 'default'
  }

  private getToastDuration(severity: ErrorSeverity): number {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 0 // Don't auto-hide critical errors
      case ErrorSeverity.HIGH:
        return 10000 // 10 seconds
      case ErrorSeverity.MEDIUM:
        return 7000 // 7 seconds
      case ErrorSeverity.LOW:
        return 5000 // 5 seconds
      default:
        return 5000
    }
  }

  private logError(processedError: ProcessedError) {
    if (process.env.NODE_ENV === 'development') {
      console.group(`🚨 Error Handler: ${processedError.title}`)
      console.error('Processed Error:', processedError)
      console.groupEnd()
    }
  }

  private async reportError(processedError: ProcessedError) {
    if (!this.reportingEnabled) return

    try {
      await fetch('/api/v1/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...processedError,
          userAgent: navigator.userAgent,
          url: window.location.href,
          timestamp: processedError.timestamp.toISOString()
        })
      })
    } catch (err) {
      console.error('Failed to report error:', err)
    }
  }
}

// Export singleton instance
export const errorHandler = new ErrorHandler()

// Convenience functions
export const handleError = (error: unknown, context?: ErrorContext) => 
  errorHandler.handleError(error, context)

export const withErrorHandling = <T extends (...args: any[]) => any>(
  fn: T,
  context?: ErrorContext
): T => {
  return ((...args: any[]) => {
    try {
      const result = fn(...args)
      
      // Handle async functions
      if (result instanceof Promise) {
        return result.catch((error) => {
          errorHandler.handleError(error, context)
          throw error
        })
      }
      
      return result
    } catch (error) {
      errorHandler.handleError(error, context)
      throw error
    }
  }) as T
}