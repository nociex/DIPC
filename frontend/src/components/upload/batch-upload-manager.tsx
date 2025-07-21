"use client"

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { cn, generateClientId } from '@/lib/utils'
import { useToast } from '@/components/ui/use-toast'
import { FileAnalysisService, FileAnalysisResult } from '@/lib/file-analysis'
import { FileAnalysisDisplay } from './file-analysis-display'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Upload,
  Play,
  Pause,
  RotateCcw,
  X,
  CheckCircle,
  AlertCircle,
  Clock,
  DollarSign,
  FileText,
  Layers,
  Settings,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react'

// Enhanced file interface for batch processing
export interface BatchFile extends File {
  id: string
  uploadStatus: 'pending' | 'uploading' | 'completed' | 'error' | 'cancelled'
  uploadProgress: number
  error?: string
  retryCount: number
  analysis?: FileAnalysisResult
  batchGroup?: string
  priority: 'low' | 'normal' | 'high'
  estimatedTime?: number
  estimatedCost?: number
}

// Batch configuration
export interface BatchConfig {
  enableIntelligentBatching: boolean
  maxConcurrentUploads: number
  retryAttempts: number
  retryDelay: number
  groupSimilarFiles: boolean
  prioritizeSmallFiles: boolean
  autoStartProcessing: boolean
}

// Batch statistics
export interface BatchStats {
  totalFiles: number
  completedFiles: number
  failedFiles: number
  totalSize: number
  totalEstimatedCost: number
  totalEstimatedTime: number
  averageProgress: number
  currentThroughput: number
}

// Batch upload manager props
export interface BatchUploadManagerProps {
  files: File[]
  onFilesChange: (files: BatchFile[]) => void
  onUploadComplete: (results: any[]) => void
  onConfigChange?: (config: BatchConfig) => void
  className?: string
  autoAnalyze?: boolean
  showAdvancedOptions?: boolean
}

// Default batch configuration
const DEFAULT_BATCH_CONFIG: BatchConfig = {
  enableIntelligentBatching: true,
  maxConcurrentUploads: 3,
  retryAttempts: 3,
  retryDelay: 2000,
  groupSimilarFiles: true,
  prioritizeSmallFiles: false,
  autoStartProcessing: true
}

