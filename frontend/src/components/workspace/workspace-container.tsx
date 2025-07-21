"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n/context'
import { useToast } from '@/components/ui/use-toast'
import { useResponsive } from '@/hooks/use-responsive'
import { useAccessibility, useAnnouncements } from '@/hooks/use-accessibility'
import { api } from '@/lib/api'
import type { Task, TaskOptions, TaskCreateRequest } from '@/types'
import { TaskStatus, StoragePolicy } from '@/types'

// Workspace view types
export type WorkspaceView = 'empty' | 'uploading' | 'processing' | 'results'

// File upload interface
export interface FileWithPreview extends File {
  preview?: string
  uploadProgress?: number
  uploadStatus?: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

// Responsive state interface
export interface ResponsiveState {
  deviceType: 'mobile' | 'tablet' | 'desktop'
  isSmallScreen: boolean
  isTouchDevice: boolean
  orientation: 'portrait' | 'landscape'
}

// Workspace state interface
export interface WorkspaceState {
  currentView: WorkspaceView
  files: FileWithPreview[]
  tasks: Task[]
  selectedTask?: Task
  sidebarCollapsed: boolean
  isUploading: boolean
  taskOptions: TaskOptions
  responsive?: ResponsiveState
}

// Keyboard shortcuts
const KEYBOARD_SHORTCUTS = {
  TOGGLE_SIDEBAR: 'b',
  UPLOAD_FILES: 'u',
  REFRESH_TASKS: 'r',
  ESCAPE: 'Escape'
} as const

interface WorkspaceContainerProps {
  children: React.ReactNode
  className?: string
}

export function WorkspaceContainer({ children, className }: WorkspaceContainerProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const responsive = useResponsive()
  const { AriaLiveRegion, SkipLink } = useAccessibility()
  const { announceNavigation, announceAction, announceError, announceSuccess } = useAnnouncements()

  // Workspace state with responsive defaults
  const [state, setState] = useState<WorkspaceState>({
    currentView: 'empty',
    files: [],
    tasks: [],
    selectedTask: undefined,
    sidebarCollapsed: responsive.isSmallScreen, // Auto-collapse on mobile
    isUploading: false,
    taskOptions: {
      enable_vectorization: true,
      storage_policy: StoragePolicy.TEMPORARY,
      max_cost_limit: 1.0,
      llm_provider: 'openai'
    }
  })

  // Auto-collapse sidebar on mobile
  useEffect(() => {
    if (responsive.isSmallScreen && !state.sidebarCollapsed) {
      setState(prev => ({ ...prev, sidebarCollapsed: true }))
    }
  }, [responsive.isSmallScreen, state.sidebarCollapsed])

  // Load tasks on mount
  useEffect(() => {
    loadTasks()
  }, [])

  // Keyboard navigation support
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle shortcuts when not in input fields
      if (event.target instanceof HTMLInputElement || 
          event.target instanceof HTMLTextAreaElement) {
        return
      }

      // Handle Ctrl/Cmd + key combinations
      if (event.ctrlKey || event.metaKey) {
        switch (event.key.toLowerCase()) {
          case KEYBOARD_SHORTCUTS.TOGGLE_SIDEBAR:
            event.preventDefault()
            toggleSidebar()
            break
          case KEYBOARD_SHORTCUTS.UPLOAD_FILES:
            event.preventDefault()
            // Focus file input or trigger upload
            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
            fileInput?.click()
            break
          case KEYBOARD_SHORTCUTS.REFRESH_TASKS:
            event.preventDefault()
            loadTasks()
            break
        }
      }

      // Handle escape key
      if (event.key === KEYBOARD_SHORTCUTS.ESCAPE) {
        if (state.selectedTask) {
          setState(prev => ({ ...prev, selectedTask: undefined, currentView: 'empty' }))
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [state.selectedTask])

  // Load tasks from API
  const loadTasks = useCallback(async () => {
    try {
      const userId = 'demo-user'
      const response = await api.listTasks(userId)
      setState(prev => ({ ...prev, tasks: response.tasks }))
      
      // Update view based on tasks
      if (response.tasks.length > 0) {
        const hasProcessing = response.tasks.some(task => 
          task.status === TaskStatus.PENDING || task.status === TaskStatus.PROCESSING
        )
        setState(prev => {
          if (hasProcessing && prev.currentView === 'empty') {
            return { ...prev, currentView: 'processing' }
          }
          return { ...prev, tasks: response.tasks }
        })
      } else {
        setState(prev => ({ ...prev, tasks: response.tasks }))
      }
    } catch (error) {
      console.error('Failed to load tasks:', error)
      toast({
        title: t('notification.error.network'),
        description: "Could not retrieve task list from server",
        variant: "destructive",
      })
    }
  }, [t, toast])

  // Toggle sidebar
  const toggleSidebar = useCallback(() => {
    setState(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed }))
  }, [])

  // Handle file selection
  const handleFilesSelected = useCallback((files: FileWithPreview[]) => {
    setState(prev => ({ 
      ...prev, 
      files,
      currentView: files.length > 0 ? 'uploading' : 'empty'
    }))
  }, [])

  // Handle file upload
  const uploadFiles = useCallback(async () => {
    if (state.files.length === 0) {
      toast({
        title: t('upload.error.noFiles'),
        description: "Please select files to upload",
        variant: "destructive",
      })
      return
    }

    setState(prev => ({ ...prev, isUploading: true, currentView: 'uploading' }))
    const uploadedFileUrls: string[] = []

    try {
      // Upload each file
      for (let i = 0; i < state.files.length; i++) {
        const file = state.files[i]
        
        // Update file status to uploading
        setState(prev => ({
          ...prev,
          files: prev.files.map((f, index) => 
            index === i ? { ...f, uploadStatus: 'uploading' as const, uploadProgress: 0 } : f
          )
        }))

        try {
          // Get presigned URL
          const presignedResponse = await api.getPresignedUrl({
            filename: file.name,
            file_type: file.type,
            file_size: file.size
          })

          // Upload file with progress tracking
          await api.uploadFile(file, presignedResponse.upload_url, (progress) => {
            setState(prev => ({
              ...prev,
              files: prev.files.map((f, index) => 
                index === i ? { ...f, uploadProgress: progress } : f
              )
            }))
          })

          // Mark as completed
          setState(prev => ({
            ...prev,
            files: prev.files.map((f, index) => 
              index === i ? { ...f, uploadStatus: 'completed' as const, uploadProgress: 100 } : f
            )
          }))

          uploadedFileUrls.push(presignedResponse.file_url)

        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          setState(prev => ({
            ...prev,
            files: prev.files.map((f, index) => 
              index === i ? { 
                ...f, 
                uploadStatus: 'error' as const, 
                error: error instanceof Error ? error.message : 'Upload failed'
              } : f
            )
          }))
        }
      }

      if (uploadedFileUrls.length > 0) {
        // Create processing task
        const taskRequest: TaskCreateRequest = {
          file_urls: uploadedFileUrls,
          user_id: 'demo-user',
          options: state.taskOptions
        }

        await api.createTask(taskRequest)
        
        toast({
          title: t('notification.success.upload'),
          description: `${uploadedFileUrls.length} files uploaded and processing started`,
        })

        // Switch to processing view and refresh tasks
        setState(prev => ({ 
          ...prev, 
          currentView: 'processing',
          files: [] // Clear files after successful upload
        }))
        await loadTasks()
      }

    } catch (error) {
      console.error('Upload process failed:', error)
      toast({
        title: t('notification.error.upload'),
        description: error instanceof Error ? error.message : "Failed to process files",
        variant: "destructive",
      })
    } finally {
      setState(prev => ({ ...prev, isUploading: false }))
    }
  }, [state.files, state.taskOptions, t, toast, loadTasks])

  // Handle task selection
  const handleTaskSelect = useCallback((task: Task) => {
    setState(prev => ({ 
      ...prev, 
      selectedTask: task,
      currentView: 'results'
    }))
  }, [])

  // Handle view change
  const handleViewChange = useCallback((view: WorkspaceView) => {
    setState(prev => ({ ...prev, currentView: view }))
  }, [])

  // Update task options
  const updateTaskOptions = useCallback((options: TaskOptions) => {
    setState(prev => ({ ...prev, taskOptions: options }))
  }, [])

  return (
    <>
      {/* Skip Links for Accessibility */}
      <SkipLink href="#main-content">
        {t('accessibility.skipToMain')}
      </SkipLink>
      <SkipLink href="#sidebar">
        {t('accessibility.skipToSidebar')}
      </SkipLink>
      
      <div 
        className={cn(
          "flex h-screen bg-background overflow-hidden",
          // Mobile-specific layout adjustments
          responsive.isSmallScreen && "flex-col",
          // Touch-friendly spacing
          responsive.isTouchDevice && "touch-manipulation",
          className
        )}
        role="application"
        aria-label={t('workspace.main')}
        // Mobile viewport meta handling
        style={{
          minHeight: responsive.isSmallScreen ? '100vh' : 'auto',
          // Prevent zoom on input focus for iOS
          fontSize: responsive.deviceType === 'mobile' ? '16px' : 'inherit'
        }}
      >
        {/* Workspace context provider with responsive data */}
        <WorkspaceContext.Provider value={{
          state: {
            ...state,
            // Add responsive state to context
            responsive: {
              deviceType: responsive.deviceType,
              isSmallScreen: responsive.isSmallScreen,
              isTouchDevice: responsive.isTouchDevice,
              orientation: responsive.orientation
            }
          },
          actions: {
            toggleSidebar,
            handleFilesSelected,
            uploadFiles,
            handleTaskSelect,
            handleViewChange,
            updateTaskOptions,
            loadTasks
          }
        }}>
          {children}
        </WorkspaceContext.Provider>
        
        {/* ARIA Live Region for Announcements */}
        <AriaLiveRegion />
      </div>
    </>
  )
}

// Workspace context for sharing state and actions
export interface WorkspaceContextValue {
  state: WorkspaceState
  actions: {
    toggleSidebar: () => void
    handleFilesSelected: (files: FileWithPreview[]) => void
    uploadFiles: () => Promise<void>
    handleTaskSelect: (task: Task) => void
    handleViewChange: (view: WorkspaceView) => void
    updateTaskOptions: (options: TaskOptions) => void
    loadTasks: () => Promise<void>
  }
}

export const WorkspaceContext = React.createContext<WorkspaceContextValue | null>(null)

// Hook to use workspace context
export function useWorkspace() {
  const context = React.useContext(WorkspaceContext)
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceContainer')
  }
  return context
}