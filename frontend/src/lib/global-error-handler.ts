import { errorHandler } from './error-handler'

interface GlobalErrorConfig {
  enableConsoleCapture: boolean
  enableUnhandledRejectionCapture: boolean
  enableResourceErrorCapture: boolean
  reportingEndpoint?: string
  maxErrorsPerSession: number
  enableUserFeedback: boolean
}

class GlobalErrorHandler {
  private config: GlobalErrorConfig
  private errorCount = 0
  private sessionId: string
  private isInitialized = false

  constructor(config: Partial<GlobalErrorConfig> = {}) {
    this.config = {
      enableConsoleCapture: true,
      enableUnhandledRejectionCapture: true,
      enableResourceErrorCapture: true,
      maxErrorsPerSession: 50,
      enableUserFeedback: true,
      ...config
    }
    
    this.sessionId = this.generateSessionId()
  }

  /**
   * Initialize global error handling
   */
  initialize() {
    if (this.isInitialized) {
      console.warn('Global error handler already initialized')
      return
    }

    this.setupWindowErrorHandler()
    this.setupUnhandledRejectionHandler()
    this.setupResourceErrorHandler()
    this.setupConsoleErrorCapture()
    
    this.isInitialized = true
    console.log('Global error handler initialized')
  }

  /**
   * Cleanup global error handlers
   */
  cleanup() {
    if (!this.isInitialized) return

    window.removeEventListener('error', this.handleWindowError)
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection)
    
    this.isInitialized = false
    console.log('Global error handler cleaned up')
  }

  private setupWindowErrorHandler() {
    window.addEventListener('error', this.handleWindowError)
  }

  private setupUnhandledRejectionHandler() {
    if (this.config.enableUnhandledRejectionCapture) {
      window.addEventListener('unhandledrejection', this.handleUnhandledRejection)
    }
  }

  private setupResourceErrorHandler() {
    if (this.config.enableResourceErrorCapture) {
      window.addEventListener('error', this.handleResourceError, true)
    }
  }

  private setupConsoleErrorCapture() {
    if (!this.config.enableConsoleCapture) return

    const originalConsoleError = console.error
    console.error = (...args: any[]) => {
      // Call original console.error
      originalConsoleError.apply(console, args)
      
      // Capture console errors
      const errorMessage = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
      ).join(' ')
      
      this.handleConsoleError(errorMessage, args)
    }
  }

  private handleWindowError = (event: ErrorEvent) => {
    if (this.shouldIgnoreError(event.error)) return

    const error = new Error(event.message)
    error.stack = `${event.filename}:${event.lineno}:${event.colno}\n${event.error?.stack || ''}`

    this.processAndReportError(error, {
      type: 'window_error',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      source: 'window'
    })
  }

  private handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    const error = event.reason instanceof Error 
      ? event.reason 
      : new Error(String(event.reason))

    this.processAndReportError(error, {
      type: 'unhandled_rejection',
      source: 'promise'
    })

    // Prevent the default browser behavior (logging to console)
    event.preventDefault()
  }

  private handleResourceError = (event: Event) => {
    const target = event.target as HTMLElement
    
    if (target && (target.tagName === 'IMG' || target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
      const error = new Error(`Failed to load resource: ${(target as any).src || (target as any).href}`)
      
      this.processAndReportError(error, {
        type: 'resource_error',
        tagName: target.tagName,
        src: (target as any).src || (target as any).href,
        source: 'resource'
      })
    }
  }

  private handleConsoleError(message: string, args: any[]) {
    // Only capture actual errors, not warnings or logs
    if (!this.isActualError(args)) return

    const error = new Error(message)
    
    this.processAndReportError(error, {
      type: 'console_error',
      args: args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : String(arg)),
      source: 'console'
    })
  }

  private processAndReportError(error: Error, metadata: Record<string, any>) {
    // Check error count limit
    if (this.errorCount >= this.config.maxErrorsPerSession) {
      console.warn('Maximum errors per session reached, ignoring further errors')
      return
    }

    this.errorCount++

    // Add global context
    const context = {
      sessionId: this.sessionId,
      errorCount: this.errorCount,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      referrer: document.referrer,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      ...metadata
    }

    // Process error through main error handler
    const processedError = errorHandler.processError(error, context)
    
    // Display error to user (but don't show toast for all global errors)
    errorHandler.displayError(processedError, {
      showToast: this.shouldShowToastForError(metadata),
      autoHide: true
    })

    // Report to external service if configured
    this.reportToExternalService(processedError, context)
  }

  private shouldIgnoreError(error: any): boolean {
    if (!error) return true

    const ignoredMessages = [
      'Script error.',
      'Non-Error promise rejection captured',
      'ResizeObserver loop limit exceeded',
      'Network request failed', // Common in development
      'Loading chunk', // Webpack chunk loading errors
      'ChunkLoadError'
    ]

    const message = error.message || String(error)
    return ignoredMessages.some(ignored => message.includes(ignored))
  }

  private isActualError(args: any[]): boolean {
    // Check if any argument is an Error object or error-like
    return args.some(arg => 
      arg instanceof Error ||
      (typeof arg === 'object' && arg?.stack) ||
      (typeof arg === 'string' && (
        arg.includes('Error:') ||
        arg.includes('Exception:') ||
        arg.includes('Failed to')
      ))
    )
  }

  private shouldShowToastForError(metadata: Record<string, any>): boolean {
    // Don't show toasts for resource errors or console errors
    return !['resource_error', 'console_error'].includes(metadata.type)
  }

  private async reportToExternalService(processedError: any, context: any) {
    if (!this.config.reportingEndpoint) return

    try {
      await fetch(this.config.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          error: processedError,
          context,
          timestamp: new Date().toISOString()
        })
      })
    } catch (err) {
      console.error('Failed to report error to external service:', err)
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Get error statistics for the current session
   */
  getErrorStats() {
    return {
      sessionId: this.sessionId,
      errorCount: this.errorCount,
      maxErrors: this.config.maxErrorsPerSession,
      isInitialized: this.isInitialized
    }
  }

  /**
   * Reset error count (useful for testing or after user action)
   */
  resetErrorCount() {
    this.errorCount = 0
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<GlobalErrorConfig>) {
    this.config = { ...this.config, ...newConfig }
  }
}

// Create singleton instance
export const globalErrorHandler = new GlobalErrorHandler()

// Auto-initialize in browser environment
if (typeof window !== 'undefined') {
  // Initialize after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      globalErrorHandler.initialize()
    })
  } else {
    globalErrorHandler.initialize()
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    globalErrorHandler.cleanup()
  })
}

export default globalErrorHandler