import { AlertTriangle, ArrowLeft, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

interface ErrorDisplayProps {
  title: string
  message: string
  onRetry?: () => void
  onBack?: () => void
  showDetails?: boolean
  details?: string
  className?: string
}

export function ErrorDisplay({
  title,
  message,
  onRetry,
  onBack,
  showDetails = false,
  details,
  className
}: ErrorDisplayProps) {
  return (
    <div className={cn(
      "min-h-screen flex items-center justify-center p-4",
      className
    )}>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle className="text-xl">{title}</CardTitle>
          <CardDescription className="text-base">
            {message}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <div className="flex flex-col space-y-2">
            {onRetry && (
              <Button onClick={onRetry} className="w-full">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
            )}
            
            {onBack && (
              <Button variant="outline" onClick={onBack} className="w-full">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Go Back
              </Button>
            )}
          </div>

          {showDetails && details && (
            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-full">
                  Show Error Details
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="rounded-md bg-gray-100 p-3">
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap overflow-auto max-h-32">
                    {details}
                  </pre>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </CardContent>
      </Card>
    </div>
  )
}