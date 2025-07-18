import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Card, CardContent } from '@/components/ui/card'
import { Edit3 } from 'lucide-react'

export default function MarkdownEditorLoading() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-sm border-border">
        <CardContent className="p-6 lg:p-8 text-center space-y-6">
          <div className="flex items-center justify-center space-x-3">
            <Edit3 className="h-6 w-6 text-primary" />
            <h2 className="text-lg lg:text-xl font-semibold text-foreground">Markdown编辑器</h2>
          </div>
          <div className="space-y-4">
            <LoadingSpinner message="正在加载编辑器..." />
            <div className="text-sm text-muted-foreground space-y-2">
              <p>正在准备Markdown编辑器...</p>
              <p className="text-xs">请稍候片刻</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}