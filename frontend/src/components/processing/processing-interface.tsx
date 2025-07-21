'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Settings, BarChart3, List, Activity } from 'lucide-react'
import { useI18n } from '@/lib/i18n/context'
import { useLiveUpdates, useProcessingTasks } from '@/hooks/use-live-updates'
import ProcessingProgress from './processing-progress'
import ProcessingQueueManager from './processing-queue'
import ConnectionStatusIndicator, { FloatingConnectionStatus } from './connection-status'
import { ProcessingTask, TaskAction, ProcessingQueue, ProcessingQueueItem } from '@/types/processing'
import { TaskStatus } from '@/types'

export interface ProcessingInterfaceProps {
    initialTasks?: ProcessingTask[]
    onTaskAction?: (taskId: string, action: TaskAction) => void
    onQueueReorder?: (newOrder: string[]) => void
    onBulkAction?: (taskIds: string[], action: TaskAction) => void
    className?: string
}

const ProcessingInterface: React.FC<ProcessingInterfaceProps> = ({
    initialTasks = [],
    onTaskAction,
    onQueueReorder,
    onBulkAction,
    className = ''
}) => {
    const { t } = useI18n()
    const [activeTab, setActiveTab] = useState<'progress' | 'queue' | 'analytics'>('progress')
    const [showDetailedProgress, setShowDetailedProgress] = useState(false)
    const [selectedTasks, setSelectedTasks] = useState<string[]>([])
    const [selectedTaskId, setSelectedTaskId] = useState<string>()

    // Live updates integration
    const {
        connectionStatus,
        isConnected,
        lastUpdate,
        connect,
        disconnect,
        subscribeToAll
    } = useLiveUpdates({
        autoConnect: true,
        onConnectionChange: (status) => {
            console.log('Connection status changed:', status)
        }
    })

    // Processing tasks management
    const {
        tasks,
        updateTask,
        addTask,
        removeTask,
        clearTasks,
        subscribeToAllTasks
    } = useProcessingTasks({
        initialTasks,
        onTaskUpdate: (taskId, update) => {
            console.log('Task updated:', taskId, update)
        },
        onBatchUpdate: (updates) => {
            console.log('Batch update received:', updates.length, 'updates')
        }
    })

    // Subscribe to live updates
    useEffect(() => {
        const unsubscribe = subscribeToAllTasks()
        return unsubscribe
    }, [subscribeToAllTasks])

    // Create processing queue from tasks
    const processingQueue: ProcessingQueue = React.useMemo(() => {
        const queueItems: ProcessingQueueItem[] = tasks
            .map((task, index) => ({
                task,
                priority: getPriorityValue(task.options.priority),
                queuePosition: index + 1,
                estimatedStartTime: new Date(Date.now() + (index * 30000)) // 30 seconds per position
            }))
            .sort((a, b) => {
                // Sort by priority first, then by queue position
                if (a.priority !== b.priority) {
                    return b.priority - a.priority // Higher priority first
                }
                return a.queuePosition - b.queuePosition
            })

        const activeTasks = tasks.filter(task => task.status === TaskStatus.PROCESSING).length
        const maxConcurrentTasks = 3 // This could be configurable

        return {
            items: queueItems,
            totalItems: queueItems.length,
            activeSlots: activeTasks,
            maxConcurrentTasks,
            averageWaitTime: calculateAverageWaitTime(queueItems)
        }
    }, [tasks])

    const getPriorityValue = (priority: string): number => {
        switch (priority) {
            case 'high': return 3
            case 'normal': return 2
            case 'low': return 1
            default: return 2
        }
    }

    const calculateAverageWaitTime = (items: ProcessingQueueItem[]): number => {
        const pendingItems = items.filter(item => item.task.status === TaskStatus.PENDING)
        if (pendingItems.length === 0) return 0

        const totalWaitTime = pendingItems.reduce((sum, item) => {
            const waitTime = (item.estimatedStartTime.getTime() - Date.now()) / 1000
            return sum + Math.max(0, waitTime)
        }, 0)

        return totalWaitTime / pendingItems.length
    }

    const handleTaskAction = useCallback((taskId: string, action: TaskAction) => {
        // Handle local state updates
        const task = tasks.find(t => t.id === taskId)
        if (!task) return

        switch (action.type) {
            case 'cancel':
                updateTask(taskId, { status: TaskStatus.CANCELLED })
                break
            case 'retry':
                updateTask(taskId, {
                    status: TaskStatus.PENDING,
                    progress: 0,
                    retryCount: task.retryCount + 1,
                    error: undefined
                })
                break
            case 'pause':
                // This would typically be handled by the backend
                console.log('Pause task:', taskId)
                break
            case 'resume':
                // This would typically be handled by the backend
                console.log('Resume task:', taskId)
                break
            case 'priority_up':
                // Reorder queue by increasing priority
                console.log('Increase priority for task:', taskId)
                break
            case 'priority_down':
                // Reorder queue by decreasing priority
                console.log('Decrease priority for task:', taskId)
                break
        }

        // Call external handler
        onTaskAction?.(taskId, action)
    }, [tasks, updateTask, onTaskAction])

    const handleQueueReorder = useCallback((newOrder: string[]) => {
        // This would typically update the backend queue order
        console.log('Reorder queue:', newOrder)
        onQueueReorder?.(newOrder)
    }, [onQueueReorder])

    const handleBulkAction = useCallback((taskIds: string[], action: TaskAction) => {
        // Apply action to multiple tasks
        taskIds.forEach(taskId => {
            handleTaskAction(taskId, action)
        })

        onBulkAction?.(taskIds, action)
    }, [handleTaskAction, onBulkAction])

    const handleReconnect = useCallback(() => {
        connect().catch(console.error)
    }, [connect])

    // Calculate tab badges
    const activeTasksCount = tasks.filter(task =>
        task.status === TaskStatus.PROCESSING || task.status === TaskStatus.PENDING
    ).length

    const queuedTasksCount = tasks.filter(task =>
        task.status === TaskStatus.PENDING
    ).length

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Floating Connection Status */}
            <FloatingConnectionStatus
                status={connectionStatus}
                onReconnect={handleReconnect}
            />

            {/* Header with Connection Status */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <h2 className="text-xl font-semibold">
                                {t('processing.realtime.title')}
                            </h2>
                            <ConnectionStatusIndicator
                                status={connectionStatus}
                                onReconnect={handleReconnect}
                                showDetails={false}
                            />
                        </div>

                        <div className="flex items-center gap-2">
                            <Badge variant="outline" className="flex items-center gap-1">
                                <Activity className="h-3 w-3" />
                                {activeTasksCount} Active
                            </Badge>

                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleReconnect}
                                disabled={isConnected}
                            >
                                <RefreshCw className="h-4 w-4 mr-1" />
                                Refresh
                            </Button>

                            <Button variant="outline" size="sm">
                                <Settings className="h-4 w-4 mr-1" />
                                Settings
                            </Button>
                        </div>
                    </div>

                    {lastUpdate && (
                        <div className="text-xs text-muted-foreground mt-2">
                            Last update: {lastUpdate.toLocaleTimeString()}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Main Interface Tabs */}
            <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)}>
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="progress" className="flex items-center gap-2">
                        <Activity className="h-4 w-4" />
                        Progress
                        {activeTasksCount > 0 && (
                            <Badge variant="secondary" className="ml-1">
                                {activeTasksCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="queue" className="flex items-center gap-2">
                        <List className="h-4 w-4" />
                        Queue
                        {queuedTasksCount > 0 && (
                            <Badge variant="secondary" className="ml-1">
                                {queuedTasksCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="analytics" className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" />
                        Analytics
                    </TabsTrigger>
                </TabsList>

                <AnimatePresence mode="wait">
                    <TabsContent value="progress" className="mt-6">
                        <motion.div
                            key="progress"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.2 }}
                        >
                            <ProcessingProgress
                                tasks={tasks}
                                showDetailedProgress={showDetailedProgress}
                                onToggleDetails={() => setShowDetailedProgress(!showDetailedProgress)}
                                onTaskAction={handleTaskAction}
                                onTaskSelect={setSelectedTaskId}
                                selectedTaskId={selectedTaskId}
                            />
                        </motion.div>
                    </TabsContent>

                    <TabsContent value="queue" className="mt-6">
                        <motion.div
                            key="queue"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.2 }}
                        >
                            <ProcessingQueueManager
                                queue={processingQueue}
                                onTaskAction={handleTaskAction}
                                onReorderQueue={handleQueueReorder}
                                onBulkAction={handleBulkAction}
                                selectedTasks={selectedTasks}
                                onTaskSelection={setSelectedTasks}
                                showStatistics={true}
                            />
                        </motion.div>
                    </TabsContent>

                    <TabsContent value="analytics" className="mt-6">
                        <motion.div
                            key="analytics"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.2 }}
                        >
                            <Card>
                                <CardContent className="p-8 text-center">
                                    <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                    <h3 className="text-lg font-medium mb-2">
                                        Analytics Dashboard
                                    </h3>
                                    <p className="text-muted-foreground">
                                        Detailed processing analytics and insights coming soon
                                    </p>
                                </CardContent>
                            </Card>
                        </motion.div>
                    </TabsContent>
                </AnimatePresence>
            </Tabs>
        </div>
    )
}

export default ProcessingInterface