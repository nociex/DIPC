"use client"

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { TaskStatusChecker } from '@/lib/task-status-checker'
import { MarkdownEditorContainer } from '@/components/markdown/markdown-editor-container'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ErrorDisplay } from '@/components/error/error-display'
import { ErrorBoundary } from '@/components/error/error-boundary'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Edit3 } from 'lucide-react'
import type { Task } from '@/types'

interface MarkdownEditorPageState {
  task: Task | null
  loading: boolean
  error: string | null
  retryCount: number
}

export default function MarkdownEditorPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.taskId as string
  const hasUnsavedChangesRef = useRef(false)
  const isNavigatingRef = useRef(false)

  const [state, setState] = useState<MarkdownEditorPageState>({
    task: null,
    loading: true,
    error: null,
    retryCount: 0
  })

  // Handle page refresh and data re-fetching
  const loadTask = useCallback(async (showLoading = true) => {
    if (!taskId) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Invalid task ID'
      }))
      return
    }

    try {
      if (showLoading) {
        setState(prev => ({ ...prev, loading: true, error: null }))
      }
      
      const task = await api.getTask(taskId)
      
      // Validate task can be edited as markdown
      const statusCheck = TaskStatusChecker.canEditAsMarkdown(task)
      if (!statusCheck.canEdit) {
        setState(prev => ({
          ...prev,
          loading: false,
          error: statusCheck.reason || 'Task cannot be edited as markdown',
          retryCount: prev.retryCount + 1
        }))
        return
      }

      setState(prev => ({
        ...prev,
        task,
        loading: false,
        error: null,
        retryCount: 0
      }))
    } catch (error) {
      console.error('Failed to load task:', error)
      
      // Determine error message based on error type
      let errorMessage = 'Failed to load task'
      if (error instanceof Error) {
        if (error.message.includes('404') || error.message.includes('not found')) {
          errorMessage = 'Task not found'
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Network error - please check your connection'
        } else {
          errorMessage = error.message
        }
      }
      
      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
        retryCount: prev.retryCount + 1
      }))
    }
  }, [taskId])

  // Handle navigation with unsaved changes check
  const handleBack = useCallback(() => {
    if (hasUnsavedChangesRef.current && !isNavigatingRef.current) {
      const shouldLeave = window.confirm(
        '您有未保存的更改，确定要离开吗？\n\n点击"确定"离开页面，点击"取消"继续编辑。'
      )
      if (!shouldLeave) {
        return
      }
    }
    
    isNavigatingRef.current = true
    router.push(`/results/${taskId}`)
  }, [router, taskId])

  // Handle retry with exponential backoff
  const handleRetry = useCallback(() => {
    const delay = Math.min(1000 * Math.pow(2, state.retryCount), 10000) // Max 10 seconds
    
    if (state.retryCount > 0) {
      setTimeout(() => {
        loadTask()
      }, delay)
    } else {
      loadTask()
    }
  }, [loadTask, state.retryCount])

  // Handle unsaved changes tracking
  const handleUnsavedChanges = useCallback((hasChanges: boolean) => {
    hasUnsavedChangesRef.current = hasChanges
  }, [])

  // Handle page visibility change (for data refresh when user returns to tab)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && state.task && !state.loading) {
        // Refresh data when user returns to tab (without showing loading)
        loadTask(false)
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [loadTask, state.task, state.loading])

  // Handle browser navigation (back/forward buttons)
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      if (hasUnsavedChangesRef.current) {
        const shouldLeave = window.confirm(
          '您有未保存的更改，确定要离开吗？\n\n点击"确定"离开页面，点击"取消"继续编辑。'
        )
        if (!shouldLeave) {
          // Push the current state back to prevent navigation
          window.history.pushState(null, '', window.location.href)
          return
        }
      }
      isNavigatingRef.current = true
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Handle page unload warning
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (hasUnsavedChangesRef.current && !isNavigatingRef.current) {
        event.preventDefault()
        event.returnValue = '您有未保存的更改，确定要离开吗？'
        return event.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [])

  // Initial load
  useEffect(() => {
    loadTask()
  }, [loadTask])

  // Error boundary error handler
  const handleError = useCallback((error: Error, errorInfo: any) => {
    console.error('Markdown Editor Error:', error, errorInfo)
    
    // You could send this to an error reporting service
    // errorReportingService.captureException(error, { extra: errorInfo })
  }, [])

  if (state.loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-sm border-border">
          <CardContent className="p-6 lg:p-8 text-center space-y-6">
            <div className="flex items-center justify-center space-x-3">
              <Edit3 className="h-6 w-6 text-primary" />
              <h2 className="text-lg lg:text-xl font-semibold text-foreground">Markdown编辑器</h2>
            </div>
            <div className="space-y-4">
              <LoadingSpinner message="正在加载任务数据..." />
              <div className="text-sm text-muted-foreground space-y-2">
                <p>正在获取任务数据并转换为Markdown格式...</p>
                {state.retryCount > 0 && (
                  <div className="flex items-center justify-center space-x-2">
                    <Badge variant="secondary" className="text-xs">
                      重试次数: {state.retryCount}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (state.error) {
    const isNetworkError = state.error.includes('network') || state.error.includes('fetch')
    const isNotFoundError = state.error.includes('not found') || state.error.includes('404')
    
    return (
      <ErrorDisplay
        title={isNotFoundError ? "任务未找到" : isNetworkError ? "网络连接错误" : "加载失败"}
        message={state.error}
        onRetry={!isNotFoundError ? handleRetry : undefined}
        onBack={handleBack}
        showDetails={process.env.NODE_ENV === 'development'}
        details={state.error}
        className="min-h-screen bg-background"
      />
    )
  }

  if (!state.task) {
    return (
      <ErrorDisplay
        title="任务未找到"
        message="请求的任务不存在或已被删除。"
        onBack={handleBack}
        className="min-h-screen bg-background"
      />
    )
  }

  return (
    <ErrorBoundary onError={handleError}>
      <MarkdownEditorContainer
        task={state.task}
        onBack={handleBack}
        onUnsavedChanges={handleUnsavedChanges}
      />
    </ErrorBoundary>
  )
}