"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/i18n/context'
import { useResponsive } from '@/hooks/use-responsive'
import { useWorkspace } from './workspace-container'
import { EmptyState } from './content-states/empty-state'
import { UploadingState } from './content-states/uploading-state'
import { ProcessingState } from './content-states/processing-state'
import { ResultsState } from './content-states/results-state'

interface WorkspaceContentProps {
  className?: string
}

export function WorkspaceContent({ className }: WorkspaceContentProps) {
  const { t } = useTranslation()
  const responsive = useResponsive()
  const { state } = useWorkspace()

  // Render content based on current view
  const renderContent = () => {
    switch (state.currentView) {
      case 'empty':
        return <EmptyState />
      case 'uploading':
        return <UploadingState />
      case 'processing':
        return <ProcessingState />
      case 'results':
        return <ResultsState />
      default:
        return <EmptyState />
    }
  }

  return (
    <div 
      className={cn(
        "flex-1 flex flex-col overflow-hidden bg-background",
        // Mobile-specific adjustments
        responsive.isSmallScreen && "min-h-0",
        // Touch-friendly scrolling
        responsive.isTouchDevice && "touch-pan-y",
        className
      )}
      role="main"
      aria-label={t('workspace.content.main')}
    >
      {/* Content area with smooth transitions */}
      <div className={cn(
        "flex-1 relative overflow-hidden",
        // Mobile: ensure proper scrolling
        responsive.isSmallScreen && "overflow-y-auto"
      )}>
        <div className={cn(
          "transition-all duration-300 ease-in-out",
          // Mobile: full height instead of absolute positioning
          responsive.isSmallScreen ? "min-h-full" : "absolute inset-0"
        )}>
          {renderContent()}
        </div>
      </div>
    </div>
  )
}