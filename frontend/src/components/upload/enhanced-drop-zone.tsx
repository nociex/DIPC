"use client"

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { cn, generateClientId } from '@/lib/utils'
import { 
  Upload, 
  FileText, 
  Image, 
  Archive, 
  AlertCircle,
  CheckCircle,
  X,
  Plus
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'

// Enhanced file interface with validation and analysis
export interface EnhancedFile extends File {
  id: string
  preview?: string
  uploadProgress?: number
  uploadStatus?: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
  validationResult?: FileValidationResult
  analysisResult?: FileAnalysisResult
}

// File validation result
export interface FileValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  suggestions: string[]
}

// File analysis result (placeholder for task 3.2)
export interface FileAnalysisResult {
  fileType: string
  suggestedConfig?: any
  estimatedCost?: number
  estimatedTime?: number
  compatibility: 'excellent' | 'good' | 'fair' | 'poor'
}

// Drop zone types
export type DropZoneType = 'main' | 'sidebar' | 'queue' | 'batch'

// Drop position interface
export interface DropPosition {
  x: number
  y: number
  zone: DropZoneType
  element?: HTMLElement
}

// Enhanced drop zone props
export interface EnhancedDropZoneProps {
  onFileDrop: (files: EnhancedFile[], dropPosition: DropPosition) => void
  onFileHover?: (isHovering: boolean, dropPosition?: DropPosition) => void
  acceptedTypes?: string[]
  maxFiles?: number
  maxSize?: number
  dropZoneStyle?: 'full-screen' | 'inline' | 'compact'
  animationDuration?: number
  showDropIndicator?: boolean
  disabled?: boolean
  className?: string
  children?: React.ReactNode
}

