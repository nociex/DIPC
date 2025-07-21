'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  ChevronUp, 
  ChevronDown, 
  Clock, 
  Zap, 
  AlertCircle, 
  CheckCircle2,
  Eye,
  EyeOff,
  TrendingUp,
  Activity
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { useI18n } from '@/lib/i18n/context'
import { ProcessingTask, TaskAction, ProcessingProgressProps, ProcessingStats } from '@/types/processing'
import { TaskStatus } from '@/types'

const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  tasks,
  showDetailedProgress,
  onToggleDetails,
  onTaskAction,
  onTaskSelect,
  selectedTaskId
}) => {
  const { t } = useI18n()
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

  // Calculate processing statistics
  const stats: ProcessingStats = useMemo(() => {
    const totalTasks = tasks.length
    const activeTasks = tasks.filter(task => 
      task.status === TaskStatus.PROCESSING || task.status === TaskStatus.PENDING
    ).length
    const completedTasks = tasks.filter(task => task.status === TaskStatus.COMPLETED).length
    const failedTasks = tasks.filter(task => task.status === TaskStatus.FAILED).length
    
    const completedTasksWithDuration = tasks.filter(task => 
      task.status === TaskStatus.COMPLETED && task.actualDuration
    )
    const averageProcessingTime = completedTasksWithDuration.length > 0
      ? completedTasksWithDuration.reduce((sum, task) => sum + (task.actualDuration || 0), 0) / completedTasksWithDuration.length
      : 0

    const totalCost = tasks.reduce((sum, task) => sum + (task.actualCost || task.estimatedCost), 0)
    const successRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0

    return {
      totalTasks,
      activeTasks,
      completedTasks,
      failedTasks,
      averageProcessingTime,
      totalCost,
      successRate
    }
  }, [tasks])

  // Calculate overall progress
  const overallProgress = useMemo(() => {
    if (tasks.length === 0) return 0
    const totalProgress = tasks.reduce((sum, task) => sum + task.progress, 0)
    return Math.round(totalProgress / tasks.length)
  }, [tasks])

  const toggleTaskExpansion = (taskId: string) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId)
    } else {
      newExpanded.add(taskId)
    }
    setExpandedTasks(newExpanded)
  }

  const handleTaskAction = (taskId: string, action: TaskAction) => {
    onTaskAction(taskId, action)
  }

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round(seconds / 3600)}h`
  }

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.PROCESSING:
        return <Activity className="h-4 w-4 text-blue-500 animate-pulse" />
      case TaskStatus.COMPLETED:
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case TaskStatus.FAILED:
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case TaskStatus.CANCELLED:
        return <Square className="h-4 w-4 text-gray-500" />
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />
    }
  }

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.PROCESSING:
        return 'bg-blue-500'
      case TaskStatus.COMPLETED:
        return 'bg-green-500'
      case TaskStatus.FAILED:
        return 'bg-red-500'
      case TaskStatus.CANCELLED:
        return 'bg-gray-500'
      default:
        return 'bg-yellow-500'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800'
      case 'normal':
        return 'bg-blue-100 text-blue-800'
      case 'low':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusLabel = (status: TaskStatus): string => {
    switch (status) {
      case TaskStatus.PENDING:
        return t('processing.status.pending')
      case TaskStatus.PROCESSING:
        return t('processing.status.inProgress')
      case TaskStatus.COMPLETED:
        return t('processing.status.completed')
      case TaskStatus.FAILED:
        return t('processing.status.failed')
      case TaskStatus.CANCELLED:
        return t('processing.status.cancelled')
      default:
        return t('processing.status.pending')
    }
  }

  const getPriorityLabel = (priority: string): string => {
    switch (priority) {
      case 'high':
        return t('processing.realtime.priorityHigh')
      case 'normal':
        return t('processing.realtime.priorityNormal')
      case 'low':
        return t('processing.realtime.priorityLow')
      default:
        return t('processing.realtime.priorityNormal')
    }
  }

  return (
    <div className="space-y-6">
      {/* Statistics Overview */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold">
              {t('processing.realtime.title')}
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleDetails}
              className="flex items-center gap-2"
            >
              {showDetailedProgress ? (
                <>
                  <EyeOff className="h-4 w-4" />
                  {t('processing.realtime.hideDetails')}
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4" />
                  {t('processing.realtime.showDetails')}
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Overall Progress */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                {t('processing.realtime.overallProgress')}
              </span>
              <span className="text-sm text-muted-foreground">
                {overallProgress}%
              </span>
            </div>
            <Progress value={overallProgress} className="h-2" />
          </div>

          {/* Statistics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {stats.activeTasks}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('processing.realtime.activeTasks')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {stats.completedTasks}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('processing.realtime.completedTasks')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {stats.failedTasks}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('processing.realtime.failedTasks')}
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {Math.round(stats.successRate)}%
              </div>
              <div className="text-sm text-muted-foreground">
                {t('processing.realtime.successRate')}
              </div>
            </div>
          </div>

          {showDetailedProgress && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {t('processing.realtime.averageTime')}:
                  </span>
                  <span className="font-medium">
                    {formatDuration(stats.averageProcessingTime)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {t('processing.realtime.totalCost')}:
                  </span>
                  <span className="font-medium">
                    ${stats.totalCost.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {t('processing.realtime.throughput')}:
                  </span>
                  <span className="font-medium">
                    {tasks.filter(t => t.throughput).length > 0 
                      ? formatBytes(
                          tasks
                            .filter(t => t.throughput)
                            .reduce((sum, t) => sum + (t.throughput || 0), 0) / 
                          tasks.filter(t => t.throughput).length
                        ) + '/s'
                      : 'N/A'
                    }
                  </span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Task List */}
      <div className="space-y-3">
        <AnimatePresence>
          {tasks.map((task) => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
            >
              <Card 
                className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                  selectedTaskId === task.id ? 'ring-2 ring-blue-500' : ''
                }`}
                onClick={() => onTaskSelect?.(task.id)}
              >
                <CardContent className="p-4">
                  {/* Task Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(task.status)}
                      <div>
                        <div className="font-medium text-sm truncate max-w-[200px]">
                          {task.fileName}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatBytes(task.fileSize)} • {getStatusLabel(task.status)}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Badge 
                        variant="secondary" 
                        className={getPriorityColor(task.options.priority)}
                      >
                        {getPriorityLabel(task.options.priority)}
                      </Badge>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleTaskExpansion(task.id)
                        }}
                      >
                        {expandedTasks.has(task.id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">
                        {task.currentStep} ({task.currentStepIndex + 1}/{task.totalSteps})
                      </span>
                      <span className="text-xs font-medium">
                        {task.progress}%
                      </span>
                    </div>
                    <Progress 
                      value={task.progress} 
                      className="h-2"
                    />
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${getStatusColor(task.status)}`}
                      style={{ width: `${task.progress}%` }}
                    />
                  </div>

                  {/* Time and Cost Info */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                      {task.status === TaskStatus.PROCESSING && (
                        <span>
                          {t('processing.realtime.timeRemaining')}: {formatDuration(task.estimatedTimeRemaining)}
                        </span>
                      )}
                      {task.throughput && (
                        <span>
                          {formatBytes(task.throughput)}/s
                        </span>
                      )}
                    </div>
                    <span>
                      ${(task.actualCost || task.estimatedCost).toFixed(2)}
                    </span>
                  </div>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {expandedTasks.has(task.id) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="mt-4 pt-4 border-t"
                      >
                        {/* Detailed Steps */}
                        <div className="space-y-2 mb-4">
                          <h4 className="text-sm font-medium">
                            {t('processing.realtime.stepProgress')}
                          </h4>
                          {task.steps.map((step, index) => (
                            <div key={step.id} className="flex items-center gap-3">
                              <div className={`w-2 h-2 rounded-full ${
                                step.status === 'completed' ? 'bg-green-500' :
                                step.status === 'active' ? 'bg-blue-500 animate-pulse' :
                                step.status === 'failed' ? 'bg-red-500' :
                                'bg-gray-300'
                              }`} />
                              <div className="flex-1">
                                <div className="text-sm">{step.name}</div>
                                <div className="text-xs text-muted-foreground">
                                  {step.description}
                                </div>
                              </div>
                              {step.status === 'active' && (
                                <div className="text-xs text-muted-foreground">
                                  {step.progress}%
                                </div>
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Task Actions */}
                        <div className="flex items-center gap-2">
                          {task.status === TaskStatus.PROCESSING && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleTaskAction(task.id, { type: 'pause' })
                              }}
                            >
                              <Pause className="h-3 w-3 mr-1" />
                              {t('processing.realtime.pauseTask')}
                            </Button>
                          )}
                          
                          {task.status === TaskStatus.FAILED && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleTaskAction(task.id, { type: 'retry' })
                              }}
                            >
                              <RotateCcw className="h-3 w-3 mr-1" />
                              {t('processing.realtime.retryTask')}
                            </Button>
                          )}
                          
                          {(task.status === TaskStatus.PROCESSING || task.status === TaskStatus.PENDING) && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleTaskAction(task.id, { type: 'cancel' })
                              }}
                            >
                              <Square className="h-3 w-3 mr-1" />
                              {t('processing.realtime.cancelTask')}
                            </Button>
                          )}

                          <div className="flex-1" />
                          
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleTaskAction(task.id, { type: 'priority_up' })
                            }}
                          >
                            <ChevronUp className="h-3 w-3" />
                          </Button>
                          
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleTaskAction(task.id, { type: 'priority_down' })
                            }}
                          >
                            <ChevronDown className="h-3 w-3" />
                          </Button>
                        </div>

                        {/* Error Details */}
                        {task.error && (
                          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-center gap-2 mb-2">
                              <AlertCircle className="h-4 w-4 text-red-500" />
                              <span className="text-sm font-medium text-red-800">
                                {t('processing.realtime.errorDetails')}
                              </span>
                            </div>
                            <div className="text-sm text-red-700 mb-2">
                              {task.error.message}
                            </div>
                            {task.error.suggestedActions.length > 0 && (
                              <div className="space-y-1">
                                <div className="text-xs font-medium text-red-800">
                                  {t('processing.realtime.recoveryActions')}:
                                </div>
                                {task.error.suggestedActions.map((action, index) => (
                                  <Button
                                    key={index}
                                    variant="outline"
                                    size="sm"
                                    className="mr-2 mb-1"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      action.action()
                                    }}
                                  >
                                    {action.label}
                                  </Button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Additional Details */}
                        <div className="mt-4 grid grid-cols-2 gap-4 text-xs text-muted-foreground">
                          <div>
                            <span className="font-medium">
                              {t('processing.realtime.bytesProcessed')}:
                            </span>
                            <br />
                            {formatBytes(task.processedBytes)} / {formatBytes(task.fileSize)}
                          </div>
                          <div>
                            <span className="font-medium">
                              {t('processing.realtime.retryCount')}:
                            </span>
                            <br />
                            {task.retryCount} / {task.maxRetries}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Empty State */}
      {tasks.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center">
            <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">
              {t('workspace.processing.noTasks')}
            </h3>
            <p className="text-muted-foreground">
              {t('workspace.processing.noTasksDescription')}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default ProcessingProgress