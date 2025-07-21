"use client"

import { useState, useEffect } from 'react'
import { AlertTriangle, DollarSign, Settings, Info } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import type { TaskOptions } from '@/types'
import { StoragePolicy } from '@/types'
import { useAnnouncements } from '@/hooks/use-accessibility'

interface TaskConfigPanelProps {
  options: TaskOptions
  onChange: (config: TaskOptions) => void
  fileCount?: number
  estimatedFileSize?: number
  className?: string
}

interface CostEstimate {
  estimatedTokens: number
  estimatedCost: number
  breakdown: {
    parsing: number
    vectorization: number
  }
}

export function TaskConfigPanel({
  options,
  onChange,
  fileCount = 0,
  estimatedFileSize = 0,
  className
}: TaskConfigPanelProps) {
  const [config, setConfig] = useState<TaskOptions>(options)

  const [costEstimate, setCostEstimate] = useState<CostEstimate>({
    estimatedTokens: 0,
    estimatedCost: 0,
    breakdown: { parsing: 0, vectorization: 0 }
  })

  const { toast } = useToast()
  const { announce } = useAnnouncements()

  // Cost calculation constants (approximate)
  const COST_PER_1K_TOKENS = 0.002 // $0.002 per 1K tokens for GPT-4
  const TOKENS_PER_KB = 300 // Rough estimate
  const VECTORIZATION_MULTIPLIER = 0.3 // Additional cost for vectorization

  useEffect(() => {
    calculateCostEstimate()
  }, [fileCount, estimatedFileSize, config.enable_vectorization])

  useEffect(() => {
    onChange(config)
  }, [config, onChange])

  const calculateCostEstimate = () => {
    if (fileCount === 0 || estimatedFileSize === 0) {
      setCostEstimate({
        estimatedTokens: 0,
        estimatedCost: 0,
        breakdown: { parsing: 0, vectorization: 0 }
      })
      return
    }

    const fileSizeKB = estimatedFileSize / 1024
    const estimatedTokens = fileSizeKB * TOKENS_PER_KB
    const parsingCost = (estimatedTokens / 1000) * COST_PER_1K_TOKENS
    const vectorizationCost = config.enable_vectorization
      ? parsingCost * VECTORIZATION_MULTIPLIER
      : 0
    const totalCost = parsingCost + vectorizationCost

    setCostEstimate({
      estimatedTokens: Math.round(estimatedTokens),
      estimatedCost: totalCost,
      breakdown: {
        parsing: parsingCost,
        vectorization: vectorizationCost
      }
    })
  }

  const handleVectorizationToggle = (enabled: boolean) => {
    setConfig((prev: TaskOptions) => ({ ...prev, enable_vectorization: enabled }))

    const message = enabled 
      ? "Vectorization enabled. Documents will be processed for semantic search capabilities"
      : "Vectorization disabled. Processing costs will be reduced, but semantic search won't be available"
      
    if (enabled) {
      toast({
        title: "Vectorization enabled",
        description: "Documents will be processed for semantic search capabilities",
      })
    } else {
      toast({
        title: "Vectorization disabled",
        description: "Processing costs will be reduced, but semantic search won't be available",
      })
    }
    
    announce(message)
  }

  const handleStoragePolicyChange = (policy: string) => {
    const storagePolicy = policy === 'permanent' ? StoragePolicy.PERMANENT : StoragePolicy.TEMPORARY
    setConfig((prev: TaskOptions) => ({ ...prev, storage_policy: storagePolicy }))

    const message = policy === 'permanent'
      ? "Storage policy updated. Files will be stored permanently"
      : "Storage policy updated. Files will be automatically deleted after processing"
      
    toast({
      title: `Storage policy updated`,
      description: policy === 'permanent'
        ? "Files will be stored permanently"
        : "Files will be automatically deleted after processing",
    })
    
    announce(message)
  }

  const handleCostLimitChange = (limit: number) => {
    setConfig((prev: TaskOptions) => ({ ...prev, max_cost_limit: limit }))
    announce(`Maximum cost limit set to $${limit}`)
  }

  const isOverCostLimit = costEstimate.estimatedCost > (config.max_cost_limit || 0)

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Settings className="h-5 w-5" />
          <span>Processing Configuration</span>
        </CardTitle>
        <CardDescription>
          Configure how your documents will be processed and stored
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Vectorization Toggle */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <label htmlFor="vectorization-toggle" className="text-sm font-medium">
                Enable Vectorization
              </label>
              <p id="vectorization-description" className="text-xs text-muted-foreground">
                Process documents for semantic search and AI-powered queries
              </p>
            </div>
            <Switch
              id="vectorization-toggle"
              checked={config.enable_vectorization}
              onCheckedChange={handleVectorizationToggle}
              aria-describedby="vectorization-description"
            />
          </div>

          {config.enable_vectorization && (
            <div className="flex items-start space-x-2 p-3 bg-blue-50 rounded-lg border border-blue-200" role="note">
              <Info className="h-4 w-4 text-blue-600 mt-0.5" aria-hidden="true" />
              <div className="text-xs text-blue-800">
                <p className="font-medium">Vectorization Benefits:</p>
                <ul className="mt-1 list-disc list-inside space-y-0.5">
                  <li>Semantic search capabilities</li>
                  <li>AI-powered document queries</li>
                  <li>Content similarity analysis</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Storage Policy Selection */}
        <div className="space-y-3">
          <div className="space-y-1">
            <label htmlFor="storage-policy" className="text-sm font-medium">
              Storage Policy
            </label>
            <p id="storage-policy-description" className="text-xs text-muted-foreground">
              Choose how long processed files should be stored
            </p>
          </div>

          <Select
            value={config.storage_policy}
            onValueChange={handleStoragePolicyChange}
          >
            <SelectTrigger id="storage-policy" aria-describedby="storage-policy-description">
              <SelectValue placeholder="Select storage policy" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="permanent">
                <div className="flex flex-col">
                  <span className="font-medium">Permanent Storage</span>
                  <span className="text-xs text-muted-foreground">
                    Files stored indefinitely
                  </span>
                </div>
              </SelectItem>
              <SelectItem value="temporary">
                <div className="flex flex-col">
                  <span className="font-medium">Temporary Storage</span>
                  <span className="text-xs text-muted-foreground">
                    Files deleted after 7 days
                  </span>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Cost Limit Setting */}
        <div className="space-y-3">
          <div className="space-y-1">
            <label id="cost-limit-label" className="text-sm font-medium">
              Maximum Cost Limit
            </label>
            <p id="cost-limit-description" className="text-xs text-muted-foreground">
              Set a spending limit for processing these documents
            </p>
          </div>

          <div className="flex space-x-2" role="group" aria-labelledby="cost-limit-label" aria-describedby="cost-limit-description">
            {[5, 10, 25, 50].map((limit) => (
              <Button
                key={limit}
                variant={config.max_cost_limit === limit ? "default" : "outline"}
                size="sm"
                onClick={() => handleCostLimitChange(limit)}
                aria-pressed={config.max_cost_limit === limit}
                aria-label={`Set maximum cost limit to $${limit}`}
              >
                ${limit}
              </Button>
            ))}
          </div>
        </div>

        {/* Cost Estimation Display */}
        {fileCount > 0 && (
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-4 w-4" />
              <span className="text-sm font-medium">Cost Estimation</span>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg space-y-3" role="region" aria-label="Cost estimation details">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Files to process:</span>
                <span className="text-sm font-medium">{fileCount}</span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Estimated tokens:</span>
                <span className="text-sm font-medium">
                  {costEstimate.estimatedTokens.toLocaleString()}
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Document parsing:</span>
                  <span className="text-sm font-medium">
                    ${costEstimate.breakdown.parsing.toFixed(3)}
                  </span>
                </div>

                {config.enable_vectorization && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Vectorization:</span>
                    <span className="text-sm font-medium">
                      ${costEstimate.breakdown.vectorization.toFixed(3)}
                    </span>
                  </div>
                )}
              </div>

              <div className="border-t pt-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">Total estimated cost:</span>
                  <span className={`text-sm font-bold ${isOverCostLimit ? 'text-red-600' : 'text-green-600'
                    }`}>
                    ${costEstimate.estimatedCost.toFixed(3)}
                  </span>
                </div>
              </div>

              {isOverCostLimit && (
                <div 
                  className="flex items-start space-x-2 p-3 bg-red-50 rounded border border-red-200"
                  role="alert"
                  aria-live="assertive"
                >
                  <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5" aria-hidden="true" />
                  <div className="text-xs text-red-800">
                    <p className="font-medium">Cost limit exceeded!</p>
                    <p>
                      Estimated cost (${costEstimate.estimatedCost.toFixed(3)}) exceeds
                      your limit of ${config.max_cost_limit?.toFixed(2)}.
                      Consider reducing files or increasing the limit.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}