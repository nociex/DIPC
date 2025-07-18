// Re-export shared types for frontend use
export type {
  Task,
  TaskStatus,
  TaskType,
  TaskOptions,
  TaskCreateRequest,
  TaskResponse,
  PresignedUrlRequest,
  PresignedUrlResponse,
  ErrorResponse,
  HealthCheckResponse,
  DocumentParsingResult,
  TokenUsage,
  DocumentMetadata,
  FileMetadata,
  StoragePolicy,
  UploadProgress,
  TaskListItem,
  SystemConfig
} from '../../../shared/types'

// Frontend-specific types
export interface ApiError {
  error_code: string
  error_message: string
  details?: Record<string, any>
  timestamp: string
  request_id: string
}

// Legacy compatibility - will be removed in future versions
export interface FileUploadResponse {
  presigned_url: string
  file_id: string
  upload_url: string
}

// UI-specific types
export interface NotificationState {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  actions?: Array<{
    label: string
    action: () => void
  }>
}

export interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
}

export interface FormValidationError {
  field: string
  message: string
}

export interface ComponentError {
  message: string
  stack?: string
  componentStack?: string
  errorBoundary?: string
}