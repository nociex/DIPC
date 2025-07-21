"use client"

import { useState, useMemo, useCallback } from 'react'
import { Search, Eye, EyeOff, ChevronDown, ChevronRight, Copy, Download, Share2, Filter, Maximize2, Minimize2, GitCompare, History, Lightbulb } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { useI18n } from '@/lib/i18n/context'
import { ShareDialog } from './share-dialog'
import { ResultComparison } from './result-comparison'
import { ResultHistory } from './result-history'
import { ResultInsights } from './result-insights'
import { ExportService } from '@/lib/export-service'
import type { Task } from '@/types'

interface EnhancedResultsViewerProps {
  task: Task
  relatedTasks?: Task[]
  onDownload?: (task: Task) => void
  onShare?: (task: Task) => void
  onClose?: () => void
  className?: string
}

type ViewMode = 'preview' | 'detailed' | 'raw'
type FilterType = 'all' | 'text' | 'numbers' | 'objects' | 'arrays'

interface SearchResult {
  path: string
  value: any
  context: string
  type: string
}

interface ExpandableJsonViewerProps {
  data: any
  path?: string
  level?: number
  expanded?: boolean
  searchQuery?: string
  onPathClick?: (path: string) => void
}

function ExpandableJsonViewer({ 
  data, 
  path = '', 
  level = 0, 
  expanded = true, 
  searchQuery = '',
  onPathClick 
}: ExpandableJsonViewerProps) {
  const [isExpanded, setIsExpanded] = useState(expanded)
  
  const isHighlighted = useMemo(() => {
    if (!searchQuery) return false
    const searchLower = searchQuery.toLowerCase()
    return (
      path.toLowerCase().includes(searchLower) ||
      String(data).toLowerCase().includes(searchLower)
    )
  }, [data, path, searchQuery])
  
  const getValueType = (value: any): string => {
    if (value === null) return 'null'
    if (Array.isArray(value)) return 'array'
    return typeof value
  }
  
  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'string': return 'text-red-600'
      case 'number': return 'text-green-600'
      case 'boolean': return 'text-blue-600'
      case 'null': return 'text-gray-500'
      case 'array': return 'text-purple-600'
      case 'object': return 'text-orange-600'
      default: return 'text-gray-600'
    }
  }
  
  const highlightText = (text: string): React.ReactNode => {
    if (!searchQuery) return text
    
    const regex = new RegExp(`(${searchQuery})`, 'gi')
    const parts = text.split(regex)
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">
          {part}
        </mark>
      ) : part
    )
  }
  
  if (data === null) {
    return (
      <span className={`${getTypeColor('null')} ${isHighlighted ? 'bg-yellow-100 px-1 rounded' : ''}`}>
        null
      </span>
    )
  }
  
  if (typeof data === 'boolean') {
    return (
      <span className={`${getTypeColor('boolean')} ${isHighlighted ? 'bg-yellow-100 px-1 rounded' : ''}`}>
        {highlightText(data.toString())}
      </span>
    )
  }
  
  if (typeof data === 'number') {
    return (
      <span className={`${getTypeColor('number')} ${isHighlighted ? 'bg-yellow-100 px-1 rounded' : ''}`}>
        {highlightText(data.toString())}
      </span>
    )
  }
  
  if (typeof data === 'string') {
    return (
      <span className={`${getTypeColor('string')} ${isHighlighted ? 'bg-yellow-100 px-1 rounded' : ''}`}>
        &quot;{highlightText(data)}&quot;
      </span>
    )
  }
  
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="text-gray-500">[]</span>
    }
    
    return (
      <div className={isHighlighted ? 'bg-yellow-100 p-1 rounded' : ''}>
        <div className="flex items-center">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
          >
            {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            <span className="ml-1 text-purple-600 font-medium">
              [{data.length} items]
            </span>
          </button>
          {onPathClick && (
            <span
              onClick={(e) => {
                e.stopPropagation()
                onPathClick(path)
              }}
              className="ml-2 text-xs text-blue-500 hover:text-blue-700 cursor-pointer"
            >
              {path}
            </span>
          )}
        </div>
        {isExpanded && (
          <div className="ml-4 border-l border-gray-200 pl-4 mt-1">
            {data.map((item, index) => (
              <div key={index} className="py-1">
                <span className="text-gray-500 text-sm">{index}: </span>
                <ExpandableJsonViewer 
                  data={item} 
                  path={`${path}[${index}]`}
                  level={level + 1} 
                  expanded={level < 2}
                  searchQuery={searchQuery}
                  onPathClick={onPathClick}
                />
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
      <div className={isHighlighted ? 'bg-yellow-100 p-1 rounded' : ''}>
        <div className="flex items-center">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center text-gray-600 hover:text-gray-800 transition-colors"
          >
            {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            <span className="ml-1 text-orange-600 font-medium">
              {'{'}...{'}'} ({keys.length} keys)
            </span>
          </button>
          {onPathClick && (
            <span
              onClick={(e) => {
                e.stopPropagation()
                onPathClick(path)
              }}
              className="ml-2 text-xs text-blue-500 hover:text-blue-700 cursor-pointer"
            >
              {path}
            </span>
          )}
        </div>
        {isExpanded && (
          <div className="ml-4 border-l border-gray-200 pl-4 mt-1">
            {keys.map((key) => (
              <div key={key} className="py-1">
                <span className="text-purple-600 font-medium">&quot;{highlightText(key)}&quot;</span>
                <span className="text-gray-500">: </span>
                <ExpandableJsonViewer 
                  data={data[key]} 
                  path={path ? `${path}.${key}` : key}
                  level={level + 1} 
                  expanded={level < 1}
                  searchQuery={searchQuery}
                  onPathClick={onPathClick}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }
  
  return (
    <span className={`text-gray-500 ${isHighlighted ? 'bg-yellow-100 px-1 rounded' : ''}`}>
      {highlightText(String(data))}
    </span>
  )
}

export function EnhancedResultsViewer({ 
  task, 
  relatedTasks = [],
  onDownload, 
  onShare, 
  onClose, 
  className 
}: EnhancedResultsViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('preview')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<FilterType>('all')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [showShareDialog, setShowShareDialog] = useState(false)
  const [showComparison, setShowComparison] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  
  const { t } = useI18n()
  const { toast } = useToast()

  // Search functionality
  const searchResults = useMemo(() => {
    if (!searchQuery || !task.results) return []
    
    const results: SearchResult[] = []
    const searchLower = searchQuery.toLowerCase()
    
    const searchInObject = (obj: any, path: string = '') => {
      if (obj === null || obj === undefined) return
      
      if (typeof obj === 'string' || typeof obj === 'number' || typeof obj === 'boolean') {
        if (String(obj).toLowerCase().includes(searchLower)) {
          results.push({
            path,
            value: obj,
            context: String(obj).substring(0, 100),
            type: typeof obj
          })
        }
      } else if (Array.isArray(obj)) {
        obj.forEach((item, index) => {
          searchInObject(item, `${path}[${index}]`)
        })
      } else if (typeof obj === 'object') {
        Object.keys(obj).forEach(key => {
          if (key.toLowerCase().includes(searchLower)) {
            results.push({
              path: `${path}.${key}`,
              value: obj[key],
              context: `Key: ${key}`,
              type: 'key'
            })
          }
          searchInObject(obj[key], path ? `${path}.${key}` : key)
        })
      }
    }
    
    searchInObject(task.results)
    return results
  }, [searchQuery, task.results])

  // Filter results based on type
  const filteredResults = useMemo(() => {
    if (filterType === 'all') return searchResults
    
    return searchResults.filter(result => {
      switch (filterType) {
        case 'text': return result.type === 'string'
        case 'numbers': return result.type === 'number'
        case 'objects': return result.type === 'object'
        case 'arrays': return Array.isArray(result.value)
        default: return true
      }
    })
  }, [searchResults, filterType])

  const copyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: t('common.success'),
        description: "Results copied to clipboard",
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: "Failed to copy to clipboard",
        variant: "destructive",
      })
    }
  }, [toast, t])

  const handlePathClick = useCallback((path: string) => {
    setSelectedPath(path)
    setSearchQuery(path)
  }, [])

  if (!task.results) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center">
          <div className="space-y-3">
            <Eye className="h-12 w-12 text-muted-foreground mx-auto" />
            <div>
              <h3 className="text-lg font-medium">{t('results.noResults')}</h3>
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
    <Card className={`${className} ${isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {t('results.title')}
              <Badge variant="outline">{task.task_type}</Badge>
            </CardTitle>
            <CardDescription>
              {task.original_filename || task.id.slice(0, 8) + '...'}
            </CardDescription>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => copyToClipboard(resultsJson)}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            
            {onDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDownload(task)}
              >
                <Download className="h-4 w-4 mr-2" />
                {t('common.download')}
              </Button>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowShareDialog(true)}
            >
              <Share2 className="h-4 w-4 mr-2" />
              {t('common.share')}
            </Button>

            {relatedTasks.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowComparison(true)}
              >
                <GitCompare className="h-4 w-4 mr-2" />
                Compare
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowHistory(true)}
            >
              <History className="h-4 w-4 mr-2" />
              History
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowInsights(true)}
            >
              <Lightbulb className="h-4 w-4 mr-2" />
              Insights
            </Button>
            
            {onClose && (
              <Button
                variant="outline"
                size="sm"
                onClick={onClose}
              >
                ×
              </Button>
            )}
          </div>
        </div>

        {/* Search and Filter Controls */}
        <div className="flex items-center space-x-4 pt-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder={t('results.search.placeholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <Select value={filterType} onValueChange={(value: FilterType) => setFilterType(value)}>
            <SelectTrigger className="w-32">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="text">Text</SelectItem>
              <SelectItem value="numbers">Numbers</SelectItem>
              <SelectItem value="objects">Objects</SelectItem>
              <SelectItem value="arrays">Arrays</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Search Results Summary */}
        {searchQuery && (
          <div className="flex items-center justify-between text-sm text-muted-foreground pt-2">
            <span>
              {filteredResults.length} result{filteredResults.length !== 1 ? 's' : ''} found
            </span>
            {selectedPath && (
              <Badge variant="secondary" className="text-xs">
                Path: {selectedPath}
              </Badge>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent>
        <Tabs value={viewMode} onValueChange={(value) => setViewMode(value as ViewMode)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="preview">{t('results.view.preview')}</TabsTrigger>
            <TabsTrigger value="detailed">{t('results.view.detailed')}</TabsTrigger>
            <TabsTrigger value="raw">{t('results.view.raw')}</TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="mt-4">
            <div className="space-y-4">
              {/* Search Results */}
              {searchQuery && filteredResults.length > 0 && (
                <div className="bg-blue-50 rounded-lg p-4 max-h-64 overflow-auto">
                  <h4 className="font-medium mb-2">Search Results</h4>
                  <div className="space-y-2">
                    {filteredResults.slice(0, 10).map((result, index) => (
                      <div key={index} className="border-l-2 border-blue-200 pl-3">
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => handlePathClick(result.path)}
                            className="text-sm font-mono text-blue-600 hover:text-blue-800"
                          >
                            {result.path}
                          </button>
                          <Badge variant="outline" className="text-xs">
                            {result.type}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 truncate">
                          {result.context}
                        </p>
                      </div>
                    ))}
                    {filteredResults.length > 10 && (
                      <p className="text-sm text-gray-500 text-center">
                        ... and {filteredResults.length - 10} more results
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Enhanced JSON Viewer */}
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
                <div className="font-mono text-sm">
                  <ExpandableJsonViewer 
                    data={task.results}
                    searchQuery={searchQuery}
                    onPathClick={handlePathClick}
                  />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="detailed" className="mt-4">
            <div className="space-y-4">
              {/* Task Metadata */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg text-sm">
                <div>
                  <span className="text-muted-foreground">Status:</span>
                  <p className="font-medium capitalize">{task.status}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Created:</span>
                  <p className="font-medium">{new Date(task.created_at).toLocaleString()}</p>
                </div>
                {task.completed_at && (
                  <div>
                    <span className="text-muted-foreground">Completed:</span>
                    <p className="font-medium">{new Date(task.completed_at).toLocaleString()}</p>
                  </div>
                )}
                {task.actual_cost && (
                  <div>
                    <span className="text-muted-foreground">Cost:</span>
                    <p className="font-medium">${task.actual_cost.toFixed(3)}</p>
                  </div>
                )}
              </div>

              {/* Results Analysis */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium mb-3">Results Analysis</h4>
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

              {/* Detailed JSON View with Search */}
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
                <div className="font-mono text-sm">
                  <ExpandableJsonViewer 
                    data={task.results}
                    searchQuery={searchQuery}
                    onPathClick={handlePathClick}
                    expanded={false}
                  />
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="raw" className="mt-4">
            <div className="bg-gray-900 text-green-400 rounded-lg p-4 max-h-96 overflow-auto">
              <pre className="font-mono text-sm whitespace-pre-wrap">
                {resultsJson}
              </pre>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>

      {/* Share Dialog */}
      {showShareDialog && (
        <ShareDialog
          task={task}
          isOpen={showShareDialog}
          onClose={() => setShowShareDialog(false)}
        />
      )}

      {/* Comparison Dialog */}
      {showComparison && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-6xl max-h-[90vh] overflow-auto">
            <ResultComparison
              tasks={[task, ...relatedTasks]}
              onClose={() => setShowComparison(false)}
              className="bg-white"
            />
          </div>
        </div>
      )}

      {/* History Dialog */}
      {showHistory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-auto">
            <ResultHistory
              task={task}
              onClose={() => setShowHistory(false)}
              className="bg-white"
            />
          </div>
        </div>
      )}

      {/* Insights Dialog */}
      {showInsights && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-auto">
            <ResultInsights
              task={task}
              onClose={() => setShowInsights(false)}
              className="bg-white"
            />
          </div>
        </div>
      )}
    </Card>
  )
}