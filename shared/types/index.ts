/**
 * Shared TypeScript type definitions for DIPC
 */

// Task Status Enum
export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// Storage Policy Enum
export enum StoragePolicy {
  PERMANENT = 'permanent',
  TEMPORARY = 'temporary'
}

// Task Types
export enum TaskType {
  DOCUMENT_PARSING = 'document_parsing',
  ARCHIVE_PROCESSING = 'archive_processing',
  VECTORIZATION = 'vectorization',
  CLEANUP = 'cleanup'
}

// Base Task Interface
export interface Task {
  id: string;
  user_id: string;
  parent_task_id?: string;
  status: TaskStatus;
  task_type: TaskType;
  file_url?: string;
  original_filename?: string;
  options: TaskOptions;
  estimated_cost?: number;
  actual_cost?: number;
  results?: any;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

// Task Options Interface
export interface TaskOptions {
  enable_vectorization?: boolean;
  storage_policy?: StoragePolicy;
  max_cost_limit?: number;
  llm_provider?: string;
  custom_prompt?: string;
}

// File Metadata Interface
export interface FileMetadata {
  id: string;
  task_id: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  storage_policy: StoragePolicy;
  expires_at?: string;
  created_at: string;
}

// API Request/Response Types
export interface TaskCreateRequest {
  file_urls: string[];
  user_id: string;
  options: TaskOptions;
}

export interface TaskResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  estimated_cost?: number;
  results?: any;
  error_message?: string;
}

export interface PresignedUrlRequest {
  filename: string;
  file_type: string;
  file_size: number;
}

export interface PresignedUrlResponse {
  upload_url: string;
  file_url: string;
  expires_in: number;
}

// Processing Results
export interface DocumentParsingResult {
  task_id: string;
  extracted_content: Record<string, any>;
  confidence_score: number;
  processing_time: number;
  token_usage: TokenUsage;
  metadata: DocumentMetadata;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
}

export interface DocumentMetadata {
  file_type: string;
  page_count?: number;
  language?: string;
  extraction_method: string;
}

// Error Response
export interface ErrorResponse {
  error_code: string;
  error_message: string;
  details?: Record<string, any>;
  timestamp: string;
  request_id: string;
}

// Health Check Response
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  services: {
    database: 'up' | 'down';
    redis: 'up' | 'down';
    storage: 'up' | 'down';
    vector_db?: 'up' | 'down';
  };
}

// Frontend-specific types
export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
  error_message?: string;
}

export interface TaskListItem {
  id: string;
  filename: string;
  status: TaskStatus;
  created_at: string;
  estimated_cost?: number;
  progress?: number;
}

// Configuration types
export interface LLMProviderConfig {
  name: string;
  base_url: string;
  api_key: string;
  models: string[];
}

export interface SystemConfig {
  max_file_size: number;
  supported_formats: string[];
  default_storage_policy: StoragePolicy;
  cost_limits: {
    default: number;
    maximum: number;
  };
}