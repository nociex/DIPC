"use client"

import React, { useState, useCallback, useRef } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { cn } from '@/lib/utils'
import { 
  Upload, 
  FolderPlus, 
  ListPlus,
  Layers
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EnhancedFile, DropPosition, DropZoneType } from './enhanced-drop-zone'

// Drop zone configuration
export interface DropZoneConfig {
  id: string
  type: DropZoneType
  title: string
  description: string
  icon: React.ComponentType<any>
  acceptedTypes?: string[]
  maxFiles?: number
  className?: string
  disabled?: boolean
}

// Multiple drop zones props
export interface MultipleDropZonesProps {
  zones: DropZoneConfig[]
  onFileDrop: (files: EnhancedFile[], dropPosition: DropPosition) => void
  onZoneHover?: (zoneId: string | null, isHovering: boolean) => void
  className?: string
  layout?: 'horizontal' | 'vertical' | 'grid'
  showActiveZone?: boolean
}

// Default drop zone configurations
export const DEFAULT_DROP_ZONES: DropZoneConfig[] = [
  {
    id: 'main',
    type: 'main',
    title: 'upload.dropZone.main.title',
    description: 'upload.dropZone.main.description',
    icon: Upload,
    className: 'border-primary/30 hover:border-primary/60'
  },
  {
    id: 'batch',
    type: 'batch',
    title: 'upload.dropZone.batch.title',
    description: 'upload.dropZone.batch.description',
    icon: Layers,
    className: 'border-blue-300 hover:border-blue-500'
  },
  {
    id: 'queue',
    type: 'queue',
    title: 'upload.dropZone.queue.title',
    description: 'upload.dropZone.queue.description',
    icon: ListPlus,
    className: 'border-green-300 hover:border-green-500'
  },
  {
    id: 'sidebar',
    type: 'sidebar',
    title: 'upload.dropZone.sidebar.title',
    description: 'upload.dropZone.sidebar.description',
    icon: FolderPlus,
    className: 'border-purple-300 hover:border-purple-500'
  }
]

