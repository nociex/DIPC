'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { TaskUpdate, ProcessingTask } from '@/types/processing'
import { 
  liveUpdatesService, 
  ConnectionStatus, 
  ConnectionStatusUpdate,
  TaskUpdateCallback,
  BatchUpdateCallback 
} from '@/lib/live-updates-service'

export interface UseLiveUpdatesOptions {
  autoConnect?: boolean
  enableBatching?: boolean
  onConnectionChange?: (status: ConnectionStatusUpdate) => void
}

export interface UseLiveUpdatesReturn {
  connectionStatus: ConnectionStatus
  isConnected: boolean
  lastUpdate: Date | null
  connect: () => Promise<void>
  disconnect: () => void
  subscribe: (taskId: string, callback: TaskUpdateCallback) => () => void
  subscribeToAll: (callback: BatchUpdateCallback) => () => void
}

export function useLiveUpdates(options: UseLiveUpdatesOptions = {}): UseLiveUpdatesReturn {
  const {
    autoConnect = true,
    onConnectionChange
  } = options

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const onConnectionChangeRef = useRef(onConnectionChange)

  // Update ref when callback changes
  useEffect(() => {
    onConnectionChangeRef.current = onConnectionChange
  }, [onConnectionChange])

  // Subscribe to connection status changes
  useEffect(() => {
    const unsubscribe = liveUpdatesService.subscribeToConnectionStatus((status) => {
      setConnectionStatus(status.status)
      onConnectionChangeRef.current?.(status)
    })

    return unsubscribe
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      liveUpdatesService.connect().catch(console.error)
    }

    // Cleanup on unmount
    return () => {
      if (autoConnect) {
        liveUpdatesService.disconnect()
      }
    }
  }, [autoConnect])

  const connect = useCallback(async () => {
    await liveUpdatesService.connect()
  }, [])

  const disconnect = useCallback(() => {
    liveUpdatesService.disconnect()
  }, [])

  const subscribe = useCallback((taskId: string, callback: TaskUpdateCallback) => {
    const wrappedCallback: TaskUpdateCallback = (update) => {
      setLastUpdate(new Date())
      callback(update)
    }
    
    return liveUpdatesService.subscribe(taskId, wrappedCallback)
  }, [])

  const subscribeToAll = useCallback((callback: BatchUpdateCallback) => {
    const wrappedCallback: BatchUpdateCallback = (updates) => {
      setLastUpdate(new Date())
      callback(updates)
    }
    
    return liveUpdatesService.subscribeToAll(wrappedCallback)
  }, [])

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    lastUpdate,
    connect,
    disconnect,
    subscribe,
    subscribeToAll
  }
}

export interface UseTaskUpdatesOptions {
  taskId: string
  onUpdate?: (update: TaskUpdate) => void
  autoSubscribe?: boolean
}

export interface UseTaskUpdatesReturn {
  lastUpdate: TaskUpdate | null
  subscribe: () => () => void
  unsubscribe: () => void
}

export function useTaskUpdates(options: UseTaskUpdatesOptions): UseTaskUpdatesReturn {
  const { taskId, onUpdate, autoSubscribe = true } = options
  const [lastUpdate, setLastUpdate] = useState<TaskUpdate | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)
  const onUpdateRef = useRef(onUpdate)

  // Update ref when callback changes
  useEffect(() => {
    onUpdateRef.current = onUpdate
  }, [onUpdate])

  const subscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current()
    }

    const unsubscribe = liveUpdatesService.subscribe(taskId, (update) => {
      setLastUpdate(update)
      onUpdateRef.current?.(update)
    })

    unsubscribeRef.current = unsubscribe
    return unsubscribe
  }, [taskId])

  const unsubscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current()
      unsubscribeRef.current = null
    }
  }, [])

  // Auto-subscribe/unsubscribe
  useEffect(() => {
    if (autoSubscribe) {
      subscribe()
    }

    return () => {
      unsubscribe()
    }
  }, [taskId, autoSubscribe, subscribe, unsubscribe])

  return {
    lastUpdate,
    subscribe,
    unsubscribe
  }
}

