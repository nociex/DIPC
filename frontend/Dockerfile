FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy application code
COPY . .

# Create a minimal shared directory structure for TypeScript compilation
# This is a workaround since we can't access the parent directory during build
RUN mkdir -p ../shared/types && \
    cat > ../shared/types/index.ts << 'EOF'
// Placeholder for shared types during Docker build
export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum StoragePolicy {
  PERMANENT = 'permanent',
  TEMPORARY = 'temporary'
}

export enum TaskType {
  DOCUMENT_PARSING = 'document_parsing',
  ARCHIVE_PROCESSING = 'archive_processing',
  VECTORIZATION = 'vectorization',
  CLEANUP = 'cleanup'
}

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

export interface TaskOptions {
  enable_vectorization?: boolean;
  storage_policy?: StoragePolicy;
  max_cost_limit?: number;
  llm_provider?: string;
  custom_prompt?: string;
}

export interface TaskResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  estimated_cost?: number;
  results?: any;
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

export interface UploadProgress {
  file_id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
  error_message?: string;
}

export interface ErrorResponse {
  error_code: string;
  error_message: string;
  details?: Record<string, any>;
  timestamp: string;
  request_id: string;
}
EOF

# Build the application
RUN npm run build

# Remove devDependencies after build to reduce image size
RUN npm prune --production

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Change ownership
RUN chown -R nextjs:nodejs /app
USER nextjs

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]