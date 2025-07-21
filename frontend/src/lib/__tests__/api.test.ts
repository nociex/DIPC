import { describe, it, expect, beforeEach, jest } from '@jest/globals'
import axios, { AxiosError } from 'axios'
import { ApiError, api } from '../api'
import {
  createMockTask,
  createMockTaskCreateRequest,
  createMockPresignedUrlRequest,
  createMockTaskResponse,
  createMockPresignedUrlResponse,
  createMockErrorResponse,
  createMockHealthCheckResponse
} from './api-test-utils'

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    defaults: { baseURL: '', timeout: 30000, headers: { common: {} } },
    interceptors: {
      request: { use: jest.fn(), eject: jest.fn() },
      response: { use: jest.fn(), eject: jest.fn() }
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
  })),
  put: jest.fn(),
}))

const mockedAxios = axios as jest.Mocked<typeof axios>

describe('API Client', () => {
  let mockAxiosInstance: any

  beforeEach(() => {
    jest.clearAllMocks()
    mockAxiosInstance = {
      defaults: { baseURL: '', timeout: 30000, headers: { common: {} } },
      interceptors: {
        request: { use: jest.fn(), eject: jest.fn() },
        response: { use: jest.fn(), eject: jest.fn() }
      },
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      request: jest.fn(),
    }
    mockedAxios.create = jest.fn().mockReturnValue(mockAxiosInstance)
  })

  describe('Task Management', () => {
    describe('createTask', () => {
      it('should create a task successfully', async () => {
        const mockResponse = createMockTaskResponse({ task_id: 'task_new_123' })
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        const request = createMockTaskCreateRequest()
        const response = await api.createTask(request)
        
        expect(response.task_id).toBe('task_new_123')
        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/tasks', request)
      })

      it('should handle validation errors', async () => {
        const errorResponse = createMockErrorResponse({
          error_code: 'VALIDATION_ERROR',
          error_message: 'Invalid file URLs provided'
        })
        
        const axiosError = new AxiosError('Validation Error', 'VALIDATION_ERROR', {} as any, null, {
          status: 400,
          data: errorResponse,
          statusText: 'Bad Request',
          headers: {},
          config: {} as any
        })
        
        mockAxiosInstance.post.mockRejectedValue(axiosError)
        
        const request = createMockTaskCreateRequest({ file_urls: [] })
        
        await expect(api.createTask(request)).rejects.toThrow(ApiError)
      })
    })

    describe('getTask', () => {
      it('should retrieve a task successfully', async () => {
        const mockTask = createMockTask({ id: 'task_123', status: 'completed' as any })
        mockAxiosInstance.get.mockResolvedValue({ data: mockTask })
        
        const task = await api.getTask('task_123')
        
        expect(task.id).toBe('task_123')
        expect(task.status).toBe('completed')
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks/task_123')
      })

      it('should handle task not found', async () => {
        const errorResponse = createMockErrorResponse({
          error_code: 'TASK_NOT_FOUND',
          error_message: 'Task not found'
        })
        
        const axiosError = new AxiosError('Not Found', 'NOT_FOUND', {} as any, null, {
          status: 404,
          data: errorResponse,
          statusText: 'Not Found',
          headers: {},
          config: {} as any
        })
        
        mockAxiosInstance.get.mockRejectedValue(axiosError)
        
        await expect(api.getTask('nonexistent')).rejects.toThrow(ApiError)
      })
    })

    describe('getTaskStatus', () => {
      it('should get task status successfully', async () => {
        const statusResponse = { status: 'processing', progress: 50 }
        mockAxiosInstance.get.mockResolvedValue({ data: statusResponse })

        const status = await api.getTaskStatus('task_123')
        
        expect(status.status).toBe('processing')
        expect(status.progress).toBe(50)
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks/task_123/status')
      })
    })

    describe('listTasks', () => {
      it('should list tasks with pagination', async () => {
        const mockTasks = [
          createMockTask({ id: 'task_1' }),
          createMockTask({ id: 'task_2' })
        ]
        const response = { tasks: mockTasks, total: 2 }
        mockAxiosInstance.get.mockResolvedValue({ data: response })

        const result = await api.listTasks('user_456', 10, 0)
        
        expect(result.tasks).toHaveLength(2)
        expect(result.total).toBe(2)
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/tasks', {
          params: { user_id: 'user_456', limit: 10, offset: 0 }
        })
      })
    })
  })

  describe('File Management', () => {
    describe('getPresignedUrl', () => {
      it('should get presigned URL successfully', async () => {
        const mockResponse = createMockPresignedUrlResponse()
        mockAxiosInstance.post.mockResolvedValue({ data: mockResponse })
        
        const request = createMockPresignedUrlRequest()
        const response = await api.getPresignedUrl(request)
        
        expect(response.upload_url).toBe('https://storage.example.com/upload/signed-url')
        expect(response.expires_in).toBe(3600)
        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/upload/presigned-url', request)
      })

      it('should handle file too large error', async () => {
        const errorResponse = createMockErrorResponse({
          error_code: 'FILE_TOO_LARGE',
          error_message: 'File size exceeds maximum limit'
        })
        
        const axiosError = new AxiosError('File Too Large', 'FILE_TOO_LARGE', {} as any, null, {
          status: 413,
          data: errorResponse,
          statusText: 'Payload Too Large',
          headers: {},
          config: {} as any
        })
        
        mockAxiosInstance.post.mockRejectedValue(axiosError)
        
        const request = createMockPresignedUrlRequest({ file_size: 100000000 })
        
        await expect(api.getPresignedUrl(request)).rejects.toThrow(ApiError)
      })
    })

    describe('downloadFile', () => {
      it('should download file as blob', async () => {
        const mockBlob = new Blob(['file content'], { type: 'application/pdf' })
        mockAxiosInstance.get.mockResolvedValue({ data: mockBlob })

        const blob = await api.downloadFile('file_123')
        
        expect(blob).toBeInstanceOf(Blob)
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/files/file_123/download', {
          responseType: 'blob'
        })
      })
    })
  })

  describe('System Methods', () => {
    describe('healthCheck', () => {
      it('should return healthy status', async () => {
        const mockHealth = createMockHealthCheckResponse()
        mockAxiosInstance.get.mockResolvedValue({ data: mockHealth })
        
        const health = await api.healthCheck()
        
        expect(health.status).toBe('healthy')
        expect(health.services.database).toBe('up')
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health')
      })

      it('should return unhealthy status', async () => {
        const mockHealth = createMockHealthCheckResponse({
          status: 'unhealthy',
          services: { database: 'down', redis: 'up', storage: 'up' }
        })
        mockAxiosInstance.get.mockResolvedValue({ data: mockHealth })
        
        const health = await api.healthCheck()
        
        expect(health.status).toBe('unhealthy')
        expect(health.services.database).toBe('down')
      })
    })

    describe('getMetrics', () => {
      it('should return system metrics', async () => {
        const mockMetrics = {
          tasks_processed: 100,
          average_processing_time: 2.5,
          error_rate: 0.02
        }
        mockAxiosInstance.get.mockResolvedValue({ data: mockMetrics })

        const metrics = await api.getMetrics()
        
        expect(metrics).toEqual(mockMetrics)
        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/metrics')
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      const networkError = new AxiosError('Network Error', 'NETWORK_ERROR')
      mockAxiosInstance.get.mockRejectedValue(networkError)
      
      await expect(api.healthCheck()).rejects.toThrow(ApiError)
    })

    it('should handle server errors', async () => {
      const errorResponse = createMockErrorResponse({
        error_code: 'INTERNAL_SERVER_ERROR',
        error_message: 'Internal server error occurred'
      })
      
      const serverError = new AxiosError('Server Error', 'SERVER_ERROR', {} as any, null, {
        status: 500,
        data: errorResponse,
        statusText: 'Internal Server Error',
        headers: {},
        config: {} as any
      })
      
      mockAxiosInstance.get.mockRejectedValue(serverError)
      
      await expect(api.healthCheck()).rejects.toThrow(ApiError)
    })

    it('should create ApiError from ErrorResponse', () => {
      const errorResponse = {
        error_code: 'TEST_ERROR',
        error_message: 'Test error message',
        details: { field: 'value' },
        request_id: 'req_123',
        timestamp: '2024-01-15T10:00:00Z'
      }

      const apiError = ApiError.fromErrorResponse(errorResponse, 400)
      
      expect(apiError.errorCode).toBe('TEST_ERROR')
      expect(apiError.errorMessage).toBe('Test error message')
      expect(apiError.details).toEqual({ field: 'value' })
      expect(apiError.requestId).toBe('req_123')
      expect(apiError.status).toBe(400)
    })
  })
})

