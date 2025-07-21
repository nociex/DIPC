'use client'

import React, { useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence, Reorder } from 'framer-motion'
import {
  Clock,
  ArrowUp,
  ArrowDown,
  Play,
  Pause,
  Square,
  MoreHorizontal,
  BarChart3,
  Users,
  Timer,
  DollarSign,
  CheckSquare,
  XSquare,
  RotateCcw,
  GripVertical
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useI18n } from '@/lib/i18n/context'
import { ProcessingTask, TaskAction, ProcessingQueue, ProcessingQueueItem } from '@/types/processing'
import { TaskStatus } from '@/types'

export interface ProcessingQueueProps {
  queue: ProcessingQueue
  onTaskAction: (taskId: string, action: TaskAction) => void
  onReorderQueue: (newOrder: string[]) => void
  onBulkAction: (taskIds: string[], action: TaskAction) => void
  selectedTasks?: string[]
  onTaskSelection?: (taskIds: string[]) => void
  showStatistics?: boolean
}

const ProcessingQueueManager: React.FC<ProcessingQueueProps> = ({
  queue,
  onTaskAction,
  onReorderQueue,
  onBulkAction,
  selectedTasks = [],
  onTaskSelection,
  showStatistics = true
}) => {
  const { t } = useI18n()
  const [bulkSelectMode, setBulkSelectMode] = useState(false)

  // Calculate queue statistics
  const queueStats = useMemo(() => {
    const totalTasks = queue.items.length
    const activeTasks = queue.items.filter(item => 
      item.task.status === TaskStatus.PROCESSING
    ).length
    const pendingTasks = queue.items.filter(item => 
      item.task.status === TaskStatus.PENDING
    ).length
    const completedTasks = queue.items.filter(item => 
      item.task.status === TaskStatus.COMPLETED
    ).length
    const failedTasks = queue.items.filter(item => 
      item.task.status === TaskStatus.FAILED
    ).length

    const totalEstimatedCost = queue.items.reduce((sum, item) => 
      sum + item.task.estimatedCost, 0
    )
    
    const averageWaitTime = queue.averageWaitTime
    const utilizationRate = queue.activeSlots / queue.maxConcurrentTasks * 100

    return {
      totalTasks,
      activeTasks,
      pendingTasks,
      completedTasks,
      failedTasks,
      totalEstimatedCost,
      averageWaitTime,
      utilizationRate
    }
  }, [queue])

  const handleTaskSelection = useCallback((taskId: string, selected: boolean) => {
    if (!onTaskSelection) return

    const newSelection = selected
      ? [...selectedTasks, taskId]
      : selectedTasks.filter(id => id !== taskId)
    
    onTaskSelection(newSelection)
  }, [selectedTasks, onTaskSelection])

  const handleSelectAll = useCallback((selected: boolean) => {
    if (!onTaskSelection) return

    const newSelection = selected
      ? queue.items.map(item => item.task.id)
      : []
    
    onTaskSelection(newSelection)
  }, [queue.items, onTaskSelection])

  const handleReorder = useCallback((newItems: ProcessingQueueItem[]) => {
    const newOrder = newItems.map(item => item.task.id)
    onReorderQueue(newOrder)
  }, [onReorderQueue])

  const handleBulkAction = useCallback((action: TaskAction) => {
    if (selectedTasks.length === 0) return
    onBulkAction(selectedTasks, action)
    setBulkSelectMode(false)
    onTaskSelection?.([])
  }, [selectedTasks, onBulkAction, onTaskSelection])

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

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'normal':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'low':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
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

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.PROCESSING:
        return <Play className="h-4 w-4 text-blue-500" />
      case TaskStatus.COMPLETED:
        return <CheckSquare className="h-4 w-4 text-green-500" />
      case TaskStatus.FAILED:
        return <XSquare className="h-4 w-4 text-red-500" />
      case TaskStatus.CANCELLED:
        return <Square className="h-4 w-4 text-gray-500" />
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Queue Statistics */}
      {showStatistics && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold">
                {t('processing.queue.title')}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="flex items-center gap-1">
                  <BarChart3 className="h-3 w-3" />
                  {Math.round(queueStats.utilizationRate)}% Utilization
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {queue.activeSlots}/{queue.maxConcurrentTasks} Active
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Statistics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {queueStats.activeTasks}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t('processing.realtime.activeTasks')}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {queueStats.pendingTasks}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t('processing.realtime.queuedTasks')}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {queueStats.completedTasks}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t('processing.realtime.completedTasks')}
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {queueStats.failedTasks}
                </div>
                <div className="text-sm text-muted-foreground">
                  {t('processing.realtime.failedTasks')}
                </div>
              </div>
            </div>

            {/* Additional Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Timer className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {t('processing.realtime.averageTime')}:
                </span>
                <span className="font-medium">
                  {formatDuration(queueStats.averageWaitTime)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  {t('processing.realtime.totalCost')}:
                </span>
                <span className="font-medium">
                  ${queueStats.totalEstimatedCost.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">
                  Queue Efficiency:
                </span>
                <span className="font-medium">
                  {Math.round(queueStats.utilizationRate)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bulk Actions */}
      {onTaskSelection && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={selectedTasks.length === queue.items.length && queue.items.length > 0}
                    onCheckedChange={handleSelectAll}
                  />
                  <span className="text-sm">
                    Select All ({selectedTasks.length} selected)
                  </span>
                </div>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setBulkSelectMode(!bulkSelectMode)}
                >
                  Bulk Actions
                </Button>
              </div>

              {bulkSelectMode && selectedTasks.length > 0 && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBulkAction({ type: 'pause' })}
                  >
                    <Pause className="h-3 w-3 mr-1" />
                    Pause
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBulkAction({ type: 'resume' })}
                  >
                    <Play className="h-3 w-3 mr-1" />
                    Resume
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBulkAction({ type: 'cancel' })}
                  >
                    <Square className="h-3 w-3 mr-1" />
                    Cancel
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleBulkAction({ type: 'retry' })}
                  >
                    <RotateCcw className="h-3 w-3 mr-1" />
                    Retry
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Queue Items */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Processing Queue ({queue.items.length} items)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {queue.items.length === 0 ? (
            <div className="p-8 text-center">
              <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">
                Queue is Empty
              </h3>
              <p className="text-muted-foreground">
                No tasks in the processing queue
              </p>
            </div>
          ) : (
            <Reorder.Group
              axis="y"
              values={queue.items}
              onReorder={handleReorder}
              className="space-y-0"
            >
              <AnimatePresence>
                {queue.items.map((item, index) => (
                  <Reorder.Item
                    key={item.task.id}
                    value={item}
                    className="border-b last:border-b-0"
                  >
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="p-4 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        {/* Drag Handle */}
                        <div className="cursor-grab active:cursor-grabbing">
                          <GripVertical className="h-4 w-4 text-muted-foreground" />
                        </div>

                        {/* Selection Checkbox */}
                        {onTaskSelection && (
                          <Checkbox
                            checked={selectedTasks.includes(item.task.id)}
                            onCheckedChange={(checked) => 
                              handleTaskSelection(item.task.id, checked as boolean)
                            }
                          />
                        )}

                        {/* Queue Position */}
                        <div className="text-sm font-mono text-muted-foreground min-w-[2rem]">
                          #{item.queuePosition}
                        </div>

                        {/* Task Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-2">
                            {getStatusIcon(item.task.status)}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-sm truncate">
                                {item.task.fileName}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {formatBytes(item.task.fileSize)} • 
                                {getStatusLabel(item.task.status)}
                              </div>
                            </div>
                          </div>

                          {/* Progress Bar */}
                          {item.task.status === TaskStatus.PROCESSING && (
                            <div className="mb-2">
                              <Progress value={item.task.progress} className="h-1" />
                            </div>
                          )}
                        </div>

                        {/* Priority Badge */}
                        <Badge 
                          variant="outline" 
                          className={getPriorityColor(item.task.options.priority)}
                        >
                          {getPriorityLabel(item.task.options.priority)}
                        </Badge>

                        {/* Time Info */}
                        <div className="text-right text-xs text-muted-foreground min-w-[6rem]">
                          {item.task.status === TaskStatus.PENDING && (
                            <div>
                              <div>ETA: {formatDuration(
                                (item.estimatedStartTime.getTime() - Date.now()) / 1000
                              )}</div>
                              <div>${item.task.estimatedCost.toFixed(2)}</div>
                            </div>
                          )}
                          {item.task.status === TaskStatus.PROCESSING && (
                            <div>
                              <div>Remaining: {formatDuration(item.task.estimatedTimeRemaining)}</div>
                              <div>${item.task.estimatedCost.toFixed(2)}</div>
                            </div>
                          )}
                          {item.task.status === TaskStatus.COMPLETED && (
                            <div>
                              <div>Completed</div>
                              <div>${(item.task.actualCost || item.task.estimatedCost).toFixed(2)}</div>
                            </div>
                          )}
                          {item.task.status === TaskStatus.FAILED && (
                            <div>
                              <div>Failed</div>
                              <div>${item.task.estimatedCost.toFixed(2)}</div>
                            </div>
                          )}
                        </div>

                        {/* Priority Controls */}
                        <div className="flex flex-col gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onTaskAction(item.task.id, { type: 'priority_up' })}
                            disabled={index === 0}
                          >
                            <ArrowUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onTaskAction(item.task.id, { type: 'priority_down' })}
                            disabled={index === queue.items.length - 1}
                          >
                            <ArrowDown className="h-3 w-3" />
                          </Button>
                        </div>

                        {/* Actions Menu */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {item.task.status === TaskStatus.PENDING && (
                              <>
                                <DropdownMenuItem
                                  onClick={() => onTaskAction(item.task.id, { type: 'pause' })}
                                >
                                  <Pause className="h-3 w-3 mr-2" />
                                  {t('processing.realtime.pauseTask')}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => onTaskAction(item.task.id, { type: 'cancel' })}
                                >
                                  <Square className="h-3 w-3 mr-2" />
                                  {t('processing.realtime.cancelTask')}
                                </DropdownMenuItem>
                              </>
                            )}
                            
                            {item.task.status === TaskStatus.PROCESSING && (
                              <>
                                <DropdownMenuItem
                                  onClick={() => onTaskAction(item.task.id, { type: 'pause' })}
                                >
                                  <Pause className="h-3 w-3 mr-2" />
                                  {t('processing.realtime.pauseTask')}
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={() => onTaskAction(item.task.id, { type: 'cancel' })}
                                >
                                  <Square className="h-3 w-3 mr-2" />
                                  {t('processing.realtime.cancelTask')}
                                </DropdownMenuItem>
                              </>
                            )}
                            
                            {item.task.status === TaskStatus.FAILED && (
                              <DropdownMenuItem
                                onClick={() => onTaskAction(item.task.id, { type: 'retry' })}
                              >
                                <RotateCcw className="h-3 w-3 mr-2" />
                                {t('processing.realtime.retryTask')}
                              </DropdownMenuItem>
                            )}
                            
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => onTaskAction(item.task.id, { type: 'priority_up' })}
                              disabled={index === 0}
                            >
                              <ArrowUp className="h-3 w-3 mr-2" />
                              {t('processing.realtime.increasePriority')}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => onTaskAction(item.task.id, { type: 'priority_down' })}
                              disabled={index === queue.items.length - 1}
                            >
                              <ArrowDown className="h-3 w-3 mr-2" />
                              {t('processing.realtime.decreasePriority')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </motion.div>
                  </Reorder.Item>
                ))}
              </AnimatePresence>
            </Reorder.Group>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ProcessingQueueManager