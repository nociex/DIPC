"use client"

import React, { useState } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { cn } from '@/lib/utils'
import { 
  FileAnalysisResult, 
  FileAnalysisUtils,
  CompatibilityLevel,
  FileCategory 
} from '@/lib/file-analysis'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { 
  FileText, 
  Image, 
  Archive, 
  File,
  Clock,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronDown,
  ChevronRight,
  Zap,
  Shield,
  TrendingUp
} from 'lucide-react'

// Props interface
export interface FileAnalysisDisplayProps {
  analysis: FileAnalysisResult
  fileName: string
  fileSize: number
  onConfigChange?: (config: any) => void
  showDetailedSteps?: boolean
  className?: string
}

// Category icon mapping
const CATEGORY_ICONS = {
  document: FileText,
  image: Image,
  archive: Archive,
  text: FileText,
  unknown: File
} as const

// Compatibility level colors and labels
const COMPATIBILITY_CONFIG = {
  excellent: { color: 'text-green-600 bg-green-50 border-green-200', label: 'Excellent', icon: CheckCircle },
  good: { color: 'text-blue-600 bg-blue-50 border-blue-200', label: 'Good', icon: CheckCircle },
  fair: { color: 'text-yellow-600 bg-yellow-50 border-yellow-200', label: 'Fair', icon: AlertTriangle },
  poor: { color: 'text-red-600 bg-red-50 border-red-200', label: 'Poor', icon: AlertTriangle }
} as const