describe('ApiError Class', () => {
  it('should create ApiError with all properties', () => {
    const error = new ApiError(
      'TEST_ERROR',
      'Test error message',
      { field: 'value' },
      'req_123',
      400
    )

    expect(error.name).toBe('ApiError')
    expect(error.message).toBe('Test error message')
    expect(error.errorCode).toBe('TEST_ERROR')
    expect(error.errorMessage).toBe('Test error message')
    expect(error.details).toEqual({ field: 'value' })
    expect(error.requestId).toBe('req_123')
    expect(error.status).toBe(400)
  })

  it('should create ApiError from AxiosError', () => {
    const axiosError = new AxiosError('Network Error', 'NETWORK_ERROR', {} as any, null, {
      status: 500,
      data: {
        error_code: 'SERVER_ERROR',
        error_message: 'Internal server error',
        timestamp: '2024-01-15T10:00:00Z',
        request_id: 'req_456'
      },
      statusText: 'Internal Server Error',
      headers: {},
      config: {} as any
    })

    const apiError = ApiError.fromAxiosError(axiosError)
    
    expect(apiError.errorCode).toBe('SERVER_ERROR')
    expect(apiError.errorMessage).toBe('Internal server error')
    expect(apiError.status).toBe(500)
  })

  it('should handle AxiosError without response data', () => {
    const axiosError = new AxiosError('Network Error', 'ECONNREFUSED')

    const apiError = ApiError.fromAxiosError(axiosError)
    
    expect(apiError.errorCode).toBe('NETWORK_ERROR')
    expect(apiError.errorMessage).toBe('Network Error')
    expect(apiError.details?.originalError).toBe('ECONNREFUSED')
  })
})