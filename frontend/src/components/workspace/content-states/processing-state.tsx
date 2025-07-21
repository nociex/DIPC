"use client"

import React, { useMemo, useEffect } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useWorkspace } from '../workspace-container'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Zap,
  FileText,
  Pause,
  Play,
  Square,
  RefreshCw,
  Eye,
  Download,
  MoreHorizontal
} from 'lucide-react'
import { TaskStatus } from '@/types'
import type { Task } from '@/types'

// Processing steps for visualization
const PROCESSING_STEPS = [
  { key: 'upload', label: 'processing.steps.upload' as const },
  { key: 'analysis', label: 'processing.steps.analysis' as const },
  { key: 'extraction', label: 'processing.steps.extraction' as const },
  { key: 'vectorization', label: 'processing.steps.vectorization' as const },
  { key: 'completion', label: 'processing.steps.completion' as const }
]

export function ProcessingState() {
  const { t } = useTranslation()
  const { state, actions } = useWorkspace()

  // Auto-refresh tasks every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      actions.loadTasks()
    }, 5000)

    return () => clearInterval(interval)
  }, [actions])

  // Group tasks by status
  const groupedTasks = useMemo(() => {
    return {
      active: state.tasks.filter(task => 
        task.status === TaskStatus.PENDING || task.status === TaskStatus.PROCESSING
      ),
      completed: state.tasks.filter(task => task.status === TaskStatus.COMPLETED),
      failed: state.tasks.filter(task => task.status === TaskStatus.FAILED)
    }
  }, [state.tasks])

  // Calculate overall progress
  const overallProgress = useMemo(() => {
    if (groupedTasks.active.length === 0) return 100
    
    // Simulate progress based on task age for demo
    const now = Date.now()
    const avgProgress = groupedTasks.active.reduce((acc, task) => {
      const taskAge = now - new Date(task.created_at).getTime()
      const estimatedProgress = Math.min(90, (taskAge / (5 * 60 * 1000)) * 100) // 5 minutes to 90%
      return acc + estimatedProgress
    }, 0) / groupedTasks.active.length
    
    return Math.round(avgProgress)
  }, [groupedTasks.active])

  // Format task duration
  const formatTaskDuration = (task: Task) => {
    const start = new Date(task.created_at)
    const end = task.completed_at ? new Date(task.completed_at) : new Date()
    const duration = end.getTime() - start.getTime()
    const minutes = Math.floor(duration / 60000)
    const seconds = Math.floor((duration % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  // Get current processing step for active tasks
  const getCurrentStep = (task: Task) => {
    if (task.status === TaskStatus.COMPLETED) return 4
    if (task.status === TaskStatus.FAILED) return -1
    
    // Simulate step progression based on task age
    const taskAge = Date.now() - new Date(task.created_at).getTime()
    const progressRatio = Math.min(0.9, taskAge / (5 * 60 * 1000)) // 5 minutes to 90%
    return Math.floor(progressRatio * 4)
  }

  // Handle task actions
  const handleTaskAction = (taskId: string, action: 'view' | 'download' | 'cancel' | 'retry') => {
    const task = state.tasks.find(t => t.id === taskId)
    if (!task) return

    switch (action) {
      case 'view':
        actions.handleTaskSelect(task)
        break
      case 'download':
        // TODO: Implement download functionality
        console.log('Download task:', taskId)
        break
      case 'cancel':
        // TODO: Implement cancel functionality
        console.log('Cancel task:', taskId)
        break
      case 'retry':
        // TODO: Implement retry functionality
        console.log('Retry task:', taskId)
        break
    }
  }

  if (state.tasks.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <Card className="max-w-md w-full">
          <CardContent className="p-8 text-center">
            <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">
              {t('workspace.processing.noTasks')}
            </h3>
            <p className="text-muted-foreground mb-4">
              {t('workspace.processing.noTasksDescription')}
            </p>
            <Button onClick={() => actions.handleViewChange('empty')}>
              {t('workspace.processing.uploadFiles')}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {t('workspace.processing.title')}
          </h2>
          <p className="text-muted-foreground">
            {t('workspace.processing.subtitle')}
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={actions.loadTasks}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            {t('workspace.processing.refresh')}
          </Button>
        </div>
      </div>

      {/* Overall Progress */}
      {groupedTasks.active.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold">
                  {t('workspace.processing.overallProgress')}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {groupedTasks.active.length} {t('workspace.processing.activeTasks')}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{overallProgress}%</div>
                <div className="text-sm text-muted-foreground">
                  {t('workspace.processing.complete')}
                </div>
              </div>
            </div>
            <Progress value={overallProgress} className="h-3" />
          </CardContent>
        </Card>
      )}

      {/* Active Tasks */}
      {groupedTasks.active.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Zap className="w-5 h-5 text-blue-500" />
              <span>{t('workspace.processing.activeTasks')}</span>
              <Badge variant="secondary">{groupedTasks.active.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {groupedTasks.active.map((task) => (
              <ProcessingTaskCard
                key={task.id}
                task={task}
                currentStep={getCurrentStep(task)}
                onAction={handleTaskAction}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Completed Tasks */}
      {groupedTasks.completed.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span>{t('workspace.processing.completedTasks')}</span>
              <Badge variant="secondary">{groupedTasks.completed.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {groupedTasks.completed.map((task) => (
              <CompletedTaskCard
                key={task.id}
                task={task}
                onAction={handleTaskAction}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Failed Tasks */}
      {groupedTasks.failed.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-red-500" />
              <span>{t('workspace.processing.failedTasks')}</span>
              <Badge variant="destructive">{groupedTasks.failed.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {groupedTasks.failed.map((task) => (
              <FailedTaskCard
                key={task.id}
                task={task}
                onAction={handleTaskAction}
              />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Processing Task Card Component
interface ProcessingTaskCardProps {
  task: Task
  currentStep: number
  onAction: (taskId: string, action: 'view' | 'download' | 'cancel' | 'retry') => void
}

function ProcessingTaskCard({ task, currentStep, onAction }: ProcessingTaskCardProps) {
  const { t } = useTranslation()
  
  return (
    <div className="border rounded-lg p-4 bg-blue-50/50 border-blue-200">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="font-medium">
            {t('workspace.processing.task')} {task.id.slice(0, 8)}
          </h4>
          <p className="text-sm text-muted-foreground">
            {t('workspace.processing.duration')}: {formatTaskDuration(task)}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
            {t('processing.status.inProgress')}
          </Badge>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Processing Steps */}
      <div className="space-y-2">
        {PROCESSING_STEPS.map((step, index) => (
          <div key={step.key} className="flex items-center space-x-3">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
              index < currentStep 
                ? 'bg-green-500 text-white' 
                : index === currentStep 
                ? 'bg-blue-500 text-white animate-pulse' 
                : 'bg-gray-200 text-gray-500'
            }`}>
              {index < currentStep ? '✓' : index + 1}
            </div>
            <span className={`text-sm ${
              index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
            }`}>
              {t(step.label)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Completed Task Card Component
interface CompletedTaskCardProps {
  task: Task
  onAction: (taskId: string, action: 'view' | 'download' | 'cancel' | 'retry') => void
}

function CompletedTaskCard({ task, onAction }: CompletedTaskCardProps) {
  const { t } = useTranslation()
  
  return (
    <div className="border rounded-lg p-4 bg-green-50/50 border-green-200">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">
            {t('workspace.processing.task')} {task.id.slice(0, 8)}
          </h4>
          <p className="text-sm text-muted-foreground">
            {t('workspace.processing.completedIn')}: {formatTaskDuration(task)}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            {t('processing.status.completed')}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAction(task.id, 'view')}
            className="h-8 w-8 p-0"
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAction(task.id, 'download')}
            className="h-8 w-8 p-0"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// Failed Task Card Component
interface FailedTaskCardProps {
  task: Task
  onAction: (taskId: string, action: 'view' | 'download' | 'cancel' | 'retry') => void
}

function FailedTaskCard({ task, onAction }: FailedTaskCardProps) {
  const { t } = useTranslation()
  
  return (
    <div className="border rounded-lg p-4 bg-red-50/50 border-red-200">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">
            {t('workspace.processing.task')} {task.id.slice(0, 8)}
          </h4>
          <p className="text-sm text-red-600">
            {t('workspace.processing.failed')}: {task.error_message || t('workspace.processing.unknownError')}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="destructive">
            {t('processing.status.failed')}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAction(task.id, 'retry')}
            className="h-8 w-8 p-0"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

// Helper function to format task duration
function formatTaskDuration(task: Task): string {
  const start = new Date(task.created_at)
  const end = task.completed_at ? new Date(task.completed_at) : new Date()
  const duration = end.getTime() - start.getTime()
  const minutes = Math.floor(duration / 60000)
  const seconds = Math.floor((duration % 60000) / 1000)
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}