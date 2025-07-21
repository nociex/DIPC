import { jest } from '@jest/globals'
import axios, { AxiosError, AxiosResponse } from 'axios'
import type {
  Task,
  TaskCreateRequest,
  TaskResponse,
  PresignedUrlRequest,
  PresignedUrlResponse,
  ErrorResponse,
  HealthCheckResponse,
  TaskStatus,
  DocumentParsingResult,
  TokenUsage,
  DocumentMetadata
} from '../../../../shared/types'

// Mock data factories
export const createMockTask = (overrides: Partial<Task> = {}): Task => ({
  id: 'task_123',
  user_id: 'user_456',
  status: 'pending' as TaskStatus,
  task_type: 'document_parsing' as any,
  options: {
    enable_vectorization: true,
    storage_policy: 'permanent' as any,
  },
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides,
})

export const createMockTaskResponse = (overrides: Partial<TaskResponse> = {}): TaskResponse => ({
  task_id: 'task_123',
  status: 'pending' as TaskStatus,
  created_at: '2024-01-15T10:00:00Z',
  ...overrides,
})

export const createMockTaskCreateRequest = (overrides: Partial<TaskCreateRequest> = {}): TaskCreateRequest => ({
  file_urls: ['https://example.com/file1.pdf'],
  user_id: 'user_456',
  options: {
    enable_vectorization: true,
    storage_policy: 'permanent' as any,
  },
  ...overrides,
})

export const createMockPresignedUrlRequest = (overrides: Partial<PresignedUrlRequest> = {}): PresignedUrlRequest => ({
  filename: 'test-document.pdf',
  file_type: 'application/pdf',
  file_size: 1024000,
  ...overrides,
})

export const createMockPresignedUrlResponse = (overrides: Partial<PresignedUrlResponse> = {}): PresignedUrlResponse => ({
  upload_url: 'https://storage.example.com/upload/signed-url',
  file_url: 'https://storage.example.com/files/file_123',
  expires_in: 3600,
  ...overrides,
})

export const createMockErrorResponse = (overrides: Partial<ErrorResponse> = {}): ErrorResponse => ({
  error_code: 'VALIDATION_ERROR',
  error_message: 'Invalid request parameters',
  timestamp: '2024-01-15T10:00:00Z',
  request_id: 'req_123',
  ...overrides,
})

export const createMockHealthCheckResponse = (overrides: Partial<HealthCheckResponse> = {}): HealthCheckResponse => ({
  status: 'healthy',
  timestamp: '2024-01-15T10:00:00Z',
  services: {
    database: 'up',
    redis: 'up',
    storage: 'up',
    vector_db: 'up',
  },
  ...overrides,
})

export const createMockDocumentParsingResult = (overrides: Partial<DocumentParsingResult> = {}): DocumentParsingResult => ({
  task_id: 'task_123',
  extracted_content: {
    title: 'Test Document',
    content: 'This is test content',
    metadata: { pages: 1 }
  },
  confidence_score: 0.95,
  processing_time: 2.5,
  token_usage: {
    prompt_tokens: 100,
    completion_tokens: 50,
    total_tokens: 150,
    estimated_cost: 0.001
  } as TokenUsage,
  metadata: {
    file_type: 'pdf',
    page_count: 1,
    language: 'en',
    extraction_method: 'llm'
  } as DocumentMetadata,
  ...overrides,
})

// Mock file creation utilities
export const createMockFile = (
  name = 'test-file.pdf',
  type = 'application/pdf',
  size = 1024000
): File => {
  const content = new Array(size).fill('a').join('')
  const blob = new Blob([content], { type })
  return new File([blob], name, { type })
}

export const createMockFileList = (files: File[]): FileList => {
  const fileList = {
    length: files.length,
    item: (index: number) => files[index] || null,
    [Symbol.iterator]: function* () {
      for (let i = 0; i < files.length; i++) {
        yield files[i]
      }
    }
  }
  
  // Add files as indexed properties
  files.forEach((file, index) => {
    Object.defineProperty(fileList, index, {
      value: file,
      enumerable: true
    })
  })
  
  return fileList as FileList
}

// Axios mock utilities
export class MockAxiosAdapter {
  private handlers: Map<string, (config: any) => Promise<AxiosResponse>> = new Map()
  private defaultHandler?: (config: any) => Promise<AxiosResponse>

  onGet(url: string, handler: (config: any) => Promise<AxiosResponse>): void {
    this.handlers.set(`GET:${url}`, handler)
  }

  onPost(url: string, handler: (config: any) => Promise<AxiosResponse>): void {
    this.handlers.set(`POST:${url}`, handler)
  }

  onPut(url: string, handler: (config: any) => Promise<AxiosResponse>): void {
    this.handlers.set(`PUT:${url}`, handler)
  }

  onDelete(url: string, handler: (config: any) => Promise<AxiosResponse>): void {
    this.handlers.set(`DELETE:${url}`, handler)
  }

  onAny(handler: (config: any) => Promise<AxiosResponse>): void {
    this.defaultHandler = handler
  }

  async handle(config: any): Promise<AxiosResponse> {
    const method = config.method?.toUpperCase() || 'GET'
    const url = config.url || ''
    const key = `${method}:${url}`
    
    const handler = this.handlers.get(key) || this.defaultHandler
    if (!handler) {
      throw new AxiosError(
        `No handler found for ${method} ${url}`,
        'MOCK_ERROR',
        config,
        null,
        {
          status: 404,
          statusText: 'Not Found',
          data: { error: 'Mock handler not found' },
          headers: {},
          config
        } as AxiosResponse
      )
    }

    return handler(config)
  }

