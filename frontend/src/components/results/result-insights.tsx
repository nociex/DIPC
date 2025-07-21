"use client"

import { useState, useMemo } from 'react'
import { 
  Lightbulb, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Info,
  Star,
  BarChart3,
  Target,
  Zap,
  Eye,
  ChevronDown,
  ChevronRight
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useI18n } from '@/lib/i18n/context'
import { ResultAnalyzer, type ResultSummary, type KeyInformation } from '@/lib/result-analyzer'
import type { Task } from '@/types'

interface ResultInsightsProps {
  task: Task
  onClose?: () => void
  className?: string
}

export function ResultInsights({ task, onClose, className }: ResultInsightsProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['overview']))
  const [selectedInsight, setSelectedInsight] = useState<string | null>(null)
  
  const { t } = useI18n()

  // Generate analysis
  const summary = useMemo(() => ResultAnalyzer.generateSummary(task), [task])
  const keyInformation = useMemo(() => ResultAnalyzer.extractKeyInformation(task.results), [task.results])
  const dataQuality = useMemo(() => ResultAnalyzer.analyzeDataQuality(task.results), [task.results])

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(section)) {
        newSet.delete(section)
      } else {
        newSet.add(section)
      }
      return newSet
    })
  }

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'pattern': return <TrendingUp className="h-4 w-4" />
      case 'anomaly': return <AlertTriangle className="h-4 w-4" />
      case 'trend': return <BarChart3 className="h-4 w-4" />
      case 'highlight': return <Star className="h-4 w-4" />
      default: return <Info className="h-4 w-4" />
    }
  }

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'pattern': return 'text-blue-600 bg-blue-50'
      case 'anomaly': return 'text-orange-600 bg-orange-50'
      case 'trend': return 'text-green-600 bg-green-50'
      case 'highlight': return 'text-purple-600 bg-purple-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'critical': return <AlertTriangle className="h-4 w-4 text-red-500" />
      case 'important': return <Star className="h-4 w-4 text-orange-500" />
      case 'informational': return <Info className="h-4 w-4 text-blue-500" />
      default: return <Info className="h-4 w-4 text-gray-500" />
    }
  }

  const formatProcessingTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  if (!task.results) {
    return (
      <Card className={className}>
        <CardContent className="p-8 text-center">
          <Lightbulb className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No Results to Analyze</h3>
          <p className="text-muted-foreground">
            Process the document first to generate insights and analysis
          </p>
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
              <Lightbulb className="h-5 w-5" />
              Result Insights
            </CardTitle>
            <CardDescription>
              AI-powered analysis of {task.original_filename || task.id.slice(0, 8) + '...'}
            </CardDescription>
          </div>
          
          {onClose && (
            <Button variant="outline" size="sm" onClick={onClose}>
              ×
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="summary" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
            <TabsTrigger value="key-info">Key Info</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="mt-4 space-y-4">
            {/* Overview */}
            <Card>
              <CardHeader className="pb-3">
                <button
                  onClick={() => toggleSection('overview')}
                  className="flex items-center justify-between w-full text-left"
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Overview
                  </CardTitle>
                  {expandedSections.has('overview') ? 
                    <ChevronDown className="h-4 w-4" /> : 
                    <ChevronRight className="h-4 w-4" />
                  }
                </button>
              </CardHeader>
              {expandedSections.has('overview') && (
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {summary.overview}
                  </p>
                </CardContent>
              )}
            </Card>

            {/* Data Structure */}
            <Card>
              <CardHeader className="pb-3">
                <button
                  onClick={() => toggleSection('structure')}
                  className="flex items-center justify-between w-full text-left"
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" />
                    Data Structure
                  </CardTitle>
                  {expandedSections.has('structure') ? 
                    <ChevronDown className="h-4 w-4" /> : 
                    <ChevronRight className="h-4 w-4" />
                  }
                </button>
              </CardHeader>
              {expandedSections.has('structure') && (
                <CardContent className="pt-0">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Type:</span>
                      <p className="font-medium capitalize">{summary.dataStructure.type}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Size:</span>
                      <p className="font-medium">{summary.dataStructure.size} elements</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Depth:</span>
                      <p className="font-medium">{summary.dataStructure.depth} levels</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Complexity:</span>
                      <Badge variant={
                        summary.dataStructure.complexity === 'high' ? 'destructive' :
                        summary.dataStructure.complexity === 'medium' ? 'default' : 'secondary'
                      }>
                        {summary.dataStructure.complexity}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Key Findings */}
            <Card>
              <CardHeader className="pb-3">
                <button
                  onClick={() => toggleSection('findings')}
                  className="flex items-center justify-between w-full text-left"
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Key Findings
                  </CardTitle>
                  {expandedSections.has('findings') ? 
                    <ChevronDown className="h-4 w-4" /> : 
                    <ChevronRight className="h-4 w-4" />
                  }
                </button>
              </CardHeader>
              {expandedSections.has('findings') && (
                <CardContent className="pt-0">
                  <ul className="space-y-2">
                    {summary.keyFindings.map((finding, index) => (
                      <li key={index} className="flex items-start space-x-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span>{finding}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              )}
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader className="pb-3">
                <button
                  onClick={() => toggleSection('recommendations')}
                  className="flex items-center justify-between w-full text-left"
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <Zap className="h-4 w-4" />
                    Recommendations
                  </CardTitle>
                  {expandedSections.has('recommendations') ? 
                    <ChevronDown className="h-4 w-4" /> : 
                    <ChevronRight className="h-4 w-4" />
                  }
                </button>
              </CardHeader>
              {expandedSections.has('recommendations') && (
                <CardContent className="pt-0">
                  <ul className="space-y-2">
                    {summary.recommendations.map((recommendation, index) => (
                      <li key={index} className="flex items-start space-x-2 text-sm">
                        <Lightbulb className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                        <span>{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              )}
            </Card>
          </TabsContent>

          <TabsContent value="insights" className="mt-4">
            <div className="space-y-4">
              {summary.insights.map((insight, index) => (
                <Card 
                  key={index} 
                  className={`cursor-pointer transition-colors ${
                    selectedInsight === insight.description ? 'ring-2 ring-blue-500' : ''
                  }`}
                  onClick={() => setSelectedInsight(
                    selectedInsight === insight.description ? null : insight.description
                  )}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start space-x-3">
                      <div className={`p-2 rounded-full ${getInsightColor(insight.type)}`}>
                        {getInsightIcon(insight.type)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <Badge variant="outline" className="text-xs capitalize">
                            {insight.type}
                          </Badge>
                          <div className="flex items-center space-x-1">
                            <span className="text-xs text-muted-foreground">
                              {(insight.confidence * 100).toFixed(0)}% confidence
                            </span>
                            <div className="w-12 h-1 bg-gray-200 rounded-full">
                              <div 
                                className="h-1 bg-blue-500 rounded-full"
                                style={{ width: `${insight.confidence * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                        <p className="text-sm">{insight.description}</p>
                        {insight.data && selectedInsight === insight.description && (
                          <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono">
                            {JSON.stringify(insight.data, null, 2)}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {summary.insights.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Lightbulb className="h-12 w-12 mx-auto mb-4" />
                  <p>No specific insights detected in this result</p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="key-info" className="mt-4">
            <div className="space-y-3">
              {keyInformation.map((info, index) => (
                <Card key={index}>
                  <CardContent className="p-4">
                    <div className="flex items-start space-x-3">
                      {getCategoryIcon(info.category)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-sm text-blue-600 truncate">
                            {info.path}
                          </span>
                          <div className="flex items-center space-x-2">
                            <Badge variant={
                              info.category === 'critical' ? 'destructive' :
                              info.category === 'important' ? 'default' : 'secondary'
                            } className="text-xs">
                              {info.category}
                            </Badge>
                            <div className="w-16 h-1 bg-gray-200 rounded-full">
                              <div 
                                className="h-1 bg-green-500 rounded-full"
                                style={{ width: `${info.importance * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground mb-2">
                          {info.description}
                        </p>
                        <div className="bg-gray-50 rounded p-2 text-xs font-mono">
                          {typeof info.value === 'object' 
                            ? JSON.stringify(info.value, null, 2)
                            : String(info.value)
                          }
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {keyInformation.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Target className="h-12 w-12 mx-auto mb-4" />
                  <p>No key information identified in this result</p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="quality" className="mt-4">
            <div className="space-y-6">
              {/* Quality Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-green-600 mb-1">
                      {(dataQuality.completeness * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">Completeness</div>
                    <Progress value={dataQuality.completeness * 100} className="h-2" />
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-blue-600 mb-1">
                      {(dataQuality.consistency * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">Consistency</div>
                    <Progress value={dataQuality.consistency * 100} className="h-2" />
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4 text-center">
                    <div className="text-2xl font-bold text-purple-600 mb-1">
                      {(dataQuality.accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">Accuracy</div>
                    <Progress value={dataQuality.accuracy * 100} className="h-2" />
                  </CardContent>
                </Card>
              </div>

              {/* Processing Metadata */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Processing Metadata</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Processing Time:</span>
                      <p className="font-medium">{formatProcessingTime(summary.metadata.processingTime)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Data Quality:</span>
                      <p className="font-medium">{(summary.metadata.dataQuality * 100).toFixed(1)}%</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Completeness:</span>
                      <p className="font-medium">{(summary.metadata.completeness * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Quality Issues */}
              {dataQuality.issues.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Quality Issues</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {dataQuality.issues.map((issue, index) => (
                        <div key={index} className="flex items-start space-x-3">
                          <AlertTriangle className={`h-4 w-4 mt-0.5 ${
                            issue.severity === 'high' ? 'text-red-500' :
                            issue.severity === 'medium' ? 'text-orange-500' : 'text-yellow-500'
                          }`} />
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <Badge variant={
                                issue.severity === 'high' ? 'destructive' :
                                issue.severity === 'medium' ? 'default' : 'secondary'
                              } className="text-xs">
                                {issue.severity}
                              </Badge>
                              <span className="text-xs text-muted-foreground capitalize">
                                {issue.type.replace('_', ' ')}
                              </span>
                            </div>
                            <p className="text-sm">{issue.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}