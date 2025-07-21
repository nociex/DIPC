"use client"

import React, { useMemo } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useWorkspace } from '../workspace-container'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { TaskConfigPanel } from '@/components/config/task-config-panel'
import { 
  Upload, 
  FileText, 
  Image, 
  Archive,
  File,
  CheckCircle,
  XCircle,
  Clock,
  Settings,
  Play,
  DollarSign,
  Timer,
  Trash2
} from 'lucide-react'

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

export function UploadingState() {
  const { t } = useTranslation()
  const { state, actions } = useWorkspace()

  // Calculate upload statistics
  const uploadStats = useMemo(() => {
    const total = state.files.length
    const completed = state.files.filter(f => f.uploadStatus === 'completed').length
    const failed = state.files.filter(f => f.uploadStatus === 'error').length
    const uploading = state.files.filter(f => f.uploadStatus === 'uploading').length
    const pending = state.files.filter(f => !f.uploadStatus || f.uploadStatus === 'pending').length
    
    const totalSize = state.files.reduce((acc, file) => acc + file.size, 0)
    const overallProgress = total > 0 ? Math.round((completed / total) * 100) : 0
    
    return { total, completed, failed, uploading, pending, totalSize, overallProgress }
  }, [state.files])

  // Estimate processing cost and time (mock calculation)
  const estimates = useMemo(() => {
    const baseTimePerMB = 30 // seconds
    const baseCostPerMB = 0.01 // dollars
    const totalMB = uploadStats.totalSize / (1024 * 1024)
    
    const estimatedTime = Math.max(60, totalMB * baseTimePerMB) // minimum 1 minute
    const estimatedCost = Math.max(0.05, totalMB * baseCostPerMB) // minimum 5 cents
    
    return { estimatedTime, estimatedCost }
  }, [uploadStats.totalSize])

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  // Format time duration
  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    }
    return `${remainingSeconds}s`
  }

  // Get file icon
  const getFileIcon = (file: File) => {
    const IconComponent = FILE_TYPE_ICONS[file.type as keyof typeof FILE_TYPE_ICONS] || FILE_TYPE_ICONS.default
    return IconComponent
  }

  // Remove file from upload queue
  const removeFile = (index: number) => {
    const newFiles = state.files.filter((_, i) => i !== index)
    actions.handleFilesSelected(newFiles)
  }

  // Check if ready to process
  const canProcess = uploadStats.completed > 0 && uploadStats.uploading === 0 && !state.isUploading

  return (
    <div className="h-full flex flex-col p-6 space-y-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">
            {t('workspace.uploading.title')}
          </h2>
          <p className="text-muted-foreground">
            {t('workspace.uploading.subtitle')}
          </p>
        </div>
        
        {/* Overall progress */}
        {state.isUploading && (
          <div className="text-right">
            <div className="text-sm font-medium mb-1">
              {uploadStats.overallProgress}% {t('workspace.uploading.complete')}
            </div>
            <Progress value={uploadStats.overallProgress} className="w-32" />
          </div>
        )}
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Files List */}
        <div className="lg:col-span-2 space-y-4">
          {/* Upload Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center space-x-2">
                <Upload className="w-5 h-5" />
                <span>{t('workspace.uploading.files')}</span>
                <Badge variant="secondary">{uploadStats.total}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Status Summary */}
              <div className="flex items-center space-x-6 mb-4">
                {uploadStats.completed > 0 && (
                  <div className="flex items-center space-x-2 text-green-600">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-sm font-medium">{uploadStats.completed} {t('workspace.uploading.completed')}</span>
                  </div>
                )}
                {uploadStats.uploading > 0 && (
                  <div className="flex items-center space-x-2 text-blue-600">
                    <Clock className="w-4 h-4 animate-spin" />
                    <span className="text-sm font-medium">{uploadStats.uploading} {t('workspace.uploading.uploading')}</span>
                  </div>
                )}
                {uploadStats.failed > 0 && (
                  <div className="flex items-center space-x-2 text-red-600">
                    <XCircle className="w-4 h-4" />
                    <span className="text-sm font-medium">{uploadStats.failed} {t('workspace.uploading.failed')}</span>
                  </div>
                )}
                {uploadStats.pending > 0 && (
                  <div className="flex items-center space-x-2 text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm font-medium">{uploadStats.pending} {t('workspace.uploading.pending')}</span>
                  </div>
                )}
              </div>

              {/* Overall Progress Bar */}
              {state.isUploading && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span>{t('workspace.uploading.overallProgress')}</span>
                    <span>{uploadStats.overallProgress}%</span>
                  </div>
                  <Progress value={uploadStats.overallProgress} className="h-2" />
                </div>
              )}

              <Separator className="my-4" />

              {/* Individual Files */}
              <div className="space-y-3 max-h-96 overflow-auto">
                {state.files.map((file, index) => {
                  const IconComponent = getFileIcon(file)
                  return (
                    <div
                      key={`${file.name}-${index}`}
                      className="flex items-center space-x-3 p-3 rounded-lg border bg-background/50"
                    >
                      {/* File icon */}
                      <div className="flex-shrink-0">
                        <IconComponent className="w-8 h-8 text-muted-foreground" />
                      </div>
                      
                      {/* File info */}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate" title={file.name}>
                          {file.name}
                        </p>
                        <p className="text-sm text-muted-foreground">
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
                      
                      {/* Status and actions */}
                      <div className="flex-shrink-0 flex items-center space-x-2">
                        {/* Status indicator */}
                        {file.uploadStatus === 'completed' && (
                          <CheckCircle className="w-5 h-5 text-green-600" />
                        )}
                        {file.uploadStatus === 'error' && (
                          <XCircle className="w-5 h-5 text-red-600" />
                        )}
                        {file.uploadStatus === 'uploading' && (
                          <Clock className="w-5 h-5 text-blue-600 animate-spin" />
                        )}
                        
                        {/* Remove button */}
                        {!state.isUploading && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(index)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Configuration and Actions */}
        <div className="space-y-4">
          {/* Processing Estimates */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center space-x-2">
                <Timer className="w-5 h-5" />
                <span>{t('workspace.uploading.estimates')}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Timer className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">{t('workspace.uploading.estimatedTime')}</span>
                </div>
                <span className="font-medium">{formatDuration(estimates.estimatedTime)}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <DollarSign className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">{t('workspace.uploading.estimatedCost')}</span>
                </div>
                <span className="font-medium">${estimates.estimatedCost.toFixed(2)}</span>
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{t('workspace.uploading.totalSize')}</span>
                <span className="font-medium">{formatFileSize(uploadStats.totalSize)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Configuration Panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center space-x-2">
                <Settings className="w-5 h-5" />
                <span>{t('workspace.uploading.configuration')}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TaskConfigPanel
                options={state.taskOptions}
                onChange={actions.updateTaskOptions}
              />
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="space-y-3">
            <Button
              onClick={actions.uploadFiles}
              disabled={!canProcess || state.files.length === 0}
              className="w-full"
              size="lg"
            >
              <Play className="w-5 h-5 mr-2" />
              {state.isUploading 
                ? t('workspace.uploading.processing') 
                : t('workspace.uploading.startProcessing')
              }
            </Button>
            
            {!state.isUploading && (
              <Button
                variant="outline"
                onClick={() => actions.handleViewChange('empty')}
                className="w-full"
              >
                {t('workspace.uploading.addMoreFiles')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}