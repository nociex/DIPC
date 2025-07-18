"use client"

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Download, Eye } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/components/ui/use-toast'
import type { Task, TaskStatus } from '@/types'

interface TaskListViewProps {
  tasks: Task[]
  onRefresh?: () => void
  onViewResults?: (task: Task) => void
  onDownloadResults?: (task: Task) => void
  className?: string
}

interface TaskItemProps {
  task: Task
  onViewResults?: (task: Task) => void
  onDownloadResults?: (task: Task) => void
}

function TaskStatusIcon({ status }: { status: TaskStatus }) {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />
    case 'processing':
      return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />
    case 'cancelled':
      return <AlertCircle className="h-4 w-4 text-gray-500" />
    default:
      return <Clock className="h-4 w-4 text-gray-400" />
  }
}

function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const statusConfig = {
    pending: { label: 'Pending', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
    processing: { label: 'Processing', className: 'bg-blue-100 text-blue-800 border-blue-200' },
    completed: { label: 'Completed', className: 'bg-green-100 text-green-800 border-green-200' },
    failed: { label: 'Failed', className: 'bg-red-100 text-red-800 border-red-200' },
    cancelled: { label: 'Cancelled', className: 'bg-gray-100 text-gray-800 border-gray-200' }
  }

  const config = statusConfig[status] || statusConfig.pending

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.className}`}>
      {config.label}
    </span>
  )
}

function TaskProgress({ task }: { task: Task }) {
  // Calculate progress based on task status and type
  const getProgress = () => {
    switch (task.status) {
      case 'pending':
        return 0
      case 'processing':
        // For archive tasks, we can show more granular progress
        if (task.task_type === 'archive_processing') {
          return 25 // Extracting
        } else if (task.task_type === 'document_parsing') {
          return 50 // Parsing
        } else if (task.task_type === 'vectorization') {
          return 75 // Vectorizing
        }
        return 30
      case 'completed':
        return 100
      case 'failed':
      case 'cancelled':
        return 0
      default:
        return 0
    }
  }

  const progress = getProgress()

  if (task.status === 'pending' || task.status === 'failed' || task.status === 'cancelled') {
    return null
  }

  return (
    <div className="space-y-1">
      <Progress value={progress} className="h-2" />
      <p className="text-xs text-muted-foreground">
        {task.status === 'processing' ? `Processing... ${progress}%` : 'Complete'}
      </p>
    </div>
  )
}

function TaskItem({ task, onViewResults, onDownloadResults }: TaskItemProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const formatDuration = (startDate: string, endDate?: string) => {
    const start = new Date(startDate)
    const end = endDate ? new Date(endDate) : new Date()
    const duration = Math.round((end.getTime() - start.getTime()) / 1000)
    
    if (duration < 60) return `${duration}s`
    if (duration < 3600) return `${Math.round(duration / 60)}m`
    return `${Math.round(duration / 3600)}h`
  }

  const getTaskTypeLabel = (taskType: string) => {
    switch (taskType) {
      case 'archive_processing':
        return 'Archive Processing'
      case 'document_parsing':
        return 'Document Parsing'
      case 'vectorization':
        return 'Vectorization'
      default:
        return taskType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between space-x-4">
          <div className="flex-1 space-y-3">
            {/* Task Header */}
            <div className="flex items-center space-x-3">
              <TaskStatusIcon status={task.status} />
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-medium">
                    {getTaskTypeLabel(task.task_type)}
                  </h3>
                  <TaskStatusBadge status={task.status} />
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  ID: {task.id.slice(0, 8)}...
                </p>
              </div>
            </div>

            {/* Task Progress */}
            <TaskProgress task={task} />

            {/* Task Details */}
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-muted-foreground">Created:</span>
                <p className="font-medium">{formatDate(task.created_at)}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Duration:</span>
                <p className="font-medium">
                  {formatDuration(task.created_at, task.completed_at)}
                </p>
              </div>
              {task.estimated_cost && (
                <div>
                  <span className="text-muted-foreground">Est. Cost:</span>
                  <p className="font-medium">${task.estimated_cost.toFixed(3)}</p>
                </div>
              )}
              {task.actual_cost && (
                <div>
                  <span className="text-muted-foreground">Actual Cost:</span>
                  <p className="font-medium">${task.actual_cost.toFixed(3)}</p>
                </div>
              )}
            </div>

            {/* Error Message */}
            {task.error_message && (
              <div className="p-2 bg-red-50 border border-red-200 rounded text-xs">
                <p className="text-red-800 font-medium">Error:</p>
                <p className="text-red-700">{task.error_message}</p>
              </div>
            )}

            {/* File Information */}
            {task.file_url && (
              <div className="text-xs">
                <span className="text-muted-foreground">File:</span>
                <p className="font-medium truncate">
                  {task.file_url.split('/').pop() || 'Unknown file'}
                </p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col space-y-2">
            {task.status === 'completed' && task.results && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onViewResults?.(task)}
                  className="text-xs"
                >
                  <Eye className="h-3 w-3 mr-1" />
                  View
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onDownloadResults?.(task)}
                  className="text-xs"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function TaskListView({
  tasks,
  onRefresh,
  onViewResults,
  onDownloadResults,
  className
}: TaskListViewProps) {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const { toast } = useToast()

  // Auto-refresh for processing tasks
  useEffect(() => {
    const hasProcessingTasks = tasks.some(task => 
      task.status === 'pending' || task.status === 'processing'
    )

    if (hasProcessingTasks && onRefresh) {
      const interval = setInterval(() => {
        onRefresh()
      }, 5000) // Refresh every 5 seconds

      return () => clearInterval(interval)
    }
  }, [tasks, onRefresh])

  const handleRefresh = async () => {
    if (!onRefresh) return

    setIsRefreshing(true)
    try {
      await onRefresh()
      toast({
        title: "Tasks refreshed",
        description: "Task list has been updated",
      })
    } catch (error) {
      toast({
        title: "Refresh failed",
        description: "Failed to refresh task list",
        variant: "destructive",
      })
    } finally {
      setIsRefreshing(false)
    }
  }

  const getTaskStats = () => {
    const stats = tasks.reduce((acc, task) => {
      acc[task.status] = (acc[task.status] || 0) + 1
      return acc
    }, {} as Record<TaskStatus, number>)

    return stats
  }

  const stats = getTaskStats()

  if (tasks.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center">
          <div className="space-y-3">
            <Clock className="h-12 w-12 text-muted-foreground mx-auto" />
            <div>
              <h3 className="text-lg font-medium">No tasks yet</h3>
              <p className="text-muted-foreground">
                Upload some documents to get started
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Task Monitor</CardTitle>
            <CardDescription>
              Track the progress of your document processing tasks
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Task Statistics */}
        <div className="flex space-x-4 text-sm">
          {stats.completed && (
            <div className="flex items-center space-x-1 text-green-600">
              <CheckCircle className="h-4 w-4" />
              <span>{stats.completed} completed</span>
            </div>
          )}
          {stats.processing && (
            <div className="flex items-center space-x-1 text-blue-600">
              <RefreshCw className="h-4 w-4" />
              <span>{stats.processing} processing</span>
            </div>
          )}
          {stats.pending && (
            <div className="flex items-center space-x-1 text-yellow-600">
              <Clock className="h-4 w-4" />
              <span>{stats.pending} pending</span>
            </div>
          )}
          {stats.failed && (
            <div className="flex items-center space-x-1 text-red-600">
              <XCircle className="h-4 w-4" />
              <span>{stats.failed} failed</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {tasks.map((task) => (
          <TaskItem
            key={task.id}
            task={task}
            onViewResults={onViewResults}
            onDownloadResults={onDownloadResults}
          />
        ))}
      </CardContent>
    </Card>
  )
}