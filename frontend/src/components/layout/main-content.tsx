"use client"

import { useState, useEffect } from 'react'
import { FileUploadZone } from '@/components/upload/file-upload-zone'
import { TaskConfigPanel } from '@/components/config/task-config-panel'
import { TaskListView } from '@/components/tasks/task-list-view'
import { ResultsViewer } from '@/components/tasks/results-viewer'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api'
import type { Task, TaskOptions, TaskCreateRequest } from '@/types'
import { TaskStatus, StoragePolicy } from '@/types'
import { Upload, Settings, Monitor, FileText } from 'lucide-react'
import { useAnnouncements } from '@/hooks/use-accessibility'

interface FileWithPreview extends File {
  preview?: string
  uploadProgress?: number
  uploadStatus?: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

export function MainContent() {
  // Add accessibility hooks
  const { announce, announceAction, announceError, announceSuccess } = useAnnouncements()
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [activeTab, setActiveTab] = useState('upload')
  const [taskOptions, setTaskOptions] = useState<TaskOptions>({
    enable_vectorization: true,
    storage_policy: StoragePolicy.TEMPORARY,
    max_cost_limit: 1.0,
    llm_provider: 'openai'
  })
  
  const { toast } = useToast()

  // Load tasks on component mount
  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    try {
      // Use a default user ID for demo purposes
      const userId = 'demo-user'
      const response = await api.listTasks(userId)
      setTasks(response.tasks)
    } catch (error) {
      console.error('Failed to load tasks:', error)
      toast({
        title: "Failed to load tasks",
        description: "Could not retrieve task list from server",
        variant: "destructive",
      })
    }
  }

  const handleFilesSelected = (files: FileWithPreview[]) => {
    setSelectedFiles(files)
  }

  const uploadFiles = async () => {
    if (selectedFiles.length === 0) {
      toast({
        title: "No files selected",
        description: "Please select files to upload",
        variant: "destructive",
      })
      return
    }

    setIsUploading(true)
    const uploadedFileUrls: string[] = []

    try {
      // Upload each file
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i]
        
        // Update file status to uploading
        setSelectedFiles(prev => prev.map((f, index) => 
          index === i ? { ...f, uploadStatus: 'uploading' as const, uploadProgress: 0 } : f
        ))
        announceAction(`Uploading ${file.name}`)

        try {
          // Get presigned URL
          const presignedResponse = await api.getPresignedUrl({
            filename: file.name,
            content_type: file.type,
            file_size: file.size
          })

          // Upload file with progress tracking
          await api.uploadFile(file, presignedResponse.upload_url, (progress) => {
            setSelectedFiles(prev => prev.map((f, index) => 
              index === i ? { ...f, uploadProgress: progress } : f
            ))
          })

          // Mark as completed
          setSelectedFiles(prev => prev.map((f, index) => 
            index === i ? { ...f, uploadStatus: 'completed' as const, uploadProgress: 100 } : f
          ))
          announceSuccess(`${file.name} uploaded successfully`)

          uploadedFileUrls.push(presignedResponse.file_url)

        } catch (error) {
          console.error(`Failed to upload ${file.name}:`, error)
          setSelectedFiles(prev => prev.map((f, index) => 
            index === i ? { 
              ...f, 
              uploadStatus: 'error' as const, 
              error: error instanceof Error ? error.message : 'Upload failed'
            } : f
          ))
          announceError(`Failed to upload ${file.name}`)
        }
      }