// File type configurations
const FILE_TYPE_CONFIG = {
  'application/pdf': { icon: FileText, color: 'text-red-500', category: 'document' },
  'application/msword': { icon: FileText, color: 'text-blue-500', category: 'document' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { 
    icon: FileText, color: 'text-blue-500', category: 'document' 
  },
  'text/plain': { icon: FileText, color: 'text-gray-500', category: 'document' },
  'image/jpeg': { icon: Image, color: 'text-green-500', category: 'image' },
  'image/png': { icon: Image, color: 'text-green-500', category: 'image' },
  'image/gif': { icon: Image, color: 'text-green-500', category: 'image' },
  'image/webp': { icon: Image, color: 'text-green-500', category: 'image' },
  'application/zip': { icon: Archive, color: 'text-purple-500', category: 'archive' },
  'application/x-zip-compressed': { icon: Archive, color: 'text-purple-500', category: 'archive' },
  'application/x-rar-compressed': { icon: Archive, color: 'text-purple-500', category: 'archive' }
} as const

export function EnhancedDropZone({
  onFileDrop,
  onFileHover,
  acceptedTypes = [
    'application/pdf',
    'image/*',
    'application/zip',
    'application/x-zip-compressed',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  maxFiles = 10,
  maxSize = 100 * 1024 * 1024, // 100MB
  dropZoneStyle = 'full-screen',
  animationDuration = 300,
  showDropIndicator = true,
  disabled = false,
  className,
  children
}: EnhancedDropZoneProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  
  // State management
  const [isDragActive, setIsDragActive] = useState(false)
  const [dragPosition, setDragPosition] = useState<DropPosition | null>(null)
  const [dragCounter, setDragCounter] = useState(0)
  const [dropZones, setDropZones] = useState<Map<string, HTMLElement>>(new Map())
  
  // Refs
  const dropZoneRef = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)
  
  // Generate unique ID for files (client-side only to avoid hydration issues)
  const generateFileId = useCallback(() => {
    return generateClientId('file')
  }, [])

  // Validate file against constraints
  const validateFile = useCallback((file: File): FileValidationResult => {
    const errors: string[] = []
    const warnings: string[] = []
    const suggestions: string[] = []

    // Check file size
    if (file.size > maxSize) {
      errors.push(t('upload.error.fileSize', { 
        maxSize: formatFileSize(maxSize) 
      }))
      suggestions.push(t('upload.suggestion.compressFile'))
    }

    // Check file type
    const isTypeAccepted = acceptedTypes.some(type => {
      if (type.endsWith('/*')) {
        return file.type.startsWith(type.slice(0, -1))
      }
      return file.type === type
    })

    if (!isTypeAccepted) {
      errors.push(t('upload.error.fileType', { fileType: file.type }))
      suggestions.push(t('upload.suggestion.convertFile'))
    }

    // Check file name
    if (file.name.length > 255) {
      warnings.push(t('upload.warning.longFileName'))
      suggestions.push(t('upload.suggestion.shortenFileName'))
    }

    // Check for special characters
    if (/[<>:"/\\|?*]/.test(file.name)) {
      warnings.push(t('upload.warning.specialCharacters'))
      suggestions.push(t('upload.suggestion.renameFile'))
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      suggestions
    }
  }, [acceptedTypes, maxSize, t])

  // Format file size for display
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }, [])

  // Get file type configuration
  const getFileTypeConfig = useCallback((file: File) => {
    return FILE_TYPE_CONFIG[file.type as keyof typeof FILE_TYPE_CONFIG] || {
      icon: FileText,
      color: 'text-gray-500',
      category: 'unknown'
    }
  }, [])

  // Process dropped files
  const processFiles = useCallback((files: FileList | File[], dropPosition: DropPosition) => {
    const fileArray = Array.from(files)
    const enhancedFiles: EnhancedFile[] = []

    fileArray.forEach(file => {
      const validationResult = validateFile(file)
      const typeConfig = getFileTypeConfig(file)
      
      const enhancedFile: EnhancedFile = {
        ...file,
        id: generateFileId(),
        uploadStatus: 'pending',
        uploadProgress: 0,
        validationResult,
        preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
      }

      enhancedFiles.push(enhancedFile)

      // Show validation errors/warnings
      if (!validationResult.isValid) {
        validationResult.errors.forEach(error => {
          toast({
            title: t('upload.validation.error'),
            description: `${file.name}: ${error}`,
            variant: "destructive",
          })
        })
      }

      validationResult.warnings.forEach(warning => {
        toast({
          title: t('upload.validation.warning'),
          description: `${file.name}: ${warning}`,
          variant: "default",
        })
      })
    })

    // Filter out invalid files
    const validFiles = enhancedFiles.filter(file => file.validationResult?.isValid)
    
    if (validFiles.length > 0) {
      onFileDrop(validFiles, dropPosition)
      
      toast({
        title: t('upload.success.filesAdded'),
        description: t('upload.success.filesAddedDescription', { 
          count: validFiles.length 
        }),
      })
    }
  }, [validateFile, getFileTypeConfig, generateFileId, onFileDrop, t, toast])

  // Determine drop zone from coordinates
  const getDropZoneFromPosition = useCallback((x: number, y: number): DropPosition => {
    const element = document.elementFromPoint(x, y) as HTMLElement
    
    // Check for specific drop zone types
    let zone: DropZoneType = 'main'
    let targetElement = element

    // Look for drop zone markers in the element hierarchy
    while (targetElement && targetElement !== document.body) {
      if (targetElement.dataset.dropZone) {
        zone = targetElement.dataset.dropZone as DropZoneType
        break
      }
      targetElement = targetElement.parentElement as HTMLElement
    }

    return { x, y, zone, element: targetElement }
  }, [])

  // Handle drag enter
  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (disabled) return

    setDragCounter(prev => prev + 1)
    
    if (dragCounter === 0) {
      setIsDragActive(true)
      const position = getDropZoneFromPosition(e.clientX, e.clientY)
      setDragPosition(position)
      onFileHover?.(true, position)
    }
  }, [disabled, dragCounter, getDropZoneFromPosition, onFileHover])

  // Handle drag over
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (disabled) return

    e.dataTransfer!.dropEffect = 'copy'
    
    const position = getDropZoneFromPosition(e.clientX, e.clientY)
    setDragPosition(position)
    onFileHover?.(true, position)
  }, [disabled, getDropZoneFromPosition, onFileHover])

  // Handle drag leave
  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (disabled) return

    setDragCounter(prev => prev - 1)
    
    if (dragCounter <= 1) {
      setIsDragActive(false)
      setDragPosition(null)
      onFileHover?.(false)
    }
  }, [disabled, dragCounter, onFileHover])

  // Handle drop
  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    if (disabled) return

    setIsDragActive(false)
    setDragCounter(0)
    setDragPosition(null)
    onFileHover?.(false)

    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      const position = getDropZoneFromPosition(e.clientX, e.clientY)
      processFiles(files, position)
    }
  }, [disabled, getDropZoneFromPosition, processFiles, onFileHover])

  // Set up global drag and drop listeners
  useEffect(() => {
    if (dropZoneStyle === 'full-screen') {
      document.addEventListener('dragenter', handleDragEnter)
      document.addEventListener('dragover', handleDragOver)
      document.addEventListener('dragleave', handleDragLeave)
      document.addEventListener('drop', handleDrop)

      return () => {
        document.removeEventListener('dragenter', handleDragEnter)
        document.removeEventListener('dragover', handleDragOver)
        document.removeEventListener('dragleave', handleDragLeave)
        document.removeEventListener('drop', handleDrop)
      }
    }
  }, [dropZoneStyle, handleDragEnter, handleDragOver, handleDragLeave, handleDrop])

  // Render drop indicator overlay
  const renderDropIndicator = () => {
    if (!isDragActive || !showDropIndicator || dropZoneStyle !== 'full-screen') {
      return null
    }

    return (
      <div
        ref={overlayRef}
        className={cn(
          "fixed inset-0 z-50 pointer-events-none",
          "bg-primary/10 backdrop-blur-sm",
          "transition-all duration-300 ease-in-out",
          isDragActive ? "opacity-100" : "opacity-0"
        )}
        style={{ animationDuration: `${animationDuration}ms` }}
      >
        {/* Drop zone indicator */}
        <div className="absolute inset-4 border-4 border-dashed border-primary rounded-2xl flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-24 h-24 mx-auto rounded-full bg-primary/20 flex items-center justify-center">
              <Upload className="w-12 h-12 text-primary animate-bounce" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-primary">
                {t('upload.dropIndicator.title')}
              </h3>
              <p className="text-lg text-primary/80">
                {t('upload.dropIndicator.subtitle')}
              </p>
              {dragPosition && (
                <Badge variant="secondary" className="mt-2">
                  {t(`upload.dropZone.${dragPosition.zone}`)}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Position indicator */}
        {dragPosition && (
          <div
            className="absolute w-4 h-4 bg-primary rounded-full transform -translate-x-2 -translate-y-2 animate-pulse"
            style={{
              left: dragPosition.x,
              top: dragPosition.y
            }}
          />
        )}
      </div>
    )
  }

  // Render inline drop zone
  const renderInlineDropZone = () => {
    if (dropZoneStyle !== 'inline') return null

    return (
      <div
        ref={dropZoneRef}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-300",
          isDragActive
            ? "border-primary bg-primary/5 scale-105"
            : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50",
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
        data-drop-zone="main"
      >
        <Upload className={cn(
          "mx-auto h-12 w-12 mb-4 transition-all duration-300",
          isDragActive ? "text-primary scale-110" : "text-muted-foreground"
        )} />
        <div className="space-y-2">
          <p className="text-lg font-medium">
            {isDragActive 
              ? t('upload.dropzone.dragHere')
              : t('upload.dropzone.title')
            }
          </p>
          <p className="text-sm text-muted-foreground">
            {t('upload.dropzone.subtitle')}
          </p>
        </div>
        {children}
      </div>
    )
  }

  return (
    <>
      {renderDropIndicator()}
      {renderInlineDropZone()}
      {children && dropZoneStyle === 'full-screen' && children}
    </>
  )
}