export interface UseProcessingTasksOptions {
  initialTasks?: ProcessingTask[]
  onTaskUpdate?: (taskId: string, update: TaskUpdate) => void
  onBatchUpdate?: (updates: TaskUpdate[]) => void
}

export interface UseProcessingTasksReturn {
  tasks: ProcessingTask[]
  updateTask: (taskId: string, updates: Partial<ProcessingTask>) => void
  addTask: (task: ProcessingTask) => void
  removeTask: (taskId: string) => void
  clearTasks: () => void
  subscribeToTask: (taskId: string) => () => void
  subscribeToAllTasks: () => () => void
}

export function useProcessingTasks(options: UseProcessingTasksOptions = {}): UseProcessingTasksReturn {
  const { initialTasks = [], onTaskUpdate, onBatchUpdate } = options
  const [tasks, setTasks] = useState<ProcessingTask[]>(initialTasks)
  const onTaskUpdateRef = useRef(onTaskUpdate)
  const onBatchUpdateRef = useRef(onBatchUpdate)

  // Update refs when callbacks change
  useEffect(() => {
    onTaskUpdateRef.current = onTaskUpdate
    onBatchUpdateRef.current = onBatchUpdate
  }, [onTaskUpdate, onBatchUpdate])

  const updateTask = useCallback((taskId: string, updates: Partial<ProcessingTask>) => {
    setTasks(prevTasks => 
      prevTasks.map(task => 
        task.id === taskId ? { ...task, ...updates } : task
      )
    )
  }, [])

  const addTask = useCallback((task: ProcessingTask) => {
    setTasks(prevTasks => {
      const existingIndex = prevTasks.findIndex(t => t.id === task.id)
      if (existingIndex >= 0) {
        // Update existing task
        const newTasks = [...prevTasks]
        newTasks[existingIndex] = task
        return newTasks
      } else {
        // Add new task
        return [...prevTasks, task]
      }
    })
  }, [])

  const removeTask = useCallback((taskId: string) => {
    setTasks(prevTasks => prevTasks.filter(task => task.id !== taskId))
  }, [])

  const clearTasks = useCallback(() => {
    setTasks([])
  }, [])

  const subscribeToTask = useCallback((taskId: string) => {
    return liveUpdatesService.subscribe(taskId, (update) => {
      // Update the task with the new information
      updateTask(taskId, {
        status: update.status,
        progress: update.progress,
        currentStep: update.currentStep,
        currentStepIndex: update.currentStepIndex,
        estimatedTimeRemaining: update.estimatedTimeRemaining,
        throughput: update.throughput,
        processedBytes: update.processedBytes,
        error: update.error,
        lastUpdate: update.timestamp
      })

      onTaskUpdateRef.current?.(taskId, update)
    })
  }, [updateTask])

  const subscribeToAllTasks = useCallback(() => {
    return liveUpdatesService.subscribeToAll((updates) => {
      // Process batch updates
      const taskUpdates = new Map<string, Partial<ProcessingTask>>()
      
      updates.forEach(update => {
        taskUpdates.set(update.taskId, {
          status: update.status,
          progress: update.progress,
          currentStep: update.currentStep,
          currentStepIndex: update.currentStepIndex,
          estimatedTimeRemaining: update.estimatedTimeRemaining,
          throughput: update.throughput,
          processedBytes: update.processedBytes,
          error: update.error,
          lastUpdate: update.timestamp
        })
      })

      // Apply all updates at once
      setTasks(prevTasks => 
        prevTasks.map(task => {
          const update = taskUpdates.get(task.id)
          return update ? { ...task, ...update } : task
        })
      )

      onBatchUpdateRef.current?.(updates)
    })
  }, [])

  return {
    tasks,
    updateTask,
    addTask,
    removeTask,
    clearTasks,
    subscribeToTask,
    subscribeToAllTasks
  }
}