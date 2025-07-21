"use client"

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useResponsive } from '@/hooks/use-responsive'
import { cn } from '@/lib/utils'
import { 
  Upload, 
  FileText, 
  Image, 
  Archive, 
  Plus,
  Camera,
  FolderOpen,
  Smartphone,
  Tablet
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'

// Enhanced file interface for mobile
export interface MobileFile extends File {
  id: string
  preview?: string
  uploadProgress?: number
  uploadStatus?: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
  source?: 'camera' | 'gallery' | 'files' | 'drag'
}

// Touch gesture types
export type TouchGesture = 'tap' | 'long-press' | 'swipe-up' | 'swipe-down' | 'swipe-left' | 'swipe-right'

// Mobile drop zone props
export interface MobileDropZoneProps {
  onFileDrop: (files: MobileFile[]) => void
  onGesture?: (gesture: TouchGesture, files?: MobileFile[]) => void
  acceptedTypes?: string[]
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
  className?: string
  showCameraOption?: boolean
  showGalleryOption?: boolean
}

// Touch event tracking
interface TouchState {
  startX: number
  startY: number
  startTime: number
  currentX: number
  currentY: number
  isLongPress: boolean
  longPressTimer?: NodeJS.Timeout
}

export function MobileDropZone({
  onFileDrop,
  onGesture,
  acceptedTypes = [
    'application/pdf',
    'image/*',
    'application/zip',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  maxFiles = 10,
  maxSize = 100 * 1024 * 1024, // 100MB
  disabled = false,
  className,
  showCameraOption = true,
  showGalleryOption = true
}: MobileDropZoneProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const responsive = useResponsive()
  
  // State management
  const [isDragActive, setIsDragActive] = useState(false)
  const [touchState, setTouchState] = useState<TouchState | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Refs
  const dropZoneRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  
  // Constants for touch gestures
  const LONG_PRESS_DURATION = 500
  const SWIPE_THRESHOLD = 50
  const TAP_THRESHOLD = 10

  // Generate unique ID for files
  const generateFileId = useCallback(() => {
    return `mobile_file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }, [])

  // Process files with mobile-specific enhancements
  const processFiles = useCallback((files: FileList | File[], source: MobileFile['source'] = 'files') => {
    const fileArray = Array.from(files)
    const mobileFiles: MobileFile[] = []

    fileArray.forEach(file => {
      // Validate file size
      if (file.size > maxSize) {
        toast({
          title: t('upload.error.fileSize'),
          description: t('upload.error.fileSizeDescription', { 
            fileName: file.name,
            maxSize: formatFileSize(maxSize) 
          }),
          variant: "destructive",
        })
        return
      }

      // Validate file type
      const isTypeAccepted = acceptedTypes.some(type => {
        if (type.endsWith('/*')) {
          return file.type.startsWith(type.slice(0, -1))
        }
        return file.type === type
      })

      if (!isTypeAccepted) {
        toast({
          title: t('upload.error.fileType'),
          description: t('upload.error.fileTypeDescription', { 
            fileName: file.name,
            fileType: file.type 
          }),
          variant: "destructive",
        })
        return
      }

      const mobileFile: MobileFile = {
        ...file,
        id: generateFileId(),
        uploadStatus: 'pending',
        uploadProgress: 0,
        source,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      }

      mobileFiles.push(mobileFile)
    })

    if (mobileFiles.length > 0) {
      onFileDrop(mobileFiles)
      
      toast({
        title: t('upload.success.filesAdded'),
        description: t('upload.success.filesAddedDescription', { 
          count: mobileFiles.length 
        }),
      })
    }
  }, [acceptedTypes, maxSize, generateFileId, onFileDrop, t, toast])

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }, [])

  // Handle touch start
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled) return

    const touch = e.touches[0]
    const newTouchState: TouchState = {
      startX: touch.clientX,
      startY: touch.clientY,
      startTime: Date.now(),
      currentX: touch.clientX,
      currentY: touch.clientY,
      isLongPress: false
    }

    // Set up long press timer
    newTouchState.longPressTimer = setTimeout(() => {
      setTouchState(prev => prev ? { ...prev, isLongPress: true } : null)
      onGesture?.('long-press')
      
      // Haptic feedback if available
      if ('vibrate' in navigator) {
        navigator.vibrate(50)
      }
    }, LONG_PRESS_DURATION)

    setTouchState(newTouchState)
  }, [disabled, onGesture])

  // Handle touch move
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchState || disabled) return

    const touch = e.touches[0]
    setTouchState(prev => prev ? {
      ...prev,
      currentX: touch.clientX,
      currentY: touch.clientY
    } : null)

    // Cancel long press if moved too much
    const deltaX = Math.abs(touch.clientX - touchState.startX)
    const deltaY = Math.abs(touch.clientY - touchState.startY)
    
    if (deltaX > TAP_THRESHOLD || deltaY > TAP_THRESHOLD) {
      if (touchState.longPressTimer) {
        clearTimeout(touchState.longPressTimer)
      }
    }
  }, [touchState, disabled])

  // Handle touch end
  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchState || disabled) return

    // Clear long press timer
    if (touchState.longPressTimer) {
      clearTimeout(touchState.longPressTimer)
    }

    const deltaX = touchState.currentX - touchState.startX
    const deltaY = touchState.currentY - touchState.startY
    const deltaTime = Date.now() - touchState.startTime
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY)

    // Determine gesture type
    if (touchState.isLongPress) {
      // Long press already handled
    } else if (distance < TAP_THRESHOLD && deltaTime < 300) {
      // Tap gesture
      onGesture?.('tap')
      if (!isExpanded) {
        setIsExpanded(true)
      }
    } else if (distance > SWIPE_THRESHOLD) {
      // Swipe gesture
      const absX = Math.abs(deltaX)
      const absY = Math.abs(deltaY)
      
      if (absX > absY) {
        // Horizontal swipe
        if (deltaX > 0) {
          onGesture?.('swipe-right')
        } else {
          onGesture?.('swipe-left')
        }
      } else {
        // Vertical swipe
        if (deltaY > 0) {
          onGesture?.('swipe-down')
        } else {
          onGesture?.('swipe-up')
          setIsExpanded(true)
        }
      }
    }

    setTouchState(null)
  }, [touchState, disabled, onGesture, isExpanded])

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      processFiles(files, 'files')
    }
    // Reset input
    e.target.value = ''
  }, [processFiles])

  // Handle camera input change
  const handleCameraInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      processFiles(files, 'camera')
    }
    // Reset input
    e.target.value = ''
  }, [processFiles])

  // Handle drag events for desktop fallback
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      setIsDragActive(true)
    }
  }, [disabled])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      setIsDragActive(false)
    }
  }, [disabled])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      e.dataTransfer.dropEffect = 'copy'
    }
  }, [disabled])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (disabled) return

    setIsDragActive(false)
    
    const files = e.dataTransfer.files
    if (files && files.length > 0) {
      processFiles(files, 'drag')
    }
  }, [disabled, processFiles])

  // Get device-specific styling
  const getDeviceStyles = () => {
    switch (responsive.deviceType) {
      case 'mobile':
        return {
          container: "p-4 min-h-[200px]",
          icon: "h-12 w-12",
          title: "text-lg",
          subtitle: "text-sm",
          button: "h-12 text-base"
        }
      case 'tablet':
        return {
          container: "p-6 min-h-[240px]",
          icon: "h-14 w-14",
          title: "text-xl",
          subtitle: "text-base",
          button: "h-14 text-lg"
        }
      default:
        return {
          container: "p-8 min-h-[280px]",
          icon: "h-16 w-16",
          title: "text-2xl",
          subtitle: "text-lg",
          button: "h-16 text-xl"
        }
    }
  }

  const styles = getDeviceStyles()

  // Render mobile-optimized upload options
  const renderUploadOptions = () => {
    if (!isExpanded && responsive.isTouchDevice) {
      return (
        <div className="space-y-4">
          <div className="text-center">
            <Upload className={cn(styles.icon, "mx-auto mb-4 text-muted-foreground")} />
            <p className={cn(styles.title, "font-medium mb-2")}>
              {t('upload.mobile.tapToExpand')}
            </p>
            <p className={cn(styles.subtitle, "text-muted-foreground")}>
              {t('upload.mobile.swipeUpHint')}
            </p>
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {/* Main upload area */}
        <div className="text-center">
          <Upload className={cn(
            styles.icon,
            "mx-auto mb-4 transition-all duration-300",
            isDragActive ? "text-primary scale-110" : "text-muted-foreground"
          )} />
          <p className={cn(styles.title, "font-medium mb-2")}>
            {isDragActive 
              ? t('upload.dropzone.dragHere')
              : responsive.isTouchDevice 
                ? t('upload.mobile.tapToSelect')
                : t('upload.dropzone.title')
            }
          </p>
          <p className={cn(styles.subtitle, "text-muted-foreground mb-4")}>
            {t('upload.dropzone.subtitle')}
          </p>
        </div>

        {/* Mobile-specific upload buttons */}
        {responsive.isTouchDevice && (
          <div className="grid grid-cols-1 gap-3">
            {/* File browser button */}
            <Button
              variant="outline"
              className={cn(styles.button, "w-full justify-start")}
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            >
              <FolderOpen className="mr-3 h-5 w-5" />
              {t('upload.mobile.browseFiles')}
            </Button>

            {/* Camera button (mobile only) */}
            {showCameraOption && responsive.deviceType === 'mobile' && (
              <Button
                variant="outline"
                className={cn(styles.button, "w-full justify-start")}
                onClick={() => cameraInputRef.current?.click()}
                disabled={disabled}
              >
                <Camera className="mr-3 h-5 w-5" />
                {t('upload.mobile.takePhoto')}
              </Button>
            )}

            {/* Gallery button (touch devices) */}
            {showGalleryOption && responsive.isTouchDevice && (
              <Button
                variant="outline"
                className={cn(styles.button, "w-full justify-start")}
                onClick={() => {
                  const input = document.createElement('input')
                  input.type = 'file'
                  input.accept = 'image/*'
                  input.multiple = true
                  input.onchange = (e) => {
                    const files = (e.target as HTMLInputElement).files
                    if (files) processFiles(files, 'gallery')
                  }
                  input.click()
                }}
                disabled={disabled}
              >
                <Image className="mr-3 h-5 w-5" />
                {t('upload.mobile.selectFromGallery')}
              </Button>
            )}
          </div>
        )}

        {/* Desktop fallback button */}
        {!responsive.isTouchDevice && (
          <Button
            variant="outline"
            className={cn(styles.button, "w-full")}
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t('upload.selectFiles')}
          </Button>
        )}

        {/* Device indicator */}
        <div className="flex items-center justify-center space-x-2 text-xs text-muted-foreground">
          {responsive.deviceType === 'mobile' && <Smartphone className="h-3 w-3" />}
          {responsive.deviceType === 'tablet' && <Tablet className="h-3 w-3" />}
          <span>
            {t(`upload.device.${responsive.deviceType}`)} • {t(`upload.touch.${responsive.touchCapability}`)}
          </span>
        </div>
      </div>
    )
  }

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="p-0">
        <div
          ref={dropZoneRef}
          className={cn(
            styles.container,
            "border-2 border-dashed rounded-lg cursor-pointer transition-all duration-300",
            isDragActive
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50",
            disabled && "opacity-50 cursor-not-allowed",
            responsive.isTouchDevice && "touch-manipulation"
          )}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => !responsive.isTouchDevice && fileInputRef.current?.click()}
        >
          {renderUploadOptions()}
        </div>

        {/* Hidden file inputs */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />
        
        {/* Camera input for mobile */}
        {showCameraOption && responsive.deviceType === 'mobile' && (
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleCameraInputChange}
            className="hidden"
          />
        )}
      </CardContent>
    </Card>
  )
}