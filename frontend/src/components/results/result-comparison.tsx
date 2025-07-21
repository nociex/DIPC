"use client"

import { useState, useMemo, useCallback } from 'react'
import { 
  GitCompare, 
  Eye, 
  EyeOff, 
  ChevronDown, 
  ChevronRight, 
  Search, 
  Filter,
  Highlighter,
  Copy,
  Download,
  BarChart3,
  TrendingUp,
  Minus,
  Plus
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { useToast } from '@/components/ui/use-toast'
import { useI18n } from '@/lib/i18n/context'
import type { Task } from '@/types'

interface ResultComparisonProps {
  tasks: Task[]
  onClose?: () => void
  className?: string
}

interface ComparisonResult {
  path: string
  values: { [taskId: string]: any }
  differences: boolean
  type: string
  similarity?: number
}

interface KeyInsight {
  type: 'common' | 'unique' | 'different' | 'missing'
  description: string
  tasks: string[]
  value?: any
  confidence: number
}

interface ComparisonStats {
  totalKeys: number
  commonKeys: number
  uniqueKeys: number
  differentValues: number
  similarity: number
}

export function ResultComparison({ tasks, onClose, className }: ResultComparisonProps) {
  const [selectedTasks, setSelectedTasks] = useState<string[]>(tasks.slice(0, 3).map(t => t.id))
  const [searchQuery, setSearchQuery] = useState('')
  const [showOnlyDifferences, setShowOnlyDifferences] = useState(false)
  const [comparisonMode, setComparisonMode] = useState<'side-by-side' | 'unified' | 'insights'>('side-by-side')
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  const [highlightedKeys, setHighlightedKeys] = useState<Set<string>>(new Set())
  
  const { t } = useI18n()
  const { toast } = useToast()

  // Filter tasks to compare
  const tasksToCompare = useMemo(() => 
    tasks.filter(task => selectedTasks.includes(task.id) && task.results),
    [tasks, selectedTasks]
  )

  // Generate comparison data
  const comparisonData = useMemo(() => {
    if (tasksToCompare.length < 2) return []

    const allPaths = new Set<string>()
    const pathValues: { [path: string]: { [taskId: string]: any } } = {}

    // Extract all paths from all tasks
    tasksToCompare.forEach(task => {
      const extractPaths = (obj: any, currentPath = '') => {
        if (obj === null || obj === undefined) return
        
        if (typeof obj === 'object' && !Array.isArray(obj)) {
          Object.keys(obj).forEach(key => {
            const path = currentPath ? `${currentPath}.${key}` : key
            allPaths.add(path)
            
            if (!pathValues[path]) pathValues[path] = {}
            pathValues[path][task.id] = obj[key]
            
            extractPaths(obj[key], path)
          })
        } else if (Array.isArray(obj)) {
          const path = currentPath || 'root'
          allPaths.add(path)
          if (!pathValues[path]) pathValues[path] = {}
          pathValues[path][task.id] = obj
          
          obj.forEach((item, index) => {
            extractPaths(item, `${path}[${index}]`)
          })
        } else {
          const path = currentPath || 'root'
          allPaths.add(path)
          if (!pathValues[path]) pathValues[path] = {}
          pathValues[path][task.id] = obj
        }
      }

      extractPaths(task.results)
    })

    // Create comparison results
    const results: ComparisonResult[] = Array.from(allPaths).map(path => {
      const values = pathValues[path] || {}
      const taskValues = Object.values(values)
      const uniqueValues = new Set(taskValues.map(v => JSON.stringify(v)))
      
      return {
        path,
        values,
        differences: uniqueValues.size > 1,
        type: typeof taskValues[0],
        similarity: uniqueValues.size === 1 ? 1 : 1 - (uniqueValues.size - 1) / tasksToCompare.length
      }
    })

    return results.sort((a, b) => {
      if (showOnlyDifferences) {
        return b.differences ? 1 : -1
      }
      return a.path.localeCompare(b.path)
    })
  }, [tasksToCompare, showOnlyDifferences])

  // Filter comparison data based on search
  const filteredComparison = useMemo(() => {
    if (!searchQuery) return comparisonData
    
    const query = searchQuery.toLowerCase()
    return comparisonData.filter(item => 
      item.path.toLowerCase().includes(query) ||
      Object.values(item.values).some(value => 
        String(value).toLowerCase().includes(query)
      )
    )
  }, [comparisonData, searchQuery])

  // Generate insights
  const insights = useMemo(() => {
    const insights: KeyInsight[] = []
    
    // Common patterns
    const commonKeys = comparisonData.filter(item => !item.differences)
    if (commonKeys.length > 0) {
      insights.push({
        type: 'common',
        description: `${commonKeys.length} keys have identical values across all documents`,
        tasks: tasksToCompare.map(t => t.id),
        confidence: 0.9
      })
    }

    // Unique values
    const uniqueKeys = comparisonData.filter(item => item.differences)
    if (uniqueKeys.length > 0) {
      insights.push({
        type: 'different',
        description: `${uniqueKeys.length} keys have different values between documents`,
        tasks: tasksToCompare.map(t => t.id),
        confidence: 0.8
      })
    }

    // Missing keys analysis
    tasksToCompare.forEach(task => {
      const missingKeys = comparisonData.filter(item => !(task.id in item.values))
      if (missingKeys.length > 0) {
        insights.push({
          type: 'missing',
          description: `${missingKeys.length} keys are missing from ${task.original_filename || task.id.slice(0, 8)}`,
          tasks: [task.id],
          confidence: 0.7
        })
      }
    })

    return insights.sort((a, b) => b.confidence - a.confidence)
  }, [comparisonData, tasksToCompare])

  // Calculate comparison statistics
  const stats = useMemo((): ComparisonStats => {
    const totalKeys = comparisonData.length
    const commonKeys = comparisonData.filter(item => !item.differences).length
    const uniqueKeys = totalKeys - commonKeys
    const differentValues = comparisonData.filter(item => item.differences).length
    const similarity = totalKeys > 0 ? commonKeys / totalKeys : 0

    return {
      totalKeys,
      commonKeys,
      uniqueKeys,
      differentValues,
      similarity
    }
  }, [comparisonData])

  const togglePath = useCallback((path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev)
      if (newSet.has(path)) {
        newSet.delete(path)
      } else {
        newSet.add(path)
      }
      return newSet
    })
  }, [])

  const toggleHighlight = useCallback((path: string) => {
    setHighlightedKeys(prev => {
      const newSet = new Set(prev)
      if (newSet.has(path)) {
        newSet.delete(path)
      } else {
        newSet.add(path)
      }
      return newSet
    })
  }, [])

  const copyComparison = useCallback(async () => {
    const comparisonText = filteredComparison.map(item => {
      const values = tasksToCompare.map(task => 
        `${task.original_filename || task.id.slice(0, 8)}: ${JSON.stringify(item.values[task.id] || 'N/A')}`
      ).join('\n  ')
      
      return `${item.path}:\n  ${values}`
    }).join('\n\n')

    try {
      await navigator.clipboard.writeText(comparisonText)
      toast({
        title: t('common.success'),
        description: 'Comparison copied to clipboard'
      })
    } catch (error) {
      toast({
        title: t('common.error'),
        description: 'Failed to copy comparison',
        variant: 'destructive'
      })
    }
  }, [filteredComparison, tasksToCompare, toast, t])

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'null'
    if (typeof value === 'string') return `"${value}"`
    if (typeof value === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  const getValueColor = (value: any): string => {
    if (value === null || value === undefined) return 'text-gray-500'
    if (typeof value === 'string') return 'text-red-600'
    if (typeof value === 'number') return 'text-green-600'
    if (typeof value === 'boolean') return 'text-blue-600'
    if (Array.isArray(value)) return 'text-purple-600'
    return 'text-orange-600'
  }

  if (tasksToCompare.length < 2) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center">
          <GitCompare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Select Results to Compare</h3>
          <p className="text-muted-foreground mb-4">
            Choose at least 2 results with data to start comparing
          </p>
          <div className="space-y-2">
            {tasks.map(task => (
              <div key={task.id} className="flex items-center space-x-2">
                <Checkbox
                  id={task.id}
                  checked={selectedTasks.includes(task.id)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedTasks(prev => [...prev, task.id])
                    } else {
                      setSelectedTasks(prev => prev.filter(id => id !== task.id))
                    }
                  }}
                  disabled={!task.results}
                />
                <label htmlFor={task.id} className="text-sm">
                  {task.original_filename || task.id.slice(0, 8) + '...'}
                  {!task.results && <span className="text-muted-foreground"> (no results)</span>}
                </label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              Result Comparison
            </CardTitle>
            <CardDescription>
              Comparing {tasksToCompare.length} results • {stats.similarity.toFixed(1)}% similar
            </CardDescription>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={copyComparison}>
              <Copy className="h-4 w-4 mr-2" />
              Copy
            </Button>
            
            {onClose && (
              <Button variant="outline" size="sm" onClick={onClose}>
                ×
              </Button>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-4 pt-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search keys and values..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="differences-only"
              checked={showOnlyDifferences}
              onCheckedChange={(checked) => setShowOnlyDifferences(checked === true)}
            />
            <label htmlFor="differences-only" className="text-sm">
              Differences only
            </label>
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 text-sm">
          <div className="text-center">
            <div className="font-medium text-lg">{stats.totalKeys}</div>
            <div className="text-muted-foreground">Total Keys</div>
          </div>
          <div className="text-center">
            <div className="font-medium text-lg text-green-600">{stats.commonKeys}</div>
            <div className="text-muted-foreground">Common</div>
          </div>
          <div className="text-center">
            <div className="font-medium text-lg text-orange-600">{stats.differentValues}</div>
            <div className="text-muted-foreground">Different</div>
          </div>
          <div className="text-center">
            <div className="font-medium text-lg text-blue-600">{(stats.similarity * 100).toFixed(1)}%</div>
            <div className="text-muted-foreground">Similarity</div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <Tabs value={comparisonMode} onValueChange={(value: any) => setComparisonMode(value)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="side-by-side">Side by Side</TabsTrigger>
            <TabsTrigger value="unified">Unified View</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="side-by-side" className="mt-4">
            <div className="space-y-2 max-h-96 overflow-auto">
              {filteredComparison.map((item, index) => (
                <div 
                  key={item.path}
                  className={`border rounded-lg p-3 ${
                    highlightedKeys.has(item.path) ? 'bg-yellow-50 border-yellow-200' : ''
                  } ${
                    item.differences ? 'border-orange-200 bg-orange-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => togglePath(item.path)}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        {expandedPaths.has(item.path) ? 
                          <ChevronDown className="h-4 w-4" /> : 
                          <ChevronRight className="h-4 w-4" />
                        }
                      </button>
                      <span className="font-mono text-sm font-medium">{item.path}</span>
                      <Badge variant={item.differences ? 'destructive' : 'secondary'} className="text-xs">
                        {item.differences ? 'Different' : 'Same'}
                      </Badge>
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleHighlight(item.path)}
                    >
                      <Highlighter className="h-4 w-4" />
                    </Button>
                  </div>
                  
                  {expandedPaths.has(item.path) && (
                    <div className="grid gap-2 ml-6">
                      {tasksToCompare.map(task => (
                        <div key={task.id} className="flex items-start space-x-3">
                          <div className="w-32 text-xs text-muted-foreground truncate">
                            {task.original_filename || task.id.slice(0, 8) + '...'}
                          </div>
                          <div className={`font-mono text-sm flex-1 ${getValueColor(item.values[task.id])}`}>
                            {item.values[task.id] !== undefined ? 
                              formatValue(item.values[task.id]) : 
                              <span className="text-gray-400 italic">missing</span>
                            }
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="unified" className="mt-4">
            <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-auto">
              <div className="font-mono text-sm space-y-4">
                {filteredComparison.map(item => (
                  <div key={item.path} className={item.differences ? 'bg-red-50 p-2 rounded' : ''}>
                    <div className="font-medium text-blue-600 mb-1">{item.path}:</div>
                    {tasksToCompare.map(task => (
                      <div key={task.id} className="ml-4 mb-1">
                        <span className="text-gray-600 text-xs">
                          [{task.original_filename || task.id.slice(0, 8)}]
                        </span>
                        <span className={`ml-2 ${getValueColor(item.values[task.id])}`}>
                          {item.values[task.id] !== undefined ? 
                            formatValue(item.values[task.id]) : 
                            <span className="text-gray-400 italic">missing</span>
                          }
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="insights" className="mt-4">
            <div className="space-y-4">
              {insights.map((insight, index) => (
                <Card key={index} className="p-4">
                  <div className="flex items-start space-x-3">
                    <div className={`p-2 rounded-full ${
                      insight.type === 'common' ? 'bg-green-100 text-green-600' :
                      insight.type === 'different' ? 'bg-orange-100 text-orange-600' :
                      insight.type === 'missing' ? 'bg-red-100 text-red-600' :
                      'bg-blue-100 text-blue-600'
                    }`}>
                      {insight.type === 'common' ? <TrendingUp className="h-4 w-4" /> :
                       insight.type === 'different' ? <BarChart3 className="h-4 w-4" /> :
                       insight.type === 'missing' ? <Minus className="h-4 w-4" /> :
                       <Plus className="h-4 w-4" />
                      }
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{insight.description}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {(insight.confidence * 100).toFixed(0)}% confidence
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Affects {insight.tasks.length} document{insight.tasks.length > 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
              
              {insights.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <BarChart3 className="h-12 w-12 mx-auto mb-4" />
                  <p>No significant insights found in the comparison</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}