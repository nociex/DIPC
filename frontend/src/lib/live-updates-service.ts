/**
 * Live Updates Service
 * Provides real-time updates for processing tasks using WebSocket with polling fallback
 */

import { TaskUpdate, ProcessingTask } from '@/types/processing'
import { TaskStatus } from '@/types'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting'

export interface LiveUpdatesConfig {
  websocketUrl?: string
  pollingInterval?: number
  maxReconnectAttempts?: number
  reconnectDelay?: number
  batchUpdateInterval?: number
  enableBatching?: boolean
}

export interface ConnectionStatusUpdate {
  status: ConnectionStatus
  error?: string
  reconnectAttempt?: number
  lastConnected?: Date
}

export type TaskUpdateCallback = (update: TaskUpdate) => void
export type BatchUpdateCallback = (updates: TaskUpdate[]) => void
export type ConnectionStatusCallback = (status: ConnectionStatusUpdate) => void

class LiveUpdatesService {
  private websocket: WebSocket | null = null
  private pollingInterval: NodeJS.Timeout | null = null
  private batchInterval: NodeJS.Timeout | null = null
  private config: Required<LiveUpdatesConfig>
  private connectionStatus: ConnectionStatus = 'disconnected'
  private reconnectAttempts = 0
  private lastConnected: Date | null = null
  
  // Callback management
  private taskCallbacks = new Map<string, Set<TaskUpdateCallback>>()
  private batchCallbacks = new Set<BatchUpdateCallback>()
  private statusCallbacks = new Set<ConnectionStatusCallback>()
  
  // Batching
  private pendingUpdates: TaskUpdate[] = []
  private subscribedTasks = new Set<string>()
  
  // Polling state
  private isPolling = false
  private lastPollingUpdate = new Date()

