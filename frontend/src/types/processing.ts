/**
 * Enhanced processing types for real-time progress tracking
 */

import { TaskStatus } from './shared'

export interface ProcessingStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped'
  progress: number
  startTime?: Date
  endTime?: Date
  duration?: number
  error?: string
}

export interface ProcessingTask {
  id: string
  fileName: string
  originalFilename: string
  fileSize: number
  status: TaskStatus
  progress: number
  currentStep: string
  currentStepIndex: number
  totalSteps: number
  steps: ProcessingStep[]
  
  // Time tracking
  startTime: Date
  lastUpdate: Date
  estimatedTimeRemaining: number
  estimatedTotalTime: number
  actualDuration?: number
  
  // Progress details
  throughput?: number // bytes per second
  processedBytes: number
  
  // Error handling
  error?: ProcessingError
  retryCount: number
  maxRetries: number
  
  // Cost tracking
  estimatedCost: number
  actualCost?: number
  
  // Configuration
  options: ProcessingOptions
}

export interface ProcessingError {
  code: string
  message: string
  details?: Record<string, any>
  recoverable: boolean
  suggestedActions: RecoveryAction[]
  timestamp: Date
}

export interface RecoveryAction {
  type: 'retry' | 'skip' | 'modify' | 'contact_support'
  label: string
  description: string
  action: () => Promise<void>
  automatic?: boolean
  delay?: number
}

export interface ProcessingOptions {
  enableVectorization: boolean
  storagePolicy: 'temporary' | 'permanent'
  maxCostLimit: number
  llmProvider: string
  customPrompt?: string
  qualityLevel: 'fast' | 'balanced' | 'accurate'
  priority: 'low' | 'normal' | 'high'
}

export interface ProcessingStats {
  totalTasks: number
  activeTasks: number
  completedTasks: number
  failedTasks: number
  averageProcessingTime: number
  totalCost: number
  successRate: number
}

export interface TaskUpdate {
  taskId: string
  status: TaskStatus
  progress: number
  currentStep: string
  currentStepIndex: number
  estimatedTimeRemaining: number
  throughput?: number
  processedBytes: number
  error?: ProcessingError
  timestamp: Date
}

export interface ProcessingProgressProps {
  tasks: ProcessingTask[]
  showDetailedProgress: boolean
  onToggleDetails: () => void
  onTaskAction: (taskId: string, action: TaskAction) => void
  onTaskSelect?: (taskId: string) => void
  selectedTaskId?: string
}

export interface TaskAction {
  type: 'cancel' | 'retry' | 'pause' | 'resume' | 'priority_up' | 'priority_down'
  reason?: string
}

export interface ProcessingQueueItem {
  task: ProcessingTask
  priority: number
  queuePosition: number
  estimatedStartTime: Date
}

export interface ProcessingQueue {
  items: ProcessingQueueItem[]
  totalItems: number
  activeSlots: number
  maxConcurrentTasks: number
  averageWaitTime: number
}