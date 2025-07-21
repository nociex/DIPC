import axios, { AxiosError, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type {
    Task,
    TaskCreateRequest,
    TaskResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    ErrorResponse,
    HealthCheckResponse,
    DocumentParsingResult
} from '@/types'
import { TaskStatus } from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Custom error class for API errors
export class ApiError extends Error {
    constructor(
        public errorCode: string,
        public errorMessage: string,
        public details?: Record<string, any>,
        public requestId?: string,
        public status?: number
    ) {
        super(errorMessage)
        this.name = 'ApiError'
    }

    static fromErrorResponse(error: ErrorResponse, status?: number): ApiError {
        return new ApiError(
            error.error_code,
            error.error_message,
            error.details,
            error.request_id,
            status
        )
    }

    static fromAxiosError(error: AxiosError): ApiError {
        if (error.response?.data && typeof error.response.data === 'object') {
            const errorData = error.response.data as ErrorResponse
            return ApiError.fromErrorResponse(errorData, error.response.status)
        }

        return new ApiError(
            'NETWORK_ERROR',
            error.message || 'Network request failed',
            { originalError: error.code },
            undefined,
            error.response?.status
        )
    }
}

// Request/Response interceptor types
interface RequestInterceptor {
    (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>
}

interface ResponseInterceptor {
    onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>
    onRejected?: (error: AxiosError) => Promise<never>
}

// API Client configuration
interface ApiClientConfig {
    baseURL?: string
    timeout?: number
    retryAttempts?: number
    retryDelay?: number
}

class ApiClient {
    private client = axios.create()
    private config: Required<ApiClientConfig>

    constructor(config: ApiClientConfig = {}) {
        this.config = {
            baseURL: config.baseURL || `${API_BASE_URL}/v1`,
            timeout: config.timeout || 30000,
            retryAttempts: config.retryAttempts || 3,
            retryDelay: config.retryDelay || 1000,
        }

        this.setupClient()
    }

    private setupClient(): void {
        this.client.defaults.baseURL = this.config.baseURL
        this.client.defaults.timeout = this.config.timeout
        this.client.defaults.headers.common['Content-Type'] = 'application/json'

        // Request interceptor
        this.client.interceptors.request.use(
            (config) => {
                // Add correlation ID for request tracking
                config.headers['X-Request-ID'] = this.generateRequestId()

                // Add auth token if available
                const token = this.getAuthToken()
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`
                }

                return config
            },
            (error) => Promise.reject(error)
        )

        // Response interceptor with retry logic
        this.client.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const config = error.config as AxiosRequestConfig & { _retryCount?: number }

                // Implement retry logic for transient errors
                if (this.shouldRetry(error) && (!config._retryCount || config._retryCount < this.config.retryAttempts)) {
                    config._retryCount = (config._retryCount || 0) + 1

                    await this.delay(this.config.retryDelay * config._retryCount)
                    return this.client.request(config)
                }

                throw ApiError.fromAxiosError(error)
            }
        )
    }

    private shouldRetry(error: AxiosError): boolean {
        if (!error.response) return true // Network errors

        const status = error.response.status
        // Retry on server errors and rate limiting
        return status >= 500 || status === 429
    }

    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }

    private generateRequestId(): string {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    }

    private getAuthToken(): string | null {
        // In a real app, this would get the token from secure storage
        if (typeof window !== 'undefined') {
            return localStorage.getItem('auth_token')
        }
        return null
    }

    // Task Management Methods
    async createTask(request: TaskCreateRequest): Promise<TaskResponse> {
        const response = await this.client.post<TaskResponse>('/tasks', request)
        return response.data
    }

    async getTask(taskId: string): Promise<Task> {
        const response = await this.client.get<Task>(`/tasks/${taskId}`)
        return response.data
    }

    async getTaskStatus(taskId: string): Promise<{ status: TaskStatus; progress?: number }> {
        const response = await this.client.get<{ status: TaskStatus; progress?: number }>(`/tasks/${taskId}/status`)
        return response.data
    }

    async getTaskResults(taskId: string): Promise<DocumentParsingResult> {
        const response = await this.client.get<DocumentParsingResult>(`/tasks/${taskId}/results`)
        return response.data
    }

    async cancelTask(taskId: string): Promise<void> {
        await this.client.post(`/tasks/${taskId}/cancel`)
    }

    async listTasks(userId: string, limit = 50, offset = 0): Promise<{ tasks: Task[]; total: number }> {
        const response = await this.client.get<{ tasks: Task[]; total: number }>('/tasks', {
            params: { user_id: userId, limit, offset }
        })
        return response.data
    }

    // File Management Methods
    async getPresignedUrl(request: PresignedUrlRequest): Promise<PresignedUrlResponse> {
        const response = await this.client.post<PresignedUrlResponse>('/upload/presigned-url', request)
        return response.data
    }

    async uploadFile(file: File, presignedUrl: string, onProgress?: (progress: number) => void): Promise<void> {
        const formData = new FormData()
        formData.append('file', file)

        await axios.put(presignedUrl, file, {
            headers: {
                'Content-Type': file.type,
            },
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                    onProgress(progress)
                }
            },
        })
    }

    async downloadFile(fileId: string): Promise<Blob> {
        const response = await this.client.get(`/files/${fileId}/download`, {
            responseType: 'blob'
        })
        return response.data
    }

    // System Methods
    async healthCheck(): Promise<HealthCheckResponse> {
        const response = await this.client.get<HealthCheckResponse>('/health')
        return response.data
    }

    async getMetrics(): Promise<Record<string, any>> {
        const response = await this.client.get<Record<string, any>>('/metrics')
        return response.data
    }

    // Utility Methods
    addRequestInterceptor(interceptor: RequestInterceptor): number {
        return this.client.interceptors.request.use(interceptor)
    }

    addResponseInterceptor(interceptor: ResponseInterceptor): number {
        return this.client.interceptors.response.use(
            interceptor.onFulfilled,
            interceptor.onRejected
        )
    }

    removeInterceptor(type: 'request' | 'response', id: number): void {
        this.client.interceptors[type].eject(id)
    }
}

// Create default API client instance
export const apiClient = new ApiClient()

// Export convenience methods
export const api = {
    // Task management
    createTask: (request: TaskCreateRequest) => apiClient.createTask(request),
    getTask: (taskId: string) => apiClient.getTask(taskId),
    getTaskStatus: (taskId: string) => apiClient.getTaskStatus(taskId),
    getTaskResults: (taskId: string) => apiClient.getTaskResults(taskId),
    cancelTask: (taskId: string) => apiClient.cancelTask(taskId),
    listTasks: (userId: string, limit?: number, offset?: number) =>
        apiClient.listTasks(userId, limit, offset),

    // File management
    getPresignedUrl: (request: PresignedUrlRequest) => apiClient.getPresignedUrl(request),
    uploadFile: (file: File, presignedUrl: string, onProgress?: (progress: number) => void) =>
        apiClient.uploadFile(file, presignedUrl, onProgress),
    downloadFile: (fileId: string) => apiClient.downloadFile(fileId),

    // System
    healthCheck: () => apiClient.healthCheck(),
    getMetrics: () => apiClient.getMetrics(),
}

// Export types for external use
export type {
    Task,
    TaskCreateRequest,
    TaskResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    ErrorResponse,
    HealthCheckResponse,
    TaskStatus,
    DocumentParsingResult
}