  constructor(config: LiveUpdatesConfig = {}) {
    this.config = {
      websocketUrl: config.websocketUrl || this.getWebSocketUrl(),
      pollingInterval: config.pollingInterval || 2000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      reconnectDelay: config.reconnectDelay || 1000,
      batchUpdateInterval: config.batchUpdateInterval || 500,
      enableBatching: config.enableBatching ?? true
    }

    // Start batch processing if enabled
    if (this.config.enableBatching) {
      this.startBatchProcessing()
    }

    // Handle page visibility changes
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this))
    }

    // Handle online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.handleOnline.bind(this))
      window.addEventListener('offline', this.handleOffline.bind(this))
    }
  }

  private getWebSocketUrl(): string {
    if (typeof window === 'undefined') return ''
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = process.env.NEXT_PUBLIC_WS_URL || window.location.host
    return `${protocol}//${host}/ws/tasks`
  }

  // Connection Management
  async connect(): Promise<void> {
    if (this.connectionStatus === 'connected' || this.connectionStatus === 'connecting') {
      return
    }

    this.setConnectionStatus('connecting')

    try {
      await this.connectWebSocket()
    } catch (error) {
      console.warn('WebSocket connection failed, falling back to polling:', error)
      this.startPolling()
    }
  }

  private async connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.websocket = new WebSocket(this.config.websocketUrl)
        
        this.websocket.onopen = () => {
          this.setConnectionStatus('connected')
          this.reconnectAttempts = 0
          this.lastConnected = new Date()
          
          // Subscribe to all tracked tasks
          this.subscribedTasks.forEach(taskId => {
            this.sendWebSocketMessage({ type: 'subscribe', taskId })
          })
          
          resolve()
        }

        this.websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.handleWebSocketMessage(data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.websocket.onclose = (event) => {
          this.websocket = null
          
          if (event.wasClean) {
            this.setConnectionStatus('disconnected')
          } else {
            this.handleConnectionLoss()
          }
        }

        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.setConnectionStatus('error', 'WebSocket connection error')
          reject(error)
        }

        // Connection timeout
        setTimeout(() => {
          if (this.websocket?.readyState === WebSocket.CONNECTING) {
            this.websocket.close()
            reject(new Error('WebSocket connection timeout'))
          }
        }, 10000)

      } catch (error) {
        reject(error)
      }
    })
  }

  private handleWebSocketMessage(data: any): void {
    if (data.type === 'task_update' && data.update) {
      const update: TaskUpdate = {
        ...data.update,
        timestamp: new Date(data.update.timestamp)
      }
      this.processTaskUpdate(update)
    } else if (data.type === 'batch_update' && data.updates) {
      const updates: TaskUpdate[] = data.updates.map((update: any) => ({
        ...update,
        timestamp: new Date(update.timestamp)
      }))
      this.processBatchUpdate(updates)
    } else if (data.type === 'connection_status') {
      // Handle server-side connection status updates
      console.log('Server connection status:', data.status)
    }
  }

  private sendWebSocketMessage(message: any): void {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify(message))
    }
  }

  private handleConnectionLoss(): void {
    if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.setConnectionStatus('reconnecting', undefined, this.reconnectAttempts + 1)
      
      setTimeout(() => {
        this.reconnectAttempts++
        this.connectWebSocket().catch(() => {
          if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached, falling back to polling')
            this.startPolling()
          }
        })
      }, this.config.reconnectDelay * Math.pow(2, this.reconnectAttempts))
    } else {
      console.log('WebSocket reconnection failed, falling back to polling')
      this.startPolling()
    }
  }

  // Polling Fallback
  private startPolling(): void {
    if (this.isPolling) return

    this.isPolling = true
    this.setConnectionStatus('connected') // Consider polling as connected
    
    this.pollingInterval = setInterval(async () => {
      try {
        await this.pollForUpdates()
      } catch (error) {
        console.error('Polling error:', error)
        this.setConnectionStatus('error', 'Polling failed')
      }
    }, this.config.pollingInterval)
  }

  private async pollForUpdates(): Promise<void> {
    if (this.subscribedTasks.size === 0) return

    try {
      // Poll for updates from all subscribed tasks
      const taskIds = Array.from(this.subscribedTasks)
      const response = await fetch('/api/v1/tasks/updates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_ids: taskIds,
          since: this.lastPollingUpdate.toISOString()
        })
      })

      if (!response.ok) {
        throw new Error(`Polling failed: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.updates && data.updates.length > 0) {
        const updates: TaskUpdate[] = data.updates.map((update: any) => ({
          ...update,
          timestamp: new Date(update.timestamp)
        }))
        
        this.processBatchUpdate(updates)
        this.lastPollingUpdate = new Date()
      }
    } catch (error) {
      throw error
    }
  }

  private stopPolling(): void {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval)
      this.pollingInterval = null
    }
    this.isPolling = false
  }

  // Subscription Management
  subscribe(taskId: string, callback: TaskUpdateCallback): () => void {
    if (!this.taskCallbacks.has(taskId)) {
      this.taskCallbacks.set(taskId, new Set())
    }
    
    this.taskCallbacks.get(taskId)!.add(callback)
    this.subscribedTasks.add(taskId)

    // Subscribe via WebSocket if connected
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.sendWebSocketMessage({ type: 'subscribe', taskId })
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.taskCallbacks.get(taskId)
      if (callbacks) {
        callbacks.delete(callback)
        if (callbacks.size === 0) {
          this.taskCallbacks.delete(taskId)
          this.subscribedTasks.delete(taskId)
          
          // Unsubscribe via WebSocket if connected
          if (this.websocket?.readyState === WebSocket.OPEN) {
            this.sendWebSocketMessage({ type: 'unsubscribe', taskId })
          }
        }
      }
    }
  }

  subscribeToAll(callback: BatchUpdateCallback): () => void {
    this.batchCallbacks.add(callback)
    
    return () => {
      this.batchCallbacks.delete(callback)
    }
  }

  subscribeToConnectionStatus(callback: ConnectionStatusCallback): () => void {
    this.statusCallbacks.add(callback)
    
    // Immediately call with current status
    callback({
      status: this.connectionStatus,
      lastConnected: this.lastConnected || undefined,
      reconnectAttempt: this.reconnectAttempts > 0 ? this.reconnectAttempts : undefined
    })
    
    return () => {
      this.statusCallbacks.delete(callback)
    }
  }

  // Update Processing
  private processTaskUpdate(update: TaskUpdate): void {
    if (this.config.enableBatching) {
      this.pendingUpdates.push(update)
    } else {
      this.deliverTaskUpdate(update)
    }
  }

  private processBatchUpdate(updates: TaskUpdate[]): void {
    if (this.config.enableBatching) {
      this.pendingUpdates.push(...updates)
    } else {
      updates.forEach(update => this.deliverTaskUpdate(update))
      this.deliverBatchUpdate(updates)
    }
  }

  private deliverTaskUpdate(update: TaskUpdate): void {
    const callbacks = this.taskCallbacks.get(update.taskId)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(update)
        } catch (error) {
          console.error('Error in task update callback:', error)
        }
      })
    }
  }

  private deliverBatchUpdate(updates: TaskUpdate[]): void {
    this.batchCallbacks.forEach(callback => {
      try {
        callback(updates)
      } catch (error) {
        console.error('Error in batch update callback:', error)
      }
    })
  }

  private startBatchProcessing(): void {
    this.batchInterval = setInterval(() => {
      if (this.pendingUpdates.length > 0) {
        const updates = [...this.pendingUpdates]
        this.pendingUpdates = []
        
        // Group updates by task ID and deliver individual updates
        const taskUpdates = new Map<string, TaskUpdate>()
        updates.forEach(update => {
          taskUpdates.set(update.taskId, update)
        })
        
        taskUpdates.forEach(update => this.deliverTaskUpdate(update))
        
        // Deliver batch update
        this.deliverBatchUpdate(updates)
      }
    }, this.config.batchUpdateInterval)
  }

  // Status Management
  private setConnectionStatus(
    status: ConnectionStatus, 
    error?: string, 
    reconnectAttempt?: number
  ): void {
    this.connectionStatus = status
    
    const statusUpdate: ConnectionStatusUpdate = {
      status,
      error,
      reconnectAttempt,
      lastConnected: this.lastConnected || undefined
    }
    
    this.statusCallbacks.forEach(callback => {
      try {
        callback(statusUpdate)
      } catch (error) {
        console.error('Error in connection status callback:', error)
      }
    })
  }

  // Utility Methods
  async getTaskStatus(taskId: string): Promise<{ status: TaskStatus; progress?: number }> {
    try {
      const response = await fetch(`/api/v1/tasks/${taskId}/status`)
      if (!response.ok) {
        throw new Error(`Failed to get task status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Failed to get task status:', error)
      throw error
    }
  }

  isConnected(): boolean {
    return this.connectionStatus === 'connected'
  }

  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus
  }

  // Event Handlers
  private handleVisibilityChange(): void {
    if (document.hidden) {
      // Page is hidden, reduce update frequency
      if (this.isPolling) {
        this.stopPolling()
        setTimeout(() => {
          if (document.hidden) {
            this.startPolling()
          }
        }, 5000) // Resume with longer interval when hidden
      }
    } else {
      // Page is visible, resume normal operation
      if (!this.isConnected() && !this.isPolling) {
        this.connect()
      }
    }
  }

  private handleOnline(): void {
    console.log('Network connection restored')
    if (!this.isConnected()) {
      this.connect()
    }
  }

  private handleOffline(): void {
    console.log('Network connection lost')
    this.setConnectionStatus('disconnected', 'Network offline')
  }

  // Cleanup
  disconnect(): void {
    if (this.websocket) {
      this.websocket.close()
      this.websocket = null
    }
    
    this.stopPolling()
    
    if (this.batchInterval) {
      clearInterval(this.batchInterval)
      this.batchInterval = null
    }
    
    this.setConnectionStatus('disconnected')
    
    // Clear all callbacks
    this.taskCallbacks.clear()
    this.batchCallbacks.clear()
    this.statusCallbacks.clear()
    this.subscribedTasks.clear()
    this.pendingUpdates = []
  }

  destroy(): void {
    this.disconnect()
    
    // Remove event listeners
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this))
    }
    
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.handleOnline.bind(this))
      window.removeEventListener('offline', this.handleOffline.bind(this))
    }
  }
}

// Create singleton instance
export const liveUpdatesService = new LiveUpdatesService()

// Export the service class for custom instances
export { LiveUpdatesService }

// Hook for React components
export function useLiveUpdates() {
  return {
    service: liveUpdatesService,
    subscribe: liveUpdatesService.subscribe.bind(liveUpdatesService),
    subscribeToAll: liveUpdatesService.subscribeToAll.bind(liveUpdatesService),
    subscribeToConnectionStatus: liveUpdatesService.subscribeToConnectionStatus.bind(liveUpdatesService),
    connect: liveUpdatesService.connect.bind(liveUpdatesService),
    disconnect: liveUpdatesService.disconnect.bind(liveUpdatesService),
    isConnected: liveUpdatesService.isConnected.bind(liveUpdatesService),
    getConnectionStatus: liveUpdatesService.getConnectionStatus.bind(liveUpdatesService)
  }
}