      if (uploadedFileUrls.length > 0) {
        // Create processing task
        const taskRequest: TaskCreateRequest = {
          file_urls: uploadedFileUrls,
          user_id: 'demo-user',
          options: taskOptions
        }

        const taskResponse = await api.createTask(taskRequest)
        
        toast({
          title: "Files uploaded successfully",
          description: `${uploadedFileUrls.length} files uploaded and processing started`,
        })
        announceSuccess(`${uploadedFileUrls.length} files uploaded and processing started`)

        // Switch to monitor tab and refresh tasks
        setActiveTab('monitor')
        await loadTasks()
        
        // Clear selected files
        setSelectedFiles([])
      }

    } catch (error) {
      console.error('Upload process failed:', error)
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to process files",
        variant: "destructive",
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleViewResults = (task: Task) => {
    setSelectedTask(task)
    setActiveTab('results')
  }

  const handleDownloadResults = async (task: Task) => {
    try {
      toast({
        title: "Download started",
        description: `Downloading results for task ${task.id.slice(0, 8)}...`,
      })
      
      // Download the task results as markdown
      const blob = await api.downloadTaskResults(task.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `dipc-results-${task.id.slice(0, 8)}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      toast({
        title: "Download complete",
        description: "Results saved to your downloads folder",
      })
      
    } catch (error) {
      console.error('Download failed:', error)
      toast({
        title: "Download failed",
        description: error instanceof Error ? error.message : "Could not download results",
        variant: "destructive",
      })
    }
  }

  return (
    <main id="main-content" role="main" className="flex-1 container py-8" tabIndex={-1}>
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="sr-only">Document Intelligence & Parsing Center Application</h1>
          <h2 className="text-3xl font-bold tracking-tight">
            Document Intelligence & Parsing Center
          </h2>
          <p className="text-muted-foreground">
            Upload and process documents with AI-powered intelligence
          </p>
        </div>

        {/* Main Interface */}
        <Tabs 
          value={activeTab} 
          onValueChange={(value) => {
            setActiveTab(value)
            announce(`Switched to ${value} tab`)
          }}
          className="space-y-6"
          aria-label="Main navigation tabs"
        >
          <TabsList className="grid w-full grid-cols-4" role="tablist" aria-label="Document processing sections">
            <TabsTrigger 
              value="upload" 
              className="flex items-center space-x-2"
              id="upload-tab"
              aria-controls="upload-section"
            >
              <Upload className="h-4 w-4" />
              <span>Upload</span>
            </TabsTrigger>
            <TabsTrigger 
              value="config" 
              className="flex items-center space-x-2"
              id="config-tab"
              aria-controls="config-section"
            >
              <Settings className="h-4 w-4" />
              <span>Configure</span>
            </TabsTrigger>
            <TabsTrigger 
              value="monitor" 
              className="flex items-center space-x-2"
              id="monitor-tab"
              aria-controls="monitor-section"
            >
              <Monitor className="h-4 w-4" />
              <span>Monitor</span>
            </TabsTrigger>
            <TabsTrigger 
              value="results" 
              className="flex items-center space-x-2"
              id="results-tab"
              aria-controls="results-section"
            >
              <FileText className="h-4 w-4" />
              <span>Results</span>
            </TabsTrigger>
          </TabsList>

          {/* Upload Tab */}
          <TabsContent 
            value="upload" 
            className="space-y-6"
            id="upload-section"
            role="tabpanel"
            aria-labelledby="upload-tab"
          >
            <Card>
              <CardHeader>
                <CardTitle>Upload Documents</CardTitle>
                <CardDescription>
                  Upload individual files or ZIP archives for batch processing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FileUploadZone
                  onFilesSelected={handleFilesSelected}
                  maxFiles={10}
                  maxSize={100 * 1024 * 1024} // 100MB
                />
                
                {selectedFiles.length > 0 && (
                  <div className="mt-6 flex justify-end">
                    <Button 
                      onClick={uploadFiles}
                      disabled={isUploading}
                      size="lg"
                    >
                      <span aria-live="polite">
                        {isUploading ? 'Uploading...' : `Process ${selectedFiles.length} File(s)`}
                      </span>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent 
            value="config" 
            className="space-y-6"
            id="config-section"
            role="tabpanel"
            aria-labelledby="config-tab"
          >
            <Card>
              <CardHeader>
                <CardTitle>Processing Configuration</CardTitle>
                <CardDescription>
                  Configure how your documents will be processed
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TaskConfigPanel
                  options={taskOptions}
                  onChange={setTaskOptions}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Monitor Tab */}
          <TabsContent 
            value="monitor" 
            className="space-y-6"
            id="monitor-section"
            role="tabpanel"
            aria-labelledby="monitor-tab"
          >
            <TaskListView
              tasks={tasks}
              onRefresh={loadTasks}
              onViewResults={handleViewResults}
              onDownloadResults={handleDownloadResults}
            />
          </TabsContent>

          {/* Results Tab */}
          <TabsContent 
            value="results" 
            className="space-y-6"
            id="results-section"
            role="tabpanel"
            aria-labelledby="results-tab"
          >
            {selectedTask ? (
              <ResultsViewer
                task={selectedTask}
                onClose={() => setSelectedTask(null)}
              />
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No results selected</h3>
                  <p className="text-muted-foreground">
                    Select a completed task from the Monitor tab to view results
                  </p>
                  <span className="sr-only" role="status">No results currently selected</span>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </main>
  )
}