export function FileAnalysisDisplay({
  analysis,
  fileName,
  fileSize,
  onConfigChange,
  showDetailedSteps = false,
  className
}: FileAnalysisDisplayProps) {
  const { t } = useTranslation()
  const [showSteps, setShowSteps] = useState(showDetailedSteps)
  const [showRecommendations, setShowRecommendations] = useState(false)

  // Get category icon
  const CategoryIcon = CATEGORY_ICONS[analysis.category] || File
  
  // Get compatibility configuration
  const compatibilityConfig = COMPATIBILITY_CONFIG[analysis.compatibility]
  const CompatibilityIcon = compatibilityConfig.icon

  // Handle configuration changes
  const handleConfigChange = (key: string, value: any) => {
    if (onConfigChange) {
      onConfigChange({
        ...analysis.suggestedConfig,
        [key]: value
      })
    }
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-muted">
              <CategoryIcon className="w-5 h-5 text-muted-foreground" />
            </div>
            <div>
              <CardTitle className="text-lg font-semibold truncate">
                {fileName}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {FileAnalysisUtils.formatFileSize(fileSize)} • {analysis.fileType}
              </p>
            </div>
          </div>
          
          {/* Compatibility Badge */}
          <Badge 
            variant="outline" 
            className={cn("border", compatibilityConfig.color)}
          >
            <CompatibilityIcon className="w-3 h-3 mr-1" />
            {compatibilityConfig.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Processing Estimates */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Processing Time */}
          <div className="flex items-center space-x-3 p-3 rounded-lg bg-muted/50">
            <div className="p-2 rounded-full bg-blue-100">
              <Clock className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium">
                {t('upload.analysis.estimatedTime')}
              </p>
              <p className="text-lg font-semibold text-blue-600">
                {FileAnalysisUtils.formatProcessingTime(analysis.estimatedTime)}
              </p>
            </div>
          </div>

          {/* Processing Cost */}
          <div className="flex items-center space-x-3 p-3 rounded-lg bg-muted/50">
            <div className="p-2 rounded-full bg-green-100">
              <DollarSign className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium">
                {t('upload.analysis.estimatedCost')}
              </p>
              <p className="text-lg font-semibold text-green-600">
                {FileAnalysisUtils.formatCost(analysis.estimatedCost)}
              </p>
            </div>
          </div>

          {/* File Complexity */}
          <div className="flex items-center space-x-3 p-3 rounded-lg bg-muted/50">
            <div className="p-2 rounded-full bg-purple-100">
              <TrendingUp className="w-4 h-4 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium">
                {t('upload.analysis.complexity')}
              </p>
              <p className="text-lg font-semibold text-purple-600 capitalize">
                {analysis.metadata.complexity}
              </p>
            </div>
          </div>
        </div>

        {/* Processing Steps */}
        {analysis.processingSteps.length > 0 && (
          <Collapsible open={showSteps} onOpenChange={setShowSteps}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <div className="flex items-center space-x-2">
                  <Zap className="w-4 h-4" />
                  <span className="font-medium">
                    {t('upload.analysis.processingSteps')}
                  </span>
                </div>
                {showSteps ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            
            <CollapsibleContent className="mt-4">
              <div className="space-y-3">
                {analysis.processingSteps.map((step, index) => (
                  <div 
                    key={step.id}
                    className="flex items-center space-x-3 p-3 rounded-lg border"
                  >
                    <div className="flex-shrink-0">
                      <div className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium",
                        step.required 
                          ? "bg-primary text-primary-foreground" 
                          : "bg-muted text-muted-foreground"
                      )}>
                        {index + 1}
                      </div>
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">{step.name}</h4>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm text-muted-foreground">
                            {FileAnalysisUtils.formatProcessingTime(step.estimatedTime)}
                          </span>
                          {!step.required && (
                            <Badge variant="secondary" className="text-xs">
                              {t('upload.analysis.optional')}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {step.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Warnings */}
        {analysis.warnings.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600" />
              <h4 className="font-medium text-yellow-800">
                {t('upload.analysis.warnings')}
              </h4>
            </div>
            <div className="space-y-2">
              {analysis.warnings.map((warning, index) => (
                <div 
                  key={index}
                  className="flex items-start space-x-2 p-3 rounded-lg bg-yellow-50 border border-yellow-200"
                >
                  <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-yellow-800">{warning}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {analysis.recommendations.length > 0 && (
          <Collapsible open={showRecommendations} onOpenChange={setShowRecommendations}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between p-0 h-auto">
                <div className="flex items-center space-x-2">
                  <Info className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-800">
                    {t('upload.analysis.recommendations')}
                  </span>
                </div>
                {showRecommendations ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </Button>
            </CollapsibleTrigger>
            
            <CollapsibleContent className="mt-4">
              <div className="space-y-2">
                {analysis.recommendations.map((recommendation, index) => (
                  <div 
                    key={index}
                    className="flex items-start space-x-2 p-3 rounded-lg bg-blue-50 border border-blue-200"
                  >
                    <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-blue-800">{recommendation}</p>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Configuration Preview */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-green-600" />
            <h4 className="font-medium text-green-800">
              {t('upload.analysis.suggestedConfig')}
            </h4>
          </div>
          
          <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-green-50 border border-green-200">
            <div>
              <p className="text-sm font-medium text-green-800">
                {t('upload.config.vectorization')}
              </p>
              <p className="text-sm text-green-700">
                {analysis.suggestedConfig.enable_vectorization 
                  ? t('common.enabled') 
                  : t('common.disabled')
                }
              </p>
            </div>
            
            <div>
              <p className="text-sm font-medium text-green-800">
                {t('upload.config.storage')}
              </p>
              <p className="text-sm text-green-700 capitalize">
                {analysis.suggestedConfig.storage_policy}
              </p>
            </div>
            
            <div>
              <p className="text-sm font-medium text-green-800">
                {t('upload.config.costLimit')}
              </p>
              <p className="text-sm text-green-700">
                {FileAnalysisUtils.formatCost(analysis.suggestedConfig.max_cost_limit || 0)}
              </p>
            </div>
            
            <div>
              <p className="text-sm font-medium text-green-800">
                {t('upload.config.provider')}
              </p>
              <p className="text-sm text-green-700 uppercase">
                {analysis.suggestedConfig.llm_provider}
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-4 border-t">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setShowRecommendations(!showRecommendations)}
          >
            {showRecommendations 
              ? t('upload.analysis.hideRecommendations')
              : t('upload.analysis.showRecommendations')
            }
          </Button>
          
          <Button 
            size="sm"
            onClick={() => onConfigChange?.(analysis.suggestedConfig)}
          >
            {t('upload.analysis.useConfig')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}