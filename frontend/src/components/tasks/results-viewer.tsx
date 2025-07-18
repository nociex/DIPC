"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Copy, Download, Eye, EyeOff, ChevronDown, ChevronRight, Edit3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { TaskStatusChecker } from '@/lib/task-status-checker'
import type { Task } from '@/types'

interface ResultsViewerProps {
  task: Task
  onDownload?: (task: Task) => void
  className?: string
}

interface JsonViewerProps {
  data: any
  level?: number
  expanded?: boolean
}

function JsonViewer({ data, level = 0, expanded = true }: JsonViewerProps) {
  const [isExpanded, setIsExpanded] = useState(expanded)
  
  if (data === null) {
    return <span className="text-gray-500">null</span>
  }
  
  if (typeof data === 'boolean') {
    return <span className="text-blue-600">{data.toString()}</span>
  }
  
  if (typeof data === 'number') {
    return <span className="text-green-600">{data}</span>
  }
  
  if (typeof data === 'string') {
    return <span className="text-red-600">&quot;{data}&quot;</span>
  }
  
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="text-gray-500">[]</span>
    }
    
    return (
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center text-gray-600 hover:text-gray-800"
        >
          {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          <span className="ml-1">[{data.length} items]</span>
        </button>
        {isExpanded && (
          <div className="ml-4 border-l border-gray-200 pl-4 mt-1">
            {data.map((item, index) => (
              <div key={index} className="py-1">
                <span className="text-gray-500 text-sm">{index}: </span>
                <JsonViewer data={item} level={level + 1} expanded={level < 2} />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  
  if (typeof data === 'object') {
    const keys = Object.keys(data)
    if (keys.length === 0) {
      return <span className="text-gray-500">{'{}'}</span>
    }
    
    return (
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center text-gray-600 hover:text-gray-800"
        >
          {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          <span className="ml-1">{'{'}...{'}'} ({keys.length} keys)</span>
        </button>
        {isExpanded && (
          <div className="ml-4 border-l border-gray-200 pl-4 mt-1">
            {keys.map((key) => (
              <div key={key} className="py-1">
                <span className="text-purple-600 font-medium">&quot;{key}&quot;</span>
                <span className="text-gray-500">: </span>
                <JsonViewer data={data[key]} level={level + 1} expanded={level < 1} />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  
  return <span className="text-gray-500">{String(data)}</span>
}

export function ResultsViewer({ task, onDownload, className }: ResultsViewerProps) {
  const [viewMode, setViewMode] = useState<'formatted' | 'raw'>('formatted')
  const [showMetadata, setShowMetadata] = useState(true)
  const { toast } = useToast()
  const router = useRouter()

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: "Copied to clipboard",
        description: "Results have been copied to your clipboard",
      })
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Failed to copy results to clipboard",
        variant: "destructive",
      })
    }
  }

  const formatTaskType = (taskType: string) => {
    return taskType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const handleMarkdownEdit = () => {
    router.push(`/results/${task.id}/markdown`)
  }

  if (!task.results) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center">
          <div className="space-y-3">
            <Eye className="h-12 w-12 text-muted-foreground mx-auto" />
            <div>
              <h3 className="text-lg font-medium">No results available</h3>
              <p className="text-muted-foreground">
                This task hasn&apos;t completed yet or has no results to display
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const resultsJson = JSON.stringify(task.results, null, 2)

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Task Results</CardTitle>
            <CardDescription>
              {formatTaskType(task.task_type)} - {task.id.slice(0, 8)}...
            </CardDescription>
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewMode(viewMode === 'formatted' ? 'raw' : 'formatted')}
            >
              {viewMode === 'formatted' ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
              {viewMode === 'formatted' ? 'Raw' : 'Formatted'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => copyToClipboard(resultsJson)}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            {TaskStatusChecker.shouldShowMarkdownButton(task) && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleMarkdownEdit}
                title="Edit results as Markdown"
              >
                <Edit3 className="h-4 w-4 mr-2" />
                Markdown编辑
              </Button>
            )}
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDownload(task)}
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            )}
          </div>
        </div>

        {/* Task Metadata Toggle */}
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowMetadata(!showMetadata)}
            className="text-xs"
          >
            {showMetadata ? <ChevronDown className="h-3 w-3 mr-1" /> : <ChevronRight className="h-3 w-3 mr-1" />}
            Task Details
          </Button>
        </div>

        {/* Task Metadata */}
        {showMetadata && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg text-sm">
            <div>
              <span className="text-muted-foreground">Status:</span>
              <p className="font-medium capitalize">{task.status}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Created:</span>
              <p className="font-medium">{formatDate(task.created_at)}</p>
            </div>
            {task.completed_at && (
              <div>
                <span className="text-muted-foreground">Completed:</span>
                <p className="font-medium">{formatDate(task.completed_at)}</p>
              </div>
            )}
            {task.actual_cost && (
              <div>
                <span className="text-muted-foreground">Cost:</span>
                <p className="font-medium">${task.actual_cost.toFixed(3)}</p>
              </div>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {viewMode === 'formatted' ? (
            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
              <div className="font-mono text-sm">
                <JsonViewer data={task.results} />
              </div>
            </div>
          ) : (
            <div className="bg-gray-900 text-green-400 rounded-lg p-4 max-h-96 overflow-auto">
              <pre className="font-mono text-sm whitespace-pre-wrap">
                {resultsJson}
              </pre>
            </div>
          )}

          {/* Results Summary */}
          {task.results && typeof task.results === 'object' && (
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-2">Results Summary</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Data Type:</span>
                  <p className="font-medium">
                    {Array.isArray(task.results) ? 'Array' : 'Object'}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Size:</span>
                  <p className="font-medium">
                    {Array.isArray(task.results) 
                      ? `${task.results.length} items`
                      : `${Object.keys(task.results).length} keys`
                    }
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">JSON Size:</span>
                  <p className="font-medium">
                    {(new Blob([resultsJson]).size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}