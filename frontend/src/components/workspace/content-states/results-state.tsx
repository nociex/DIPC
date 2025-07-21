"use client"

import React, { useState } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useWorkspace } from '../workspace-container'
import { ResultsViewer } from '@/components/tasks/results-viewer'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, ArrowLeft } from 'lucide-react'

export function ResultsState() {
  const { t } = useTranslation()
  const { state, actions } = useWorkspace()

  // Handle back navigation
  const handleBack = () => {
    actions.handleViewChange('processing')
  }

  if (!state.selectedTask) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <Card className="max-w-md w-full">
          <CardContent className="p-8 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">
              {t('workspace.results.noSelection')}
            </h3>
            <p className="text-muted-foreground mb-4">
              {t('workspace.results.noSelectionDescription')}
            </p>
            <Button onClick={() => actions.handleViewChange('processing')}>
              {t('workspace.results.selectTask')}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with back button */}
      <div className="flex items-center space-x-4 p-6 border-b">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleBack}
          className="flex items-center space-x-2"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{t('workspace.results.back')}</span>
        </Button>
        <div>
          <h2 className="text-xl font-semibold">
            {t('workspace.results.title')} - {state.selectedTask.id.slice(0, 8)}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t('workspace.results.subtitle')}
          </p>
        </div>
      </div>

      {/* Results viewer */}
      <div className="flex-1 overflow-hidden">
        <ResultsViewer
          task={state.selectedTask}
          onClose={handleBack}
        />
      </div>
    </div>
  )
}