  reset(): void {
    this.handlers.clear()
    this.defaultHandler = undefined
  }
}

// Test scenario builders
export const createSuccessResponse = <T>(data: T, status = 200): AxiosResponse<T> => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {} as any,
})

export const createErrorResponse = (
  errorResponse: ErrorResponse,
  status = 400
): AxiosError => {
  const axiosResponse: AxiosResponse = {
    data: errorResponse,
    status,
    statusText: 'Bad Request',
    headers: {},
    config: {} as any,
  }

  return new AxiosError(
    errorResponse.error_message,
    'API_ERROR',
    {} as any,
    null,
    axiosResponse
  )
}

export const createNetworkError = (message = 'Network Error'): AxiosError => {
  return new AxiosError(message, 'NETWORK_ERROR', {} as any, null)
}

// Integration test helpers
export const setupApiMocks = () => {
  const mockAdapter = new MockAxiosAdapter()
  
  // Mock axios.create to return our mock adapter
  const mockAxios = {
    create: jest.fn(() => ({
      defaults: { baseURL: '', timeout: 30000, headers: { common: {} } },
      interceptors: {
        request: { use: jest.fn(), eject: jest.fn() },
        response: { use: jest.fn(), eject: jest.fn() }
      },
      get: jest.fn((url, config) => mockAdapter.handle({ method: 'GET', url, ...config })),
      post: jest.fn((url, data, config) => mockAdapter.handle({ method: 'POST', url, data, ...config })),
      put: jest.fn((url, data, config) => mockAdapter.handle({ method: 'PUT', url, data, ...config })),
      delete: jest.fn((url, config) => mockAdapter.handle({ method: 'DELETE', url, ...config })),
      request: jest.fn((config) => mockAdapter.handle(config)),
    })),
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  }

  // Replace axios with our mock
  jest.doMock('axios', () => mockAxios)
  
  return { mockAdapter, mockAxios }
}

// Common test scenarios
export const apiTestScenarios = {
  // Task management scenarios
  createTaskSuccess: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onPost('/tasks', async (config) => {
      const request = config.data as TaskCreateRequest
      return createSuccessResponse(createMockTaskResponse({
        task_id: 'task_new_123',
        status: 'pending' as TaskStatus,
      }))
    })
  },

  createTaskValidationError: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onPost('/tasks', async () => {
      throw createErrorResponse(createMockErrorResponse({
        error_code: 'VALIDATION_ERROR',
        error_message: 'Invalid file URLs provided',
      }))
    })
  },

  getTaskSuccess: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onGet('/tasks/task_123', async () => {
      return createSuccessResponse(createMockTask({
        id: 'task_123',
        status: 'completed' as TaskStatus,
      }))
    })
  },

  getTaskNotFound: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onGet('/tasks/nonexistent', async () => {
      throw createErrorResponse(createMockErrorResponse({
        error_code: 'TASK_NOT_FOUND',
        error_message: 'Task not found',
      }), 404)
    })
  },

  // File upload scenarios
  presignedUrlSuccess: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onPost('/upload/presigned-url', async () => {
      return createSuccessResponse(createMockPresignedUrlResponse())
    })
  },

  presignedUrlFileTooLarge: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onPost('/upload/presigned-url', async () => {
      throw createErrorResponse(createMockErrorResponse({
        error_code: 'FILE_TOO_LARGE',
        error_message: 'File size exceeds maximum limit',
      }))
    })
  },

  // Health check scenarios
  healthCheckHealthy: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onGet('/health', async () => {
      return createSuccessResponse(createMockHealthCheckResponse())
    })
  },

  healthCheckUnhealthy: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onGet('/health', async () => {
      return createSuccessResponse(createMockHealthCheckResponse({
        status: 'unhealthy',
        services: {
          database: 'down',
          redis: 'up',
          storage: 'up',
        }
      }))
    })
  },

  // Network error scenarios
  networkError: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onAny(async () => {
      throw createNetworkError('Connection timeout')
    })
  },

  serverError: (mockAdapter: MockAxiosAdapter) => {
    mockAdapter.onAny(async () => {
      throw createErrorResponse(createMockErrorResponse({
        error_code: 'INTERNAL_SERVER_ERROR',
        error_message: 'Internal server error occurred',
      }), 500)
    })
  },
}

// Test assertion helpers
export const expectApiError = (error: any, expectedCode: string, expectedMessage?: string) => {
  expect(error).toBeInstanceOf(Error)
  expect(error.errorCode).toBe(expectedCode)
  if (expectedMessage) {
    expect(error.errorMessage).toContain(expectedMessage)
  }
}

export const expectSuccessfulResponse = <T>(response: T, expectedData: Partial<T>) => {
  expect(response).toBeDefined()
  Object.keys(expectedData).forEach(key => {
    expect((response as any)[key]).toEqual((expectedData as any)[key])
  })
}

// Performance testing utilities
export const measureApiCallTime = async <T>(apiCall: () => Promise<T>): Promise<{ result: T; duration: number }> => {
  const startTime = performance.now()
  const result = await apiCall()
  const endTime = performance.now()
  
  return {
    result,
    duration: endTime - startTime
  }
}

export const createConcurrentApiCalls = <T>(
  apiCall: () => Promise<T>,
  concurrency: number
): Promise<T>[] => {
  return Array.from({ length: concurrency }, () => apiCall())
}