export function MultipleDropZones({
  zones = DEFAULT_DROP_ZONES,
  onFileDrop,
  onZoneHover,
  className,
  layout = 'grid',
  showActiveZone = true
}: MultipleDropZonesProps) {
  const { t } = useTranslation()
  const [activeZone, setActiveZone] = useState<string | null>(null)
  const [dragPosition, setDragPosition] = useState<{ x: number; y: number } | null>(null)
  const dropZoneRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  // Handle drag enter for specific zone
  const handleZoneDragEnter = useCallback((zoneId: string, event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    
    setActiveZone(zoneId)
    setDragPosition({ x: event.clientX, y: event.clientY })
    onZoneHover?.(zoneId, true)
  }, [onZoneHover])

  // Handle drag over for specific zone
  const handleZoneDragOver = useCallback((zoneId: string, event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    
    event.dataTransfer.dropEffect = 'copy'
    setDragPosition({ x: event.clientX, y: event.clientY })
  }, [])

  // Handle drag leave for specific zone
  const handleZoneDragLeave = useCallback((zoneId: string, event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    
    // Only clear if we're actually leaving the zone
    const rect = event.currentTarget.getBoundingClientRect()
    const isLeavingZone = (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
    
    if (isLeavingZone) {
      setActiveZone(null)
      setDragPosition(null)
      onZoneHover?.(null, false)
    }
  }, [onZoneHover])

  // Handle drop for specific zone
  const handleZoneDrop = useCallback((zoneId: string, event: React.DragEvent) => {
    event.preventDefault()
    event.stopPropagation()
    
    setActiveZone(null)
    setDragPosition(null)
    onZoneHover?.(null, false)

    const files = event.dataTransfer?.files
    if (files && files.length > 0) {
      const zone = zones.find(z => z.id === zoneId)
      if (zone) {
        const enhancedFiles: EnhancedFile[] = Array.from(files).map(file => ({
          ...file,
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          uploadStatus: 'pending' as const,
          uploadProgress: 0
        }))

        const dropPosition: DropPosition = {
          x: event.clientX,
          y: event.clientY,
          zone: zone.type,
          element: event.currentTarget as HTMLElement
        }

        onFileDrop(enhancedFiles, dropPosition)
      }
    }
  }, [zones, onFileDrop, onZoneHover])

  // Get layout classes
  const getLayoutClasses = () => {
    switch (layout) {
      case 'horizontal':
        return 'flex flex-row space-x-4 overflow-x-auto'
      case 'vertical':
        return 'flex flex-col space-y-4'
      case 'grid':
      default:
        return 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-4'
    }
  }

  // Render individual drop zone
  const renderDropZone = (zone: DropZoneConfig) => {
    const IconComponent = zone.icon
    const isActive = activeZone === zone.id
    const isDisabled = zone.disabled

    return (
      <Card
        key={zone.id}
        ref={(el) => {
          if (el) {
            dropZoneRefs.current.set(zone.id, el)
          }
        }}
        className={cn(
          "relative border-2 border-dashed transition-all duration-300 cursor-pointer",
          "hover:shadow-md transform hover:scale-105",
          isActive && "border-solid shadow-lg scale-105 bg-primary/5",
          isDisabled && "opacity-50 cursor-not-allowed",
          zone.className,
          layout === 'horizontal' && "min-w-[200px]",
          layout === 'vertical' && "w-full"
        )}
        data-drop-zone={zone.type}
        onDragEnter={(e) => !isDisabled && handleZoneDragEnter(zone.id, e)}
        onDragOver={(e) => !isDisabled && handleZoneDragOver(zone.id, e)}
        onDragLeave={(e) => !isDisabled && handleZoneDragLeave(zone.id, e)}
        onDrop={(e) => !isDisabled && handleZoneDrop(zone.id, e)}
      >
        <CardContent className="p-6 text-center">
          <div className="space-y-3">
            {/* Zone Icon */}
            <div className={cn(
              "mx-auto w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300",
              isActive ? "bg-primary/20 scale-110" : "bg-muted/50"
            )}>
              <IconComponent className={cn(
                "w-6 h-6 transition-colors duration-300",
                isActive ? "text-primary" : "text-muted-foreground"
              )} />
            </div>

            {/* Zone Title */}
            <h3 className={cn(
              "font-semibold transition-colors duration-300",
              isActive ? "text-primary" : "text-foreground"
            )}>
              {t(zone.title as any)}
            </h3>

            {/* Zone Description */}
            <p className="text-sm text-muted-foreground">
              {t(zone.description as any)}
            </p>

            {/* Zone Badge */}
            <Badge 
              variant={isActive ? "default" : "secondary"}
              className="text-xs"
            >
              {t(`upload.dropZone.${zone.type}` as any)}
            </Badge>

            {/* File Constraints */}
            {zone.maxFiles && (
              <p className="text-xs text-muted-foreground">
                {t('upload.maxFiles', { count: zone.maxFiles })}
              </p>
            )}
          </div>

          {/* Active Indicator */}
          {isActive && showActiveZone && (
            <div className="absolute inset-0 border-2 border-primary rounded-lg pointer-events-none">
              <div className="absolute -top-2 -right-2 w-4 h-4 bg-primary rounded-full animate-pulse" />
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={cn("w-full", className)}>
      {/* Drop Zones Grid */}
      <div className={getLayoutClasses()}>
        {zones.map(renderDropZone)}
      </div>

      {/* Active Zone Indicator */}
      {activeZone && dragPosition && showActiveZone && (
        <div
          className="fixed w-6 h-6 bg-primary rounded-full pointer-events-none z-50 transform -translate-x-3 -translate-y-3 animate-pulse"
          style={{
            left: dragPosition.x,
            top: dragPosition.y
          }}
        />
      )}
    </div>
  )
}

// Hook for managing multiple drop zones
export function useMultipleDropZones(
  zones: DropZoneConfig[],
  onFileDrop: (files: EnhancedFile[], dropPosition: DropPosition) => void
) {
  const [activeZone, setActiveZone] = useState<string | null>(null)
  const [isAnyZoneActive, setIsAnyZoneActive] = useState(false)

  const handleZoneHover = useCallback((zoneId: string | null, isHovering: boolean) => {
    setActiveZone(isHovering ? zoneId : null)
    setIsAnyZoneActive(isHovering)
  }, [])

  const handleFileDrop = useCallback((files: EnhancedFile[], dropPosition: DropPosition) => {
    onFileDrop(files, dropPosition)
    setActiveZone(null)
    setIsAnyZoneActive(false)
  }, [onFileDrop])

  return {
    activeZone,
    isAnyZoneActive,
    handleZoneHover,
    handleFileDrop
  }
}