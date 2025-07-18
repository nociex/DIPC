"use client"

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { ArrowLeft, Edit3, AlertTriangle, Eye, Copy, Download, Save, RotateCcw, ChevronDown, FileText, Globe, Wifi, WifiOff, Clock } from 'lucide-react'
import type { Task } from '@/types'
import { JsonToMarkdownConverter } from '@/lib/json-to-markdown'
import type { MarkdownEditorState, ConversionResult, LocalStorageData, EditHistoryEntry } from '@/lib/markdown-types'
import { ExportManager } from '@/lib/export-manager'
import { SplitView } from './split-view'
import { MarkdownEditor } from './markdown-editor'
import { MarkdownPreview } from './markdown-preview'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

interface MarkdownEditorContainerProps {
  task: Task
  onBack: () => void
  onUnsavedChanges?: (hasChanges: boolean) => void
}

export function MarkdownEditorContainer({ task, onBack, onUnsavedChanges }: MarkdownEditorContainerProps) {
  const { toast } = useToast()
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // State management
  const [editorState, setEditorState] = useState<MarkdownEditorState>({
    originalMarkdown: '',
    currentMarkdown: '',
    isEdited: false,
    editHistory: [],
    historyIndex: -1,
    isPreviewMode: false,
    isSplitView: true,
    lastSaved: null,
    autoSaveEnabled: true
  })
  
  const [isMobileView, setIsMobileView] = useState(false)
  
  const [conversionResult, setConversionResult] = useState<ConversionResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'offline'>('online')
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  // Format task type for display
  const formatTaskType = (taskType: string) => {
    return taskType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  // Initialize markdown content from task results
  const initializeMarkdown = useCallback(async () => {
    if (!task.results) {
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      
      // Convert JSON to markdown
      const result = JsonToMarkdownConverter.convert(task.results, {
        includeMetadata: true,
        maxDepth: 5,
        tableFormat: 'github',
        maxContentSize: 500 * 1024, // 500KB
        truncateThreshold: 400 * 1024 // 400KB
      })
      
      setConversionResult(result)
      
      // Check for saved content in localStorage directly
      let savedContent: string | null = null
      try {
        const stored = localStorage.getItem(`markdown-editor-${task.id}`)
        if (stored) {
          const data: LocalStorageData = JSON.parse(stored)
          // Check if the stored content is recent (within 24 hours)
          const isRecent = Date.now() - data.timestamp < 24 * 60 * 60 * 1000
          if (isRecent) {
            savedContent = data.content
          } else {
            // Clean up old data
            localStorage.removeItem(`markdown-editor-${task.id}`)
          }
        }
      } catch (error) {
        console.warn('Failed to load from localStorage:', error)
      }
      
      const initialMarkdown = savedContent || result.markdown
      
      const initialHistoryEntry: EditHistoryEntry = {
        content: initialMarkdown,
        timestamp: new Date(),
        operationType: savedContent ? 'import' : 'manual',
        description: savedContent ? '从本地存储恢复' : '初始内容',
        contentSize: initialMarkdown.length
      }
      
      setEditorState(prev => ({
        ...prev,
        originalMarkdown: result.markdown,
        currentMarkdown: initialMarkdown,
        isEdited: savedContent !== null,
        editHistory: [initialHistoryEntry],
        historyIndex: 0,
        lastSaved: savedContent ? new Date() : null
      }))
      
      setHasUnsavedChanges(savedContent !== null)
      
      // Show warnings if any
      if (result.warnings.length > 0) {
        result.warnings.forEach(warning => {
          toast({
            title: "内容处理提示",
            description: warning,
            variant: "default"
          })
        })
      }
      
    } catch (error) {
      console.error('Failed to convert JSON to markdown:', error)
      toast({
        title: "转换失败",
        description: "无法将结果转换为Markdown格式",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }, [task.results, task.id, toast])

  // Load content from localStorage
  const loadFromLocalStorage = useCallback((): string | null => {
    try {
      const stored = localStorage.getItem(`markdown-editor-${task.id}`)
      if (stored) {
        const data: LocalStorageData = JSON.parse(stored)
        // Check if the stored content is recent (within 24 hours)
        const isRecent = Date.now() - data.timestamp < 24 * 60 * 60 * 1000
        if (isRecent) {
          return data.content
        } else {
          // Clean up old data
          localStorage.removeItem(`markdown-editor-${task.id}`)
        }
      }
    } catch (error) {
      console.warn('Failed to load from localStorage:', error)
    }
    return null
  }, [task.id])

  // Save content to localStorage
  const saveToLocalStorage = useCallback((content: string) => {
    try {
      const data: LocalStorageData = {
        taskId: task.id,
        content,
        timestamp: Date.now(),
        version: '1.0'
      }
      localStorage.setItem(`markdown-editor-${task.id}`, JSON.stringify(data))
      
      setEditorState(prev => ({
        ...prev,
        lastSaved: new Date()
      }))
      
      setHasUnsavedChanges(false)
    } catch (error) {
      console.warn('Failed to save to localStorage:', error)
      toast({
        title: "自动保存失败",
        description: "无法保存到本地存储",
        variant: "destructive"
      })
    }
  }, [task.id, toast])

  // Auto-save functionality
  const scheduleAutoSave = useCallback((content: string) => {
    if (!editorState.autoSaveEnabled) return
    
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current)
    }
    
    autoSaveTimeoutRef.current = setTimeout(() => {
      saveToLocalStorage(content)
    }, 3000) // Auto-save after 3 seconds of inactivity
  }, [editorState.autoSaveEnabled, saveToLocalStorage])

  // Handle content change
  const handleContentChange = useCallback((newContent: string, operationType: 'manual' | 'paste' | 'format' = 'manual') => {
    setEditorState(prev => {
      const newHistory = prev.editHistory.slice(0, prev.historyIndex + 1)
      
      const newHistoryEntry: EditHistoryEntry = {
        content: newContent,
        timestamp: new Date(),
        operationType,
        contentSize: newContent.length
      }
      
      newHistory.push(newHistoryEntry)
      
      return {
        ...prev,
        currentMarkdown: newContent,
        isEdited: newContent !== prev.originalMarkdown,
        editHistory: newHistory.slice(-50), // Keep last 50 changes
        historyIndex: Math.min(newHistory.length - 1, 49)
      }
    })
    
    setHasUnsavedChanges(true)
    scheduleAutoSave(newContent)
  }, [scheduleAutoSave])

  // Undo functionality
  const handleUndo = useCallback(() => {
    setEditorState(prev => {
      if (prev.historyIndex > 0) {
        const newIndex = prev.historyIndex - 1
        const historyEntry = prev.editHistory[newIndex]
        const content = historyEntry.content
        setHasUnsavedChanges(content !== prev.originalMarkdown)
        scheduleAutoSave(content)
        
        // Create new history entry for undo action
        const undoEntry: EditHistoryEntry = {
          content,
          timestamp: new Date(),
          operationType: 'undo',
          description: `撤销到 ${historyEntry.timestamp.toLocaleTimeString()}`,
          contentSize: content.length
        }
        
        return {
          ...prev,
          currentMarkdown: content,
          historyIndex: newIndex,
          isEdited: content !== prev.originalMarkdown
        }
      }
      return prev
    })
  }, [scheduleAutoSave])

  // Redo functionality
  const handleRedo = useCallback(() => {
    setEditorState(prev => {
      if (prev.historyIndex < prev.editHistory.length - 1) {
        const newIndex = prev.historyIndex + 1
        const historyEntry = prev.editHistory[newIndex]
        const content = historyEntry.content
        setHasUnsavedChanges(content !== prev.originalMarkdown)
        scheduleAutoSave(content)
        
        // Create new history entry for redo action
        const redoEntry: EditHistoryEntry = {
          content,
          timestamp: new Date(),
          operationType: 'redo',
          description: `重做到 ${historyEntry.timestamp.toLocaleTimeString()}`,
          contentSize: content.length
        }
        
        return {
          ...prev,
          currentMarkdown: content,
          historyIndex: newIndex,
          isEdited: content !== prev.originalMarkdown
        }
      }
      return prev
    })
  }, [scheduleAutoSave])

  // Reset to original content
  const handleReset = useCallback(() => {
    setEditorState(prev => {
      const resetEntry: EditHistoryEntry = {
        content: prev.originalMarkdown,
        timestamp: new Date(),
        operationType: 'reset',
        description: '重置为原始内容',
        contentSize: prev.originalMarkdown.length
      }
      
      return {
        ...prev,
        currentMarkdown: prev.originalMarkdown,
        isEdited: false,
        editHistory: [resetEntry],
        historyIndex: 0
      }
    })
    setHasUnsavedChanges(false)
    
    // Clear localStorage
    localStorage.removeItem(`markdown-editor-${task.id}`)
    
    toast({
      title: "已重置",
      description: "内容已重置为原始版本",
      variant: "default"
    })
  }, [task.id, toast])

  // Manual save
  const handleManualSave = useCallback(() => {
    saveToLocalStorage(editorState.currentMarkdown)
    toast({
      title: "保存成功",
      description: "内容已保存到本地",
      variant: "default"
    })
  }, [editorState.currentMarkdown, saveToLocalStorage, toast])

  // Copy to clipboard using ExportManager
  const handleCopy = useCallback(async () => {
    try {
      await ExportManager.copyToClipboard(editorState.currentMarkdown)
      toast({
        title: "复制成功",
        description: "Markdown内容已复制到剪贴板",
        variant: "default"
      })
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      
      // Check if clipboard is supported and provide appropriate error message
      if (!ExportManager.isClipboardSupported()) {
        toast({
          title: "复制失败",
          description: "您的浏览器不支持剪贴板功能，请手动选择文本复制",
          variant: "destructive"
        })
      } else {
        toast({
          title: "复制失败",
          description: "无法复制到剪贴板，请手动选择文本复制",
          variant: "destructive"
        })
      }
    }
  }, [editorState.currentMarkdown, toast])

  // Export as markdown file using ExportManager
  const handleExportMarkdown = useCallback(async () => {
    try {
      const filename = ExportManager.generateFilename(task.id, 'markdown')
      await ExportManager.exportMarkdown(editorState.currentMarkdown, filename)
      
      toast({
        title: "导出成功",
        description: "Markdown文件已下载",
        variant: "default"
      })
    } catch (error) {
      console.error('Failed to export markdown:', error)
      toast({
        title: "导出失败",
        description: error instanceof Error ? error.message : "无法导出Markdown文件",
        variant: "destructive"
      })
    }
  }, [editorState.currentMarkdown, task.id, toast])

  // Export as HTML file using ExportManager
  const handleExportHtml = useCallback(async () => {
    try {
      const filename = ExportManager.generateFilename(task.id, 'html')
      await ExportManager.exportHtml(editorState.currentMarkdown, filename)
      
      toast({
        title: "导出成功",
        description: "HTML文件已下载",
        variant: "default"
      })
    } catch (error) {
      console.error('Failed to export HTML:', error)
      toast({
        title: "导出失败",
        description: error instanceof Error ? error.message : "无法导出HTML文件",
        variant: "destructive"
      })
    }
  }, [editorState.currentMarkdown, task.id, toast])

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'z':
          e.preventDefault()
          if (e.shiftKey) {
            handleRedo()
          } else {
            handleUndo()
          }
          break
        case 's':
          e.preventDefault()
          handleManualSave()
          break
      }
    }
  }, [handleUndo, handleRedo, handleManualSave])

  // Notify parent about unsaved changes
  useEffect(() => {
    if (onUnsavedChanges) {
      onUnsavedChanges(hasUnsavedChanges)
    }
  }, [hasUnsavedChanges, onUnsavedChanges])

  // Handle page unload warning (backup for when parent doesn't handle it)
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = '您有未保存的更改，确定要离开吗？'
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  // Initialize on mount and when task results change
  useEffect(() => {
    initializeMarkdown()
  }, [initializeMarkdown])

  // Handle connection status monitoring
  useEffect(() => {
    const handleOnline = () => {
      setConnectionStatus('online')
      setLastRefresh(new Date())
      
      // Refresh data when connection is restored if no unsaved changes
      if (!hasUnsavedChanges && !isLoading) {
        initializeMarkdown()
      }
      
      toast({
        title: "连接已恢复",
        description: "网络连接已恢复，数据已刷新",
        variant: "default"
      })
    }

    const handleOffline = () => {
      setConnectionStatus('offline')
      toast({
        title: "网络连接断开",
        description: "您的更改将保存在本地，连接恢复后会自动同步",
        variant: "destructive"
      })
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    // Set initial connection status
    setConnectionStatus(navigator.onLine ? 'online' : 'offline')
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [hasUnsavedChanges, isLoading, initializeMarkdown, toast])

  // Handle page focus/visibility change for data refresh
  useEffect(() => {
    const handleFocus = () => {
      // When user returns to the page, check if we need to refresh data
      // This is useful if the task was updated in another tab
      if (document.visibilityState === 'visible' && !isLoading && connectionStatus === 'online') {
        // Only refresh if we don't have unsaved changes
        if (!hasUnsavedChanges) {
          setLastRefresh(new Date())
          initializeMarkdown()
        }
      }
    }

    const handleVisibilityChange = () => {
      if (!document.hidden && !isLoading && !hasUnsavedChanges && connectionStatus === 'online') {
        // Refresh data when user returns to tab
        setLastRefresh(new Date())
        initializeMarkdown()
      }
    }

    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [initializeMarkdown, isLoading, hasUnsavedChanges, connectionStatus])

  // Handle responsive design
  useEffect(() => {
    const checkMobileView = () => {
      // Better responsive breakpoints
      // sm: 640px, md: 768px, lg: 1024px, xl: 1280px
      setIsMobileView(window.innerWidth < 768) // md breakpoint for tablet
    }
    
    checkMobileView()
    window.addEventListener('resize', checkMobileView)
    
    return () => window.removeEventListener('resize', checkMobileView)
  }, [])

  // Toggle view mode for mobile
  const toggleViewMode = useCallback(() => {
    setEditorState(prev => ({
      ...prev,
      isPreviewMode: !prev.isPreviewMode
    }))
  }, [])

  // Cleanup auto-save timeout on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current)
      }
    }
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">正在转换内容...</p>
        </div>
      </div>
    )
  }

  return (
    <TooltipProvider>
    <div className="min-h-screen bg-background" onKeyDown={handleKeyDown}>
      {/* Header */}
      <header className="border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-3 sm:px-4 py-2 sm:py-3 lg:py-4">
          <div className="flex items-center justify-between gap-2 sm:gap-4">
            <div className="flex items-center space-x-2 sm:space-x-3 lg:space-x-4 min-w-0 flex-1">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => {
                  if (hasUnsavedChanges) {
                    const shouldLeave = window.confirm(
                      '您有未保存的更改，确定要离开吗？\n\n点击"确定"返回结果页面，点击"取消"继续编辑。'
                    )
                    if (!shouldLeave) {
                      return
                    }
                  }
                  onBack()
                }}
                className="hover:bg-accent shrink-0 px-2 sm:px-4"
              >
                <ArrowLeft className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">返回结果</span>
              </Button>
              <div className="flex flex-col min-w-0 flex-1">
                <div className="flex items-center space-x-1 sm:space-x-2">
                  <Edit3 className="h-4 sm:h-5 w-4 sm:w-5 text-primary shrink-0" />
                  <h1 className="text-base sm:text-lg lg:text-xl font-semibold text-foreground truncate">
                    Markdown编辑器
                  </h1>
                </div>
                <div className="flex items-center space-x-1 sm:space-x-2 mt-1 flex-wrap gap-1">
                  <Badge variant="outline" className="text-[10px] sm:text-xs font-medium shrink-0 px-1.5 sm:px-2.5">
                    {formatTaskType(task.task_type)}
                  </Badge>
                  <span className="text-xs sm:text-sm text-muted-foreground font-mono truncate">
                    <span className="hidden sm:inline">ID: </span>{task.id.slice(0, 8)}
                  </span>
                  {task.created_at && (
                    <span className="text-[10px] sm:text-xs text-muted-foreground hidden sm:flex items-center shrink-0">
                      <Clock className="h-3 w-3 mr-1" />
                      {new Date(task.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-1 sm:space-x-2 shrink-0">
              {connectionStatus === 'offline' && (
                <Badge variant="destructive" className="text-[10px] sm:text-xs flex items-center px-1.5 sm:px-2.5 py-0.5 sm:py-1">
                  <WifiOff className="h-3 w-3 sm:mr-1" />
                  <span className="hidden sm:inline">离线</span>
                </Badge>
              )}
              {connectionStatus === 'online' && (
                <Badge variant="secondary" className="text-[10px] sm:text-xs items-center px-1.5 sm:px-2.5 py-0.5 sm:py-1 hidden sm:flex">
                  <Wifi className="h-3 w-3 mr-1" />
                  在线
                </Badge>
              )}
              {hasUnsavedChanges && (
                <Badge variant="secondary" className="text-[10px] sm:text-xs px-1.5 sm:px-2.5 py-0.5 sm:py-1">
                  <span className="hidden sm:inline">未保存</span>
                  <span className="sm:hidden">•</span>
                </Badge>
              )}
              <div className="hidden lg:flex flex-col text-right">
                {editorState.lastSaved && (
                  <span className="text-xs text-muted-foreground">
                    上次保存: {editorState.lastSaved.toLocaleTimeString()}
                  </span>
                )}
                {lastRefresh && connectionStatus === 'online' && (
                  <span className="text-xs text-muted-foreground">
                    数据刷新: {lastRefresh.toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Truncation Warning */}
      {conversionResult?.isTruncated && (
        <div className="border-b bg-yellow-50 dark:bg-yellow-950/20">
          <div className="container mx-auto px-4 py-3">
            <Card className="border-yellow-200 bg-yellow-50/50 dark:border-yellow-800 dark:bg-yellow-950/50">
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                          内容已截断
                        </p>
                        <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                          原始内容大小: {Math.round(conversionResult.originalSize / 1024)}KB，
                          当前显示: {Math.round(conversionResult.truncatedSize / 1024)}KB
                        </p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={onBack} 
                        className="shrink-0 border-yellow-300 text-yellow-800 hover:bg-yellow-100 dark:border-yellow-700 dark:text-yellow-200 dark:hover:bg-yellow-900/50"
                      >
                        查看完整内容
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="border-b bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-3 sm:px-4 py-2 sm:py-3">
          <div className="flex items-center justify-between flex-wrap gap-2 sm:gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center space-x-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleUndo}
                      disabled={editorState.historyIndex <= 0}
                      className="hover:bg-accent"
                    >
                      <RotateCcw className="h-4 w-4" />
                      <span className="hidden md:inline ml-1">撤销</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>撤销 (Ctrl+Z)</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRedo}
                      disabled={editorState.historyIndex >= editorState.editHistory.length - 1}
                      className="hover:bg-accent"
                    >
                      <RotateCcw className="h-4 w-4 scale-x-[-1]" />
                      <span className="hidden md:inline ml-1">重做</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>重做 (Ctrl+Shift+Z)</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              
              <Separator orientation="vertical" className="h-4 mx-2" />
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReset}
                    disabled={!editorState.isEdited}
                    className="hover:bg-accent"
                  >
                    <span>重置</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>重置为原始内容</p>
                </TooltipContent>
              </Tooltip>
            </div>
            
            <div className="flex items-center gap-2 flex-wrap">
              {/* Mobile view toggle */}
              {isMobileView && (
                <>
                  <Button
                    variant={editorState.isPreviewMode ? "secondary" : "outline"}
                    size="sm"
                    onClick={toggleViewMode}
                    className="hover:bg-accent"
                  >
                    {editorState.isPreviewMode ? (
                      <>
                        <Edit3 className="h-4 w-4 mr-1" />
                        编辑
                      </>
                    ) : (
                      <>
                        <Eye className="h-4 w-4 mr-1" />
                        预览
                      </>
                    )}
                  </Button>
                  <Separator orientation="vertical" className="h-4 mx-2" />
                </>
              )}
              
              <div className="flex items-center space-x-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={handleManualSave}
                      className="hover:bg-accent"
                    >
                      <Save className="h-4 w-4" />
                      <span className="hidden sm:inline ml-1">保存</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>手动保存 (Ctrl+S)</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={handleCopy}
                      className="hover:bg-accent"
                    >
                      <Copy className="h-4 w-4" />
                      <span className="hidden sm:inline ml-1">复制</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>复制到剪贴板</p>
                  </TooltipContent>
                </Tooltip>
                
                {/* Export dropdown menu */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="hover:bg-accent"
                      title="导出文件"
                    >
                      <Download className="h-4 w-4" />
                      <span className="hidden sm:inline ml-1">导出</span>
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuItem onClick={handleExportMarkdown} className="cursor-pointer">
                      <FileText className="h-4 w-4 mr-2" />
                      <div className="flex flex-col">
                        <span>导出为 Markdown</span>
                        <span className="text-xs text-muted-foreground">.md 文件</span>
                      </div>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={handleExportHtml} className="cursor-pointer">
                      <Globe className="h-4 w-4 mr-2" />
                      <div className="flex flex-col">
                        <span>导出为 HTML</span>
                        <span className="text-xs text-muted-foreground">.html 文件</span>
                      </div>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-3 sm:px-4 py-3 sm:py-4 lg:py-6">
        <div className="h-[calc(100vh-160px)] sm:h-[calc(100vh-180px)] lg:h-[calc(100vh-200px)] min-h-[300px] sm:min-h-[400px]">
          {isMobileView ? (
            // Mobile: Single view with toggle
            <Card className="h-full flex flex-col shadow-sm border-border bg-card">
              <CardHeader className="pb-2 sm:pb-3 px-3 sm:px-4 py-2 sm:py-3 border-b border-border bg-card/50">
                <CardTitle className="text-sm sm:text-base lg:text-lg flex items-center text-foreground">
                  {editorState.isPreviewMode ? (
                    <>
                      <Eye className="h-3.5 sm:h-4 w-3.5 sm:w-4 mr-1.5 sm:mr-2 text-primary" />
                      预览
                    </>
                  ) : (
                    <>
                      <Edit3 className="h-3.5 sm:h-4 w-3.5 sm:w-4 mr-1.5 sm:mr-2 text-primary" />
                      编辑器
                    </>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 p-0 overflow-hidden">
                {editorState.isPreviewMode ? (
                  <MarkdownPreview 
                    content={editorState.currentMarkdown}
                    className="h-full border-0 rounded-none"
                  />
                ) : (
                  <MarkdownEditor
                    value={editorState.currentMarkdown}
                    onChange={handleContentChange}
                    onKeyDown={handleKeyDown}
                    className="h-full border-0 rounded-none"
                  />
                )}
              </CardContent>
            </Card>
          ) : (
            // Desktop: Split view
            <div className="h-full rounded-lg overflow-hidden border border-border shadow-sm bg-card">
              <SplitView
                className="h-full"
                leftPanel={
                  <div className="h-full flex flex-col border-r border-border">
                    <div className="pb-3 px-4 py-3 border-b border-border bg-card/50">
                      <h3 className="text-base lg:text-lg font-semibold flex items-center text-foreground">
                        <Edit3 className="h-4 w-4 mr-2 text-primary" />
                        编辑器
                      </h3>
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <MarkdownEditor
                        value={editorState.currentMarkdown}
                        onChange={handleContentChange}
                        onKeyDown={handleKeyDown}
                        className="h-full border-0 rounded-none"
                      />
                    </div>
                  </div>
                }
                rightPanel={
                  <div className="h-full flex flex-col">
                    <div className="pb-3 px-4 py-3 border-b border-border bg-card/50">
                      <h3 className="text-base lg:text-lg font-semibold flex items-center text-foreground">
                        <Eye className="h-4 w-4 mr-2 text-primary" />
                        预览
                      </h3>
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <MarkdownPreview 
                        content={editorState.currentMarkdown}
                        className="h-full border-0 rounded-none"
                      />
                    </div>
                  </div>
                }
                defaultSplitPosition={50}
                minPaneSize={25}
              />
            </div>
          )}
        </div>
      </main>
    </div>
    </TooltipProvider>
  )
}