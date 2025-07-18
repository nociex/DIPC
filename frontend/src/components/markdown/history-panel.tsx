"use client"

import { useCallback, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  History, 
  Clock, 
  FileText, 
  Edit3, 
  RotateCcw, 
  Copy, 
  Import,
  RefreshCw,
  ChevronRight,
  X
} from 'lucide-react'
import type { EditHistoryEntry } from '@/lib/markdown-types'
import { cn } from '@/lib/utils'

interface HistoryPanelProps {
  history: EditHistoryEntry[]
  currentIndex: number
  onSelectEntry: (index: number) => void
  onClose?: () => void
  className?: string
}

export function HistoryPanel({ 
  history, 
  currentIndex, 
  onSelectEntry,
  onClose,
  className 
}: HistoryPanelProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const getOperationIcon = (type: EditHistoryEntry['operationType']) => {
    switch (type) {
      case 'manual':
        return <Edit3 className="h-3.5 w-3.5" />
      case 'paste':
        return <Copy className="h-3.5 w-3.5" />
      case 'undo':
        return <RotateCcw className="h-3.5 w-3.5" />
      case 'redo':
        return <RotateCcw className="h-3.5 w-3.5 scale-x-[-1]" />
      case 'reset':
        return <RefreshCw className="h-3.5 w-3.5" />
      case 'format':
        return <FileText className="h-3.5 w-3.5" />
      case 'import':
        return <Import className="h-3.5 w-3.5" />
      default:
        return <Edit3 className="h-3.5 w-3.5" />
    }
  }

  const getOperationName = (type: EditHistoryEntry['operationType']) => {
    switch (type) {
      case 'manual':
        return '手动编辑'
      case 'paste':
        return '粘贴内容'
      case 'undo':
        return '撤销操作'
      case 'redo':
        return '重做操作'
      case 'reset':
        return '重置内容'
      case 'format':
        return '格式化'
      case 'import':
        return '导入内容'
      default:
        return '编辑'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 60 * 1000) return '刚刚'
    if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))} 分钟前`
    if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))} 小时前`
    
    return date.toLocaleString()
  }

  const handleSelectEntry = useCallback((index: number) => {
    setSelectedIndex(index)
    onSelectEntry(index)
  }, [onSelectEntry])

  return (
    <TooltipProvider>
      <Card className={cn("flex flex-col h-full shadow-sm border-border bg-card", className)}>
        <CardHeader className="pb-3 px-4 py-3 border-b border-border bg-card/50">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base lg:text-lg flex items-center text-foreground">
              <History className="h-4 w-4 mr-2 text-primary" />
              编辑历史
              <Badge variant="secondary" className="ml-2 text-xs">
                {history.length} 条记录
              </Badge>
            </CardTitle>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 space-y-2">
              {history.map((entry, index) => {
                const isCurrent = index === currentIndex
                const isSelected = index === selectedIndex
                const isActive = isCurrent || isSelected
                
                return (
                  <div
                    key={index}
                    className={cn(
                      "rounded-lg border p-3 cursor-pointer transition-all",
                      "hover:bg-accent hover:border-accent-foreground/20",
                      isCurrent && "border-primary bg-primary/5",
                      isSelected && !isCurrent && "bg-accent/50",
                      !isActive && "border-border"
                    )}
                    onClick={() => handleSelectEntry(index)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2 min-w-0 flex-1">
                        <div className={cn(
                          "mt-0.5 p-1.5 rounded",
                          isActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                        )}>
                          {getOperationIcon(entry.operationType)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={cn(
                              "font-medium text-sm",
                              isActive && "text-foreground"
                            )}>
                              {getOperationName(entry.operationType)}
                            </span>
                            {isCurrent && (
                              <Badge variant="default" className="text-xs px-1.5">
                                当前
                              </Badge>
                            )}
                            {entry.description && (
                              <span className="text-xs text-muted-foreground">
                                {entry.description}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span>{formatTime(entry.timestamp)}</span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{entry.timestamp.toLocaleString()}</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <Separator orientation="vertical" className="h-3" />
                            <div className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              <span>{formatFileSize(entry.contentSize)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                      {index !== currentIndex && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 shrink-0"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSelectEntry(index)
                              }}
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>恢复到此版本</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </TooltipProvider>
  )
}