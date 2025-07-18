"use client"

import { useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, ArrowLeft, RotateCcw, Edit3 } from 'lucide-react'

interface MarkdownEditorErrorProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function MarkdownEditorError({
  error,
  reset
}: MarkdownEditorErrorProps) {
  const router = useRouter()
  const params = useParams()
  const taskId = params.taskId as string

  useEffect(() => {
    // Log the error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Markdown Editor Error:', error)
    }
  }, [error])

  const handleBack = () => {
    router.push(`/results/${taskId}`)
  }

  const handleRetry = () => {
    reset()
  }

  // Determine error type and provide appropriate message
  const getErrorMessage = () => {
    if (error.message.includes('404') || error.message.includes('not found')) {
      return '任务不存在或已被删除'
    }
    if (error.message.includes('network') || error.message.includes('fetch')) {
      return '网络连接错误，请检查您的网络连接'
    }
    if (error.message.includes('permission') || error.message.includes('unauthorized')) {
      return '您没有权限访问此任务'
    }
    return error.message || '加载Markdown编辑器时发生未知错误'
  }

  const getErrorTitle = () => {
    if (error.message.includes('404') || error.message.includes('not found')) {
      return '任务未找到'
    }
    if (error.message.includes('network') || error.message.includes('fetch')) {
      return '网络错误'
    }
    if (error.message.includes('permission') || error.message.includes('unauthorized')) {
      return '权限错误'
    }
    return 'Markdown编辑器错误'
  }

  const getErrorType = () => {
    if (error.message.includes('404') || error.message.includes('not found')) {
      return 'not-found'
    }
    if (error.message.includes('network') || error.message.includes('fetch')) {
      return 'network'
    }
    if (error.message.includes('permission') || error.message.includes('unauthorized')) {
      return 'permission'
    }
    return 'unknown'
  }

  const shouldShowRetry = () => {
    const errorType = getErrorType()
    return errorType === 'network' || errorType === 'unknown'
  }

  const getErrorVariant = () => {
    const errorType = getErrorType()
    switch (errorType) {
      case 'not-found':
        return 'secondary'
      case 'network':
        return 'destructive'
      case 'permission':
        return 'destructive'
      default:
        return 'destructive'
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-lg shadow-sm border-border">
        <CardHeader className="text-center pb-4">
          <div className="flex items-center justify-center space-x-3 mb-3">
            <Edit3 className="h-6 w-6 text-primary" />
            <CardTitle className="text-lg lg:text-xl text-foreground">Markdown编辑器</CardTitle>
          </div>
          <Badge variant={getErrorVariant()} className="mx-auto text-xs">
            错误
          </Badge>
        </CardHeader>
        
        <CardContent className="text-center space-y-6">
          <div className="flex items-center justify-center">
            <AlertTriangle className="h-12 w-12 text-destructive" />
          </div>
          
          <div className="space-y-3">
            <h3 className="text-lg lg:text-xl font-semibold text-foreground">
              {getErrorTitle()}
            </h3>
            <p className="text-muted-foreground text-sm lg:text-base">
              {getErrorMessage()}
            </p>
          </div>

          {process.env.NODE_ENV === 'development' && error.stack && (
            <details className="text-left">
              <summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                查看技术详情
              </summary>
              <pre className="mt-3 p-3 bg-muted rounded-md text-xs overflow-auto max-h-32 border border-border">
                {error.stack}
              </pre>
            </details>
          )}

          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
            <Button
              variant="outline"
              onClick={handleBack}
              className="flex items-center hover:bg-accent"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回结果页面
            </Button>
            
            {shouldShowRetry() && (
              <Button
                onClick={handleRetry}
                className="flex items-center"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                重试
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}