export function BatchUploadManager({
  files,
  onFilesChange,
  onUploadComplete,
  onConfigChange,
  className,
  autoAnalyze = true,
  showAdvancedOptions = false
}: BatchUploadManagerProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  
  // State management
  const [batchFiles, setBatchFiles] = useState<BatchFile[]>([])
  const [batchConfig, setBatchConfig] = useState<BatchConfig>(DEFAULT_BATCH_CONFIG)
  const [batchStats, setBatchStats] = useState<BatchStats | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [batchAnalysis, setBatchAnalysis] = useState<any>(null)
  
  // Refs for upload management
  const uploadQueueRef = useRef<BatchFile[]>([])
  const activeUploadsRef = useRef<Map<string, AbortController>>(new Map())
  const statsIntervalRef = useRef<NodeJS.Timeout>()

  // Initialize batch files when files prop changes
  useEffect(() => {
    if (files.length > 0) {
      const newBatchFiles: BatchFile[] = files.map((file, index) => ({
        ...file,
        id: generateClientId(`batch_${index}`),
        uploadStatus: 'pending',
        uploadProgress: 0,
        retryCount: 0,
        priority: 'normal'
      }))
      
      setBatchFiles(newBatchFiles)
      onFilesChange(newBatchFiles)
      
      // Auto-analyze files if enabled
      if (autoAnalyze) {
        analyzeBatch(newBatchFiles)
      }
    }
  }, [files, autoAnalyze, onFilesChange])

  // Analyze batch of files
  const analyzeBatch = useCallback(async (filesToAnalyze: BatchFile[]) => {
    try {
      const regularFiles = filesToAnalyze.map(f => {
        const { id, uploadStatus, uploadProgress, error, retryCount, analysis, batchGroup, priority, estimatedTime, estimatedCost, ...regularFile } = f
        return regularFile as File
      })
      
      const analysis = await FileAnalysisService.analyzeBatch(regularFiles)
      setBatchAnalysis(analysis)
      
      // Update batch files with individual analyses
      const updatedFiles = filesToAnalyze.map((file, index) => ({
        ...file,
        analysis: analysis.individualAnalyses[index],
        estimatedTime: analysis.individualAnalyses[index].estimatedTime,
        estimatedCost: analysis.individualAnalyses[index].estimatedCost,
        batchGroup: analysis.individualAnalyses[index].category
      }))
      
      setBatchFiles(updatedFiles)
      onFilesChange(updatedFiles)
      
      // Apply intelligent batching if enabled
      if (batchConfig.enableIntelligentBatching) {
        applyIntelligentBatching(updatedFiles)
      }
      
    } catch (error) {
      console.error('Batch analysis failed:', error)
      toast({
        title: t('upload.batch.analysisError'),
        description: t('upload.batch.analysisErrorDescription'),
        variant: "destructive",
      })
    }
  }, [batchConfig.enableIntelligentBatching, onFilesChange, t, toast])

  // Apply intelligent batching logic
  const applyIntelligentBatching = useCallback((files: BatchFile[]) => {
    let updatedFiles = [...files]
    
    if (batchConfig.groupSimilarFiles) {
      // Group files by category and assign batch groups
      const groups = new Map<string, BatchFile[]>()
      updatedFiles.forEach(file => {
        const category = file.analysis?.category || 'unknown'
        if (!groups.has(category)) {
          groups.set(category, [])
        }
        groups.get(category)!.push(file)
      })
      
      // Assign batch group identifiers
      updatedFiles = updatedFiles.map(file => ({
        ...file,
        batchGroup: file.analysis?.category || 'unknown'
      }))
    }
    
    if (batchConfig.prioritizeSmallFiles) {
      // Prioritize smaller files for faster initial results
      updatedFiles = updatedFiles.map(file => ({
        ...file,
        priority: file.size < 1024 * 1024 ? 'high' : file.size < 10 * 1024 * 1024 ? 'normal' : 'low'
      }))
    }
    
    setBatchFiles(updatedFiles)
    onFilesChange(updatedFiles)
  }, [batchConfig.groupSimilarFiles, batchConfig.prioritizeSmallFiles, onFilesChange])

  // Calculate batch statistics
  const calculateBatchStats = useCallback(() => {
    const stats: BatchStats = {
      totalFiles: batchFiles.length,
      completedFiles: batchFiles.filter(f => f.uploadStatus === 'completed').length,
      failedFiles: batchFiles.filter(f => f.uploadStatus === 'error').length,
      totalSize: batchFiles.reduce((sum, f) => sum + f.size, 0),
      totalEstimatedCost: batchFiles.reduce((sum, f) => sum + (f.estimatedCost || 0), 0),
      totalEstimatedTime: Math.max(...batchFiles.map(f => f.estimatedTime || 0)),
      averageProgress: batchFiles.reduce((sum, f) => sum + f.uploadProgress, 0) / batchFiles.length,
      currentThroughput: 0 // TODO: Calculate based on recent upload speeds
    }
    
    setBatchStats(stats)
    return stats
  }, [batchFiles])

  // Update statistics periodically
  useEffect(() => {
    if (isUploading) {
      statsIntervalRef.current = setInterval(calculateBatchStats, 1000)
    } else {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current)
      }
    }
    
    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current)
      }
    }
  }, [isUploading, calculateBatchStats])

  // Start batch upload
  const startBatchUpload = useCallback(async () => {
    setIsUploading(true)
    setIsPaused(false)
    
    // Sort files by priority
    const sortedFiles = [...batchFiles]
      .filter(f => f.uploadStatus === 'pending' || f.uploadStatus === 'error')
      .sort((a, b) => {
        const priorityOrder = { high: 3, normal: 2, low: 1 }
        return priorityOrder[b.priority] - priorityOrder[a.priority]
      })
    
    uploadQueueRef.current = sortedFiles
    
    // Start concurrent uploads
    const concurrentUploads = Math.min(batchConfig.maxConcurrentUploads, sortedFiles.length)
    const uploadPromises = []
    
    for (let i = 0; i < concurrentUploads; i++) {
      uploadPromises.push(processUploadQueue())
    }
    
    try {
      await Promise.all(uploadPromises)
      
      toast({
        title: t('upload.batch.completed'),
        description: t('upload.batch.completedDescription', { 
          count: batchFiles.filter(f => f.uploadStatus === 'completed').length 
        }),
      })
      
      onUploadComplete(batchFiles.filter(f => f.uploadStatus === 'completed'))
      
    } catch (error) {
      console.error('Batch upload failed:', error)
      toast({
        title: t('upload.batch.error'),
        description: t('upload.batch.errorDescription'),
        variant: "destructive",
      })
    } finally {
      setIsUploading(false)
    }
  }, [batchFiles, batchConfig.maxConcurrentUploads, onUploadComplete, t, toast])

  // Process upload queue
  const processUploadQueue = useCallback(async () => {
    while (uploadQueueRef.current.length > 0 && !isPaused) {
      const file = uploadQueueRef.current.shift()
      if (!file) break
      
      await uploadSingleFile(file)
    }
  }, [isPaused])

  // Upload single file with retry logic
  const uploadSingleFile = useCallback(async (file: BatchFile) => {
    const abortController = new AbortController()
    activeUploadsRef.current.set(file.id, abortController)
    
    try {
      // Update file status to uploading
      setBatchFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { ...f, uploadStatus: 'uploading' as const, uploadProgress: 0 }
          : f
      ))
      
      // Simulate file upload with progress
      // In real implementation, this would use the actual upload API
      await simulateFileUpload(file, abortController.signal)
      
      // Mark as completed
      setBatchFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { ...f, uploadStatus: 'completed' as const, uploadProgress: 100 }
          : f
      ))
      
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Upload was cancelled
        setBatchFiles(prev => prev.map(f => 
          f.id === file.id 
            ? { ...f, uploadStatus: 'cancelled' as const }
            : f
        ))
      } else {
        // Upload failed, check if we should retry
        const shouldRetry = file.retryCount < batchConfig.retryAttempts
        
        if (shouldRetry) {
          // Schedule retry
          setTimeout(() => {
            const updatedFile = { ...file, retryCount: file.retryCount + 1 }
            uploadQueueRef.current.unshift(updatedFile)
          }, batchConfig.retryDelay)
          
          setBatchFiles(prev => prev.map(f => 
            f.id === file.id 
              ? { ...f, retryCount: f.retryCount + 1, uploadStatus: 'pending' as const }
              : f
          ))
        } else {
          // Mark as failed
          setBatchFiles(prev => prev.map(f => 
            f.id === file.id 
              ? { 
                  ...f, 
                  uploadStatus: 'error' as const, 
                  error: error instanceof Error ? error.message : 'Upload failed'
                }
              : f
          ))
        }
      }
    } finally {
      activeUploadsRef.current.delete(file.id)
    }
  }, [batchConfig.retryAttempts, batchConfig.retryDelay])

  // Simulate file upload (replace with actual upload logic)
  const simulateFileUpload = useCallback(async (file: BatchFile, signal: AbortSignal) => {
    const totalSteps = 10
    const stepDelay = (file.estimatedTime || 30) * 100 // Convert to milliseconds per step
    
    for (let step = 0; step <= totalSteps; step++) {
      if (signal.aborted) {
        throw new Error('Upload cancelled')
      }
      
      const progress = (step / totalSteps) * 100
      
      setBatchFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { ...f, uploadProgress: progress }
          : f
      ))
      
      if (step < totalSteps) {
        await new Promise(resolve => setTimeout(resolve, stepDelay))
      }
    }
  }, [])

  // Pause batch upload
  const pauseBatchUpload = useCallback(() => {
    setIsPaused(true)
    
    // Cancel active uploads
    activeUploadsRef.current.forEach(controller => {
      controller.abort()
    })
    activeUploadsRef.current.clear()
    
    toast({
      title: t('upload.batch.paused'),
      description: t('upload.batch.pausedDescription'),
    })
  }, [t, toast])

  // Resume batch upload
  const resumeBatchUpload = useCallback(() => {
    setIsPaused(false)
    
    // Restart processing queue
    const pendingFiles = batchFiles.filter(f => 
      f.uploadStatus === 'pending' || f.uploadStatus === 'cancelled'
    )
    
    if (pendingFiles.length > 0) {
      uploadQueueRef.current = pendingFiles
      processUploadQueue()
    }
    
    toast({
      title: t('upload.batch.resumed'),
      description: t('upload.batch.resumedDescription'),
    })
  }, [batchFiles, processUploadQueue, t, toast])

  // Retry failed files
  const retryFailedFiles = useCallback(() => {
    const failedFiles = batchFiles.filter(f => f.uploadStatus === 'error')
    
    if (failedFiles.length === 0) return
    
    // Reset failed files to pending
    setBatchFiles(prev => prev.map(f => 
      f.uploadStatus === 'error' 
        ? { ...f, uploadStatus: 'pending' as const, error: undefined, retryCount: 0 }
        : f
    ))
    
    toast({
      title: t('upload.batch.retrying'),
      description: t('upload.batch.retryingDescription', { count: failedFiles.length }),
    })
  }, [batchFiles, t, toast])

  // Remove file from batch
  const removeFile = useCallback((fileId: string) => {
    // Cancel upload if in progress
    const controller = activeUploadsRef.current.get(fileId)
    if (controller) {
      controller.abort()
      activeUploadsRef.current.delete(fileId)
    }
    
    const updatedFiles = batchFiles.filter(f => f.id !== fileId)
    setBatchFiles(updatedFiles)
    onFilesChange(updatedFiles)
  }, [batchFiles, onFilesChange])

  // Toggle file selection
  const toggleFileSelection = useCallback((fileId: string) => {
    setSelectedFiles(prev => {
      const newSelection = new Set(prev)
      if (newSelection.has(fileId)) {
        newSelection.delete(fileId)
      } else {
        newSelection.add(fileId)
      }
      return newSelection
    })
  }, [])

  // Calculate current statistics
  useEffect(() => {
    calculateBatchStats()
  }, [calculateBatchStats])

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }, [])

  // Format time
  const formatTime = useCallback((seconds: number): string => {
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }, [])

  if (batchFiles.length === 0) {
    return null
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Layers className="w-5 h-5" />
            <span>{t('upload.batch.title')}</span>
            <Badge variant="secondary">
              {batchFiles.length} {t('upload.batch.files')}
            </Badge>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfig(!showConfig)}
            >
              <Settings className="w-4 h-4 mr-1" />
              {t('upload.batch.config')}
              {showConfig ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
            </Button>
            
            {!isUploading ? (
              <Button onClick={startBatchUpload} disabled={batchFiles.length === 0}>
                <Play className="w-4 h-4 mr-1" />
                {t('upload.batch.start')}
              </Button>
            ) : isPaused ? (
              <Button onClick={resumeBatchUpload}>
                <Play className="w-4 h-4 mr-1" />
                {t('upload.batch.resume')}
              </Button>
            ) : (
              <Button onClick={pauseBatchUpload} variant="outline">
                <Pause className="w-4 h-4 mr-1" />
                {t('upload.batch.pause')}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Batch Statistics */}
        {batchStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-blue-600">
                {batchStats.completedFiles}/{batchStats.totalFiles}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('upload.batch.completed')}
              </div>
            </div>
            
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-green-600">
                ${batchStats.totalEstimatedCost.toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('upload.batch.totalCost')}
              </div>
            </div>
            
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-purple-600">
                {formatTime(batchStats.totalEstimatedTime)}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('upload.batch.totalTime')}
              </div>
            </div>
            
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold text-orange-600">
                {formatFileSize(batchStats.totalSize)}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('upload.batch.totalSize')}
              </div>
            </div>
          </div>
        )}

        {/* Overall Progress */}
        {isUploading && batchStats && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{t('upload.batch.overallProgress')}</span>
              <span>{Math.round(batchStats.averageProgress)}%</span>
            </div>
            <Progress value={batchStats.averageProgress} className="h-2" />
          </div>
        )}

        {/* Batch Analysis Summary */}
        {batchAnalysis && (
          <div className="p-4 rounded-lg bg-blue-50 border border-blue-200">
            <div className="flex items-center space-x-2 mb-3">
              <Info className="w-4 h-4 text-blue-600" />
              <h4 className="font-medium text-blue-800">
                {t('upload.batch.analysisTitle')}
              </h4>
            </div>
            
            {batchAnalysis.batchWarnings.length > 0 && (
              <div className="mb-3">
                <h5 className="text-sm font-medium text-yellow-800 mb-1">
                  {t('upload.analysis.warnings')}
                </h5>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {batchAnalysis.batchWarnings.map((warning: string, index: number) => (
                    <li key={index} className="flex items-start space-x-1">
                      <span>•</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {batchAnalysis.batchRecommendations.length > 0 && (
              <div>
                <h5 className="text-sm font-medium text-blue-800 mb-1">
                  {t('upload.analysis.recommendations')}
                </h5>
                <ul className="text-sm text-blue-700 space-y-1">
                  {batchAnalysis.batchRecommendations.map((recommendation: string, index: number) => (
                    <li key={index} className="flex items-start space-x-1">
                      <span>•</span>
                      <span>{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* File List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">{t('upload.batch.fileList')}</h4>
            <div className="flex items-center space-x-2">
              {batchFiles.some(f => f.uploadStatus === 'error') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={retryFailedFiles}
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  {t('upload.batch.retryFailed')}
                </Button>
              )}
            </div>
          </div>
          
          <ScrollArea className="h-96">
            <div className="space-y-2">
              {batchFiles.map((file) => (
                <div
                  key={file.id}
                  className={cn(
                    "flex items-center space-x-3 p-3 rounded-lg border transition-colors",
                    selectedFiles.has(file.id) && "bg-primary/5 border-primary/30"
                  )}
                >
                  {/* File Status Icon */}
                  <div className="flex-shrink-0">
                    {file.uploadStatus === 'completed' && (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    )}
                    {file.uploadStatus === 'error' && (
                      <AlertCircle className="w-5 h-5 text-red-600" />
                    )}
                    {file.uploadStatus === 'uploading' && (
                      <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    )}
                    {(file.uploadStatus === 'pending' || file.uploadStatus === 'cancelled') && (
                      <Clock className="w-5 h-5 text-gray-400" />
                    )}
                  </div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="font-medium truncate">{file.name}</p>
                      <div className="flex items-center space-x-2">
                        {file.batchGroup && (
                          <Badge variant="outline" className="text-xs">
                            {file.batchGroup}
                          </Badge>
                        )}
                        {file.priority !== 'normal' && (
                          <Badge 
                            variant={file.priority === 'high' ? 'default' : 'secondary'}
                            className="text-xs"
                          >
                            {file.priority}
                          </Badge>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>{formatFileSize(file.size)}</span>
                      <div className="flex items-center space-x-4">
                        {file.estimatedTime && (
                          <span className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatTime(file.estimatedTime)}</span>
                          </span>
                        )}
                        {file.estimatedCost && (
                          <span className="flex items-center space-x-1">
                            <DollarSign className="w-3 h-3" />
                            <span>${file.estimatedCost.toFixed(2)}</span>
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    {file.uploadStatus === 'uploading' && (
                      <Progress value={file.uploadProgress} className="mt-2 h-1" />
                    )}

                    {/* Error Message */}
                    {file.uploadStatus === 'error' && file.error && (
                      <p className="text-xs text-red-600 mt-1">{file.error}</p>
                    )}

                    {/* Retry Count */}
                    {file.retryCount > 0 && (
                      <p className="text-xs text-yellow-600 mt-1">
                        {t('upload.batch.retryCount', { count: file.retryCount })}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(file.id)}
                      className="h-8 w-8 p-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  )
}