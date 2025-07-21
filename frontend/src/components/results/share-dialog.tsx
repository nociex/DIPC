"use client"

import { useState } from 'react'
import { Copy, Share2, Download, Calendar, Lock, Eye, EyeOff, Archive, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { useI18n } from '@/lib/i18n/context'
import { ExportService, type SharePermissions, type ExportFormat } from '@/lib/export-service'
import type { Task } from '@/types'

interface ShareDialogProps {
  task?: Task
  tasks?: Task[]
  isOpen: boolean
  onClose: () => void
}

export function ShareDialog({ task, tasks, isOpen, onClose }: ShareDialogProps) {
  const [shareLink, setShareLink] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState({ completed: 0, total: 0 })
  const [permissions, setPermissions] = useState<SharePermissions>({
    allowDownload: true,
    allowCopy: true,
    expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days from now
  })
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json')
  const [showPassword, setShowPassword] = useState(false)
  const [bulkExportMode, setBulkExportMode] = useState(false)
  
  const { t } = useI18n()
  const { toast } = useToast()

  const generateShareLink = async () => {
    if (!task) return
    
    setIsGenerating(true)
    try {
      const link = await ExportService.generateShareLink(task.id, permissions)
      setShareLink(link)
      toast({
        title: t('common.success'),
        description: 'Share link generated successfully'
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: 'Failed to generate share link',
        variant: 'destructive'
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const copyShareLink = async () => {
    if (!shareLink) return
    
    try {
      await navigator.clipboard.writeText(shareLink)
      toast({
        title: t('common.success'),
        description: 'Share link copied to clipboard'
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: 'Failed to copy share link',
        variant: 'destructive'
      })
    }
  }

  const handleExport = async () => {
    setIsExporting(true)
    setExportProgress({ completed: 0, total: 0 })
    
    try {
      const exportOptions = {
        includeMetadata: true,
        includeRawData: true,
        format: 'pretty' as const,
        dateFormat: 'locale' as const
      }

      let blob: Blob
      let filename: string

      if (tasks && tasks.length > 1) {
        // Bulk export
        setExportProgress({ completed: 0, total: tasks.length })
        
        blob = await ExportService.exportMultipleWithProgress(
          tasks,
          exportFormat,
          exportOptions,
          (completed, total) => setExportProgress({ completed, total })
        )
        
        filename = ExportService.getBulkExportFilename(tasks, exportFormat)
      } else if (task) {
        // Single export
        setExportProgress({ completed: 0, total: 1 })
        blob = await ExportService.exportResult(task, exportFormat, exportOptions)
        filename = ExportService.getExportFilename(task, exportFormat)
        setExportProgress({ completed: 1, total: 1 })
      } else {
        throw new Error('No task or tasks provided for export')
      }
      
      ExportService.downloadBlob(blob, filename)
      
      const count = tasks ? tasks.length : 1
      toast({
        title: t('common.success'),
        description: `${count} result${count > 1 ? 's' : ''} exported as ${exportFormat.toUpperCase()}`
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: 'Failed to export results',
        variant: 'destructive'
      })
    } finally {
      setIsExporting(false)
      setExportProgress({ completed: 0, total: 0 })
    }
  }

  const handleBulkExport = async () => {
    if (!tasks || tasks.length === 0) return
    
    setIsExporting(true)
    setExportProgress({ completed: 0, total: tasks.length })
    
    try {
      const formats: ExportFormat[] = ['json', 'csv', 'markdown', 'pdf']
      
      const blob = await ExportService.createExportArchive(
        tasks,
        formats,
        {
          includeMetadata: true,
          includeRawData: true,
          format: 'pretty',
          dateFormat: 'locale'
        },
        (completed, total) => setExportProgress({ completed, total })
      )
      
      const filename = `bulk-export-${tasks.length}-tasks-${new Date().toISOString().split('T')[0]}.zip`
      ExportService.downloadBlob(blob, filename)
      
      toast({
        title: t('common.success'),
        description: `Archive with ${tasks.length} results exported in multiple formats`
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: 'Failed to create export archive',
        variant: 'destructive'
      })
    } finally {
      setIsExporting(false)
      setExportProgress({ completed: 0, total: 0 })
    }
  }

  const updatePermissions = (key: keyof SharePermissions, value: any) => {
    setPermissions(prev => ({ ...prev, [key]: value }))
    // Clear existing share link when permissions change
    setShareLink('')
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            {t('common.share')} Results
          </CardTitle>
          <CardDescription>
            {tasks && tasks.length > 1 
              ? `Share or export ${tasks.length} results`
              : `Share or export results for: ${task?.original_filename || task?.id.slice(0, 8) + '...' || 'Unknown'}`
            }
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Export Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Export Results</h3>
            
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Select value={exportFormat} onValueChange={(value: ExportFormat) => setExportFormat(value)}>
                  <SelectTrigger className="flex-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="markdown">Markdown</SelectItem>
                    <SelectItem value="pdf">PDF</SelectItem>
                    <SelectItem value="xlsx">Excel</SelectItem>
                  </SelectContent>
                </Select>
                
                <Button onClick={handleExport} variant="outline" disabled={isExporting}>
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4 mr-2" />
                  )}
                  Export
                </Button>
              </div>

              {/* Bulk Export Option */}
              {tasks && tasks.length > 1 && (
                <div className="flex items-center gap-2">
                  <Button 
                    onClick={handleBulkExport} 
                    variant="outline" 
                    disabled={isExporting}
                    className="flex-1"
                  >
                    {isExporting ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Archive className="h-4 w-4 mr-2" />
                    )}
                    Export All Formats
                  </Button>
                </div>
              )}

              {/* Progress Indicator */}
              {isExporting && exportProgress.total > 0 && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Exporting...</span>
                    <span>{exportProgress.completed}/{exportProgress.total}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(exportProgress.completed / exportProgress.total) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Share Link Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Share Link</h3>
            
            {/* Permissions */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm">Allow downloads</label>
                <Switch
                  checked={permissions.allowDownload}
                  onCheckedChange={(checked) => updatePermissions('allowDownload', checked)}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <label className="text-sm">Allow copying</label>
                <Switch
                  checked={permissions.allowCopy}
                  onCheckedChange={(checked) => updatePermissions('allowCopy', checked)}
                />
              </div>
              
              <div className="space-y-2">
                <label className="text-sm">Expires on</label>
                <Input
                  type="datetime-local"
                  value={permissions.expiresAt ? new Date(permissions.expiresAt.getTime() - permissions.expiresAt.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ''}
                  onChange={(e) => updatePermissions('expiresAt', e.target.value ? new Date(e.target.value) : undefined)}
                />
              </div>
              
              <div className="space-y-2">
                <label className="text-sm">Password protection (optional)</label>
                <div className="flex items-center gap-2">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={permissions.password || ''}
                    onChange={(e) => updatePermissions('password', e.target.value || undefined)}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </div>

            {/* Generate/Copy Link */}
            <div className="space-y-2">
              {!shareLink ? (
                <Button 
                  onClick={generateShareLink} 
                  disabled={isGenerating}
                  className="w-full"
                >
                  {isGenerating ? 'Generating...' : 'Generate Share Link'}
                </Button>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Input
                      value={shareLink}
                      readOnly
                      className="flex-1"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copyShareLink}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Link expires on {permissions.expiresAt?.toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}