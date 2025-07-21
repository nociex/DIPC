"use client"

import React, { useState, useMemo, useRef } from 'react'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n/context'
import { useResponsive } from '@/hooks/use-responsive'
import { useFocusManagement, useAnnouncements } from '@/hooks/use-accessibility'
import { useWorkspace } from './workspace-container'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { 
  ChevronLeft, 
  ChevronRight, 
  ChevronDown, 
  ChevronUp,
  File, 
  FileText, 
  Image, 
  Archive,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  MoreHorizontal,
  Trash2,
  Download,
  Eye
} from 'lucide-react'
import { TaskStatus } from '@/types'
import type { Task } from '@/types'
import type { FileWithPreview } from './workspace-container'

// File type icons mapping
const FILE_TYPE_ICONS = {
  'application/pdf': FileText,
  'application/msword': FileText,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileText,
  'text/plain': FileText,
  'image/jpeg': Image,
  'image/png': Image,
  'image/gif': Image,
  'application/zip': Archive,
  'application/x-zip-compressed': Archive,
  default: File
} as const

// Task status colors and icons
const TASK_STATUS_CONFIG = {
  [TaskStatus.PENDING]: {
    color: 'bg-yellow-500',
    icon: Clock,
    label: 'processing.status.pending'
  },
  [TaskStatus.PROCESSING]: {
    color: 'bg-blue-500',
    icon: Clock,
    label: 'processing.status.inProgress'
  },
  [TaskStatus.COMPLETED]: {
    color: 'bg-green-500',
    icon: CheckCircle,
    label: 'processing.status.completed'
  },
  [TaskStatus.FAILED]: {
    color: 'bg-red-500',
    icon: XCircle,
    label: 'processing.status.failed'
  },
  [TaskStatus.CANCELLED]: {
    color: 'bg-gray-500',
    icon: XCircle,
    label: 'processing.status.cancelled'
  }
} as const

interface WorkspaceSidebarProps {
  className?: string
}

export function WorkspaceSidebar({ className }: WorkspaceSidebarProps) {
  const { t } = useTranslation()
  const responsive = useResponsive()
  const { state, actions } = useWorkspace()
  const [filesExpanded, setFilesExpanded] = useState(!responsive.isSmallScreen)
  const [tasksExpanded, setTasksExpanded] = useState(!responsive.isSmallScreen)
  
  // Accessibility hooks
  const sidebarRef = useRef<HTMLDivElement>(null)
  const { handleKeyDown } = useFocusManagement(sidebarRef)
  const { announceNavigation, announceAction } = useAnnouncements()

  // Group tasks by status
  const groupedTasks = useMemo(() => {
    const groups = {
      active: state.tasks.filter(task => 
        task.status === TaskStatus.PENDING || task.status === TaskStatus.PROCESSING
      ),
      completed: state.tasks.filter(task => task.status === TaskStatus.COMPLETED),
      failed: state.tasks.filter(task => task.status === TaskStatus.FAILED)
    }
    return groups
  }, [state.tasks])

  // Calculate overall progress for active tasks
  const overallProgress = useMemo(() => {
    if (groupedTasks.active.length === 0) return 0
    // For demo purposes, we'll simulate progress based on task age
    const now = Date.now()
    const avgProgress = groupedTasks.active.reduce((acc, task) => {
      const taskAge = now - new Date(task.created_at).getTime()
      const estimatedProgress = Math.min(90, (taskAge / (5 * 60 * 1000)) * 100) // 5 minutes to 90%
      return acc + estimatedProgress
    }, 0) / groupedTasks.active.length
    return Math.round(avgProgress)
  }, [groupedTasks.active])

  // Handle file drag start for reordering
  const handleFileDragStart = (event: React.DragEvent, index: number) => {
    event.dataTransfer.setData('text/plain', index.toString())
    event.dataTransfer.effectAllowed = 'move'
  }

  // Handle file drop for reordering
  const handleFileDrop = (event: React.DragEvent, dropIndex: number) => {
    event.preventDefault()
    const dragIndex = parseInt(event.dataTransfer.getData('text/plain'))
    
    if (dragIndex !== dropIndex) {
      const newFiles = [...state.files]
      const [draggedFile] = newFiles.splice(dragIndex, 1)
      newFiles.splice(dropIndex, 0, draggedFile)
      actions.handleFilesSelected(newFiles)
    }
  }

  // Handle file drag over
  const handleFileDragOver = (event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }

  // Get file type icon
  const getFileIcon = (file: FileWithPreview) => {
    const IconComponent = FILE_TYPE_ICONS[file.type as keyof typeof FILE_TYPE_ICONS] || FILE_TYPE_ICONS.default
    return IconComponent
  }

  // Get file thumbnail if available
  const getFileThumbnail = (file: FileWithPreview) => {
    if (file.preview) {
      return (
        <img 
          src={file.preview} 
          alt={file.name}
          className="w-8 h-8 object-cover rounded"
        />
      )
    }
    
    const IconComponent = getFileIcon(file)
    return <IconComponent className="w-8 h-8 text-muted-foreground" />
  }

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  // Format task duration
  const formatTaskDuration = (task: Task) => {
    const start = new Date(task.created_at)
    const end = task.completed_at ? new Date(task.completed_at) : new Date()
    const duration = end.getTime() - start.getTime()
    const minutes = Math.floor(duration / 60000)
    const seconds = Math.floor((duration % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  if (state.sidebarCollapsed) {
    return (
      <div className={cn(
        "border-r bg-muted/30 flex items-center py-4",
        // Mobile: horizontal collapsed bar at bottom
        responsive.isSmallScreen ? "w-full h-16 flex-row justify-center space-x-4 border-t border-r-0" : "w-12 flex-col",
        className
      )}>
        <Button
          variant="ghost"
          size={responsive.isSmallScreen ? "default" : "sm"}
          onClick={actions.toggleSidebar}
          className={cn(
            responsive.isSmallScreen ? "h-12 px-4" : "mb-4",
            // Touch-friendly sizing
            responsive.isTouchDevice && "min-h-[44px] min-w-[44px]"
          )}
          aria-label={t('workspace.sidebar.expand')}
        >
          <ChevronRight className={cn(
            responsive.isSmallScreen ? "h-5 w-5" : "h-4 w-4"
          )} />
          {responsive.isSmallScreen && (
            <span className="ml-2">{t('workspace.sidebar.show')}</span>
          )}
        </Button>
        
        {/* Collapsed indicators */}
        {state.files.length > 0 && (
          <div className={cn(
            "rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium",
            responsive.isSmallScreen ? "w-10 h-10" : "w-8 h-8 mb-2"
          )}>
            {state.files.length}
          </div>
        )}
        
        {groupedTasks.active.length > 0 && (
          <div className={cn(
            "rounded-full bg-blue-500 text-white flex items-center justify-center text-xs font-medium",
            responsive.isSmallScreen ? "w-10 h-10" : "w-8 h-8"
          )}>
            {groupedTasks.active.length}
          </div>
        )}
      </div>
    )
  }

  return (
    <aside 
      ref={sidebarRef}
      id="sidebar"
      className={cn(
        "border-r bg-muted/30 flex flex-col",
        // Responsive width
        responsive.isSmallScreen ? "w-full" : responsive.isMediumScreen ? "w-72" : "w-80",
        // Mobile: full height overlay
        responsive.isSmallScreen && "fixed inset-0 z-50 bg-background",
        className
      )}
      role="complementary"
      aria-label={t('workspace.sidebar.title')}
      onKeyDown={handleKeyDown}
    >
      {/* Mobile overlay backdrop */}
      {responsive.isSmallScreen && (
        <div 
          className="absolute inset-0 bg-black/20 backdrop-blur-sm"
          onClick={() => {
            actions.toggleSidebar()
            announceAction(t('workspace.sidebar.collapsed'))
          }}
          aria-label={t('workspace.sidebar.closeOverlay')}
        />
      )}
      
      {/* Sidebar content */}
      <div className={cn(
        "relative bg-background border-r flex flex-col",
        responsive.isSmallScreen ? "w-80 h-full shadow-xl" : "w-full h-full"
      )}>
        {/* Sidebar Header */}
        <header className={cn(
          "border-b flex items-center justify-between",
          responsive.isSmallScreen ? "p-6" : "p-4"
        )}>
          <h2 
            id="sidebar-title"
            className={cn(
              "font-semibold text-muted-foreground uppercase tracking-wide",
              responsive.isSmallScreen ? "text-base" : "text-sm"
            )}
          >
            {t('workspace.sidebar.title')}
          </h2>
          <Button
            variant="ghost"
            size={responsive.isSmallScreen ? "default" : "sm"}
            onClick={() => {
              actions.toggleSidebar()
              announceAction(t('workspace.sidebar.collapsed'))
            }}
            className={cn(
              responsive.isTouchDevice && "min-h-[44px] min-w-[44px]"
            )}
            aria-label={t('workspace.sidebar.collapse')}
            aria-describedby="sidebar-title"
          >
            <ChevronLeft className={cn(
              responsive.isSmallScreen ? "h-5 w-5" : "h-4 w-4"
            )} />
          </Button>
        </header>

        <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Files Section */}
          <Collapsible open={filesExpanded} onOpenChange={setFilesExpanded}>
            <CollapsibleTrigger asChild>
              <Button 
                variant="ghost" 
                className="w-full justify-between p-0 h-auto"
                aria-expanded={filesExpanded}
                aria-controls="files-section"
                onClick={() => {
                  setFilesExpanded(!filesExpanded)
                  announceAction(filesExpanded ? t('workspace.sidebar.filesCollapsed') : t('workspace.sidebar.filesExpanded'))
                }}
              >
                <div className="flex items-center space-x-2">
                  <h3 
                    id="files-heading"
                    className="font-medium text-sm"
                  >
                    {t('workspace.sidebar.files')}
                  </h3>
                  {state.files.length > 0 && (
                    <Badge 
                      variant="secondary" 
                      className="text-xs"
                      aria-label={t('workspace.sidebar.fileCount', { count: state.files.length })}
                    >
                      {state.files.length}
                    </Badge>
                  )}
                </div>
                {filesExpanded ? (
                  <ChevronUp className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
            </CollapsibleTrigger>
            
            <CollapsibleContent 
              className="space-y-2 mt-3"
              id="files-section"
              role="region"
              aria-labelledby="files-heading"
            >
              {state.files.length === 0 ? (
                <div 
                  className="text-center py-8 text-muted-foreground"
                  role="status"
                  aria-live="polite"
                >
                  <File className="h-8 w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                  <p className="text-sm">{t('workspace.sidebar.noFiles')}</p>
                </div>
              ) : (
                state.files.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    draggable
                    onDragStart={(e) => handleFileDragStart(e, index)}
                    onDrop={(e) => handleFileDrop(e, index)}
                    onDragOver={handleFileDragOver}
                    className={cn(
                      "flex items-center space-x-3 p-3 rounded-lg border bg-background cursor-move hover:bg-muted/50 transition-colors",
                      file.uploadStatus === 'error' && "border-red-200 bg-red-50/50",
                      file.uploadStatus === 'completed' && "border-green-200 bg-green-50/50"
                    )}
                  >
                    {/* File thumbnail/icon */}
                    <div className="flex-shrink-0">
                      {getFileThumbnail(file)}
                    </div>
                    
                    {/* File info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </p>
                      
                      {/* Upload progress */}
                      {file.uploadStatus === 'uploading' && (
                        <div className="mt-2">
                          <Progress value={file.uploadProgress || 0} className="h-1" />
                          <p className="text-xs text-muted-foreground mt-1">
                            {file.uploadProgress || 0}%
                          </p>
                        </div>
                      )}
                      
                      {/* Error message */}
                      {file.uploadStatus === 'error' && file.error && (
                        <p className="text-xs text-red-600 mt-1">{file.error}</p>
                      )}
                    </div>
                    
                    {/* Status indicator */}
                    <div className="flex-shrink-0">
                      {file.uploadStatus === 'completed' && (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      )}
                      {file.uploadStatus === 'error' && (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                      {file.uploadStatus === 'uploading' && (
                        <Clock className="h-4 w-4 text-blue-600 animate-spin" />
                      )}
                    </div>
                  </div>
                ))
              )}
            </CollapsibleContent>
          </Collapsible>

          <Separator />

          {/* Tasks Section */}
          <Collapsible open={tasksExpanded} onOpenChange={setTasksExpanded}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <div className="flex items-center space-x-2">
                  <h3 className="font-medium text-sm">
                    {t('workspace.sidebar.tasks')}
                  </h3>
                  {state.tasks.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {state.tasks.length}
                    </Badge>
                  )}
                </div>
                {tasksExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            
            <CollapsibleContent className="space-y-4 mt-3">
              {/* Overall progress for active tasks */}
              {groupedTasks.active.length > 0 && (
                <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-900">
                      {t('workspace.sidebar.processing')}
                    </span>
                    <span className="text-xs text-blue-700">
                      {groupedTasks.active.length} {t('workspace.sidebar.active')}
                    </span>
                  </div>
                  <Progress value={overallProgress} className="h-2" />
                  <p className="text-xs text-blue-700 mt-1">
                    {overallProgress}% {t('workspace.sidebar.complete')}
                  </p>
                </div>
              )}

              {/* Task list */}
              {state.tasks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">{t('workspace.sidebar.noTasks')}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Active tasks */}
                  {groupedTasks.active.map((task) => (
                    <TaskItem
                      key={task.id}
                      task={task}
                      onSelect={() => actions.handleTaskSelect(task)}
                      isSelected={state.selectedTask?.id === task.id}
                    />
                  ))}
                  
                  {/* Completed tasks */}
                  {groupedTasks.completed.map((task) => (
                    <TaskItem
                      key={task.id}
                      task={task}
                      onSelect={() => actions.handleTaskSelect(task)}
                      isSelected={state.selectedTask?.id === task.id}
                    />
                  ))}
                  
                  {/* Failed tasks */}
                  {groupedTasks.failed.map((task) => (
                    <TaskItem
                      key={task.id}
                      task={task}
                      onSelect={() => actions.handleTaskSelect(task)}
                      isSelected={state.selectedTask?.id === task.id}
                    />
                  ))}
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        </div>
      </ScrollArea>
      </div>
    </aside>
  )
}

// Task item component
interface TaskItemProps {
  task: Task
  onSelect: () => void
  isSelected: boolean
}

function TaskItem({ task, onSelect, isSelected }: TaskItemProps) {
  const { t } = useTranslation()
  const statusConfig = TASK_STATUS_CONFIG[task.status]
  const StatusIcon = statusConfig.icon

  return (
    <div
      className={cn(
        "flex items-center space-x-3 p-3 rounded-lg border bg-background cursor-pointer hover:bg-muted/50 transition-colors",
        isSelected && "ring-2 ring-primary ring-offset-2"
      )}
      onClick={onSelect}
    >
      {/* Status indicator */}
      <div className="flex-shrink-0">
        <div className={cn("w-2 h-2 rounded-full", statusConfig.color)} />
      </div>
      
      {/* Task info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">
          {t('workspace.sidebar.task')} {task.id.slice(0, 8)}
        </p>
        <div className="flex items-center space-x-2 mt-1">
          <StatusIcon className="h-3 w-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">
            {t(statusConfig.label)}
          </span>
          <span className="text-xs text-muted-foreground">
            • {formatTaskDuration(task)}
          </span>
        </div>
      </div>
      
      {/* Action buttons */}
      <div className="flex-shrink-0 flex items-center space-x-1">
        {task.status === TaskStatus.COMPLETED && (
          <>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Eye className="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Download className="h-3 w-3" />
            </Button>
          </>
        )}
        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
          <MoreHorizontal className="h-3 w-3" />
        </Button>
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