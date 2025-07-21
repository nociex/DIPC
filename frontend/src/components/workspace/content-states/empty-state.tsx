"use client"

import React, { useRef } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useResponsive } from '@/hooks/use-responsive'
import { useWorkspace } from '../workspace-container'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EnhancedDropZone, EnhancedFile, DropPosition } from '@/components/upload/enhanced-drop-zone'
import { MobileDropZone, MobileFile } from '@/components/upload/mobile-drop-zone'
import { MultipleDropZones, DEFAULT_DROP_ZONES, useMultipleDropZones } from '@/components/upload/multiple-drop-zones'
import { 
  Upload, 
  FileText, 
  Image, 
  Archive,
  Zap,
  Shield,
  Globe,
  ArrowRight
} from 'lucide-react'

const SUPPORTED_FORMATS = [
  { type: 'Documents', icon: FileText, formats: ['PDF', 'DOC', 'DOCX', 'TXT'] },
  { type: 'Images', icon: Image, formats: ['JPG', 'PNG', 'GIF', 'WEBP'] },
  { type: 'Archives', icon: Archive, formats: ['ZIP', 'RAR', '7Z'] }
]

const FEATURES = [
  {
    icon: Zap,
    title: 'workspace.empty.features.fast.title' as const,
    description: 'workspace.empty.features.fast.description' as const
  },
  {
    icon: Shield,
    title: 'workspace.empty.features.secure.title' as const,
    description: 'workspace.empty.features.secure.description' as const
  },
  {
    icon: Globe,
    title: 'workspace.empty.features.multilingual.title' as const,
    description: 'workspace.empty.features.multilingual.description' as const
  }
]

export function EmptyState() {
  const { t } = useTranslation()
  const responsive = useResponsive()
  const { actions } = useWorkspace()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Handle enhanced file drop
  const handleEnhancedFileDrop = (files: EnhancedFile[], dropPosition: DropPosition) => {
    // Convert enhanced files back to regular files for workspace compatibility
    const regularFiles = files.map(file => {
      const { id, validationResult, analysisResult, ...regularFile } = file
      return regularFile as File
    })
    
    actions.handleFilesSelected(regularFiles)
  }

  // Handle mobile file drop
  const handleMobileFileDrop = (files: MobileFile[]) => {
    // Convert mobile files back to regular files for workspace compatibility
    const regularFiles = files.map(file => {
      const { id, source, ...regularFile } = file
      return regularFile as File
    })
    
    actions.handleFilesSelected(regularFiles)
  }

  // Handle file selection from input
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (files.length > 0) {
      actions.handleFilesSelected(files)
    }
  }

  // Multiple drop zones configuration for empty state
  const dropZones = DEFAULT_DROP_ZONES.slice(0, 2) // Only show main and batch zones

  // Use multiple drop zones hook
  const { activeZone, isAnyZoneActive, handleZoneHover, handleFileDrop } = useMultipleDropZones(
    dropZones,
    handleEnhancedFileDrop
  )

  return (
    <div className="h-full flex flex-col">
      {/* Enhanced Drop Zone Overlay */}
      <EnhancedDropZone
        onFileDrop={handleEnhancedFileDrop}
        dropZoneStyle="full-screen"
        showDropIndicator={true}
        animationDuration={300}
      />

      {/* Hero Section */}
      <div className={cn(
        "flex-1 flex items-center justify-center",
        responsive.isSmallScreen ? "p-4" : "p-8"
      )}>
        <div className={cn(
          "w-full",
          responsive.isSmallScreen ? "max-w-sm" : responsive.isMediumScreen ? "max-w-2xl" : "max-w-4xl"
        )}>
          {/* Main Drop Zone - Mobile vs Desktop */}
          {responsive.isTouchDevice ? (
            <MobileDropZone
              onFileDrop={handleMobileFileDrop}
              showCameraOption={responsive.deviceType === 'mobile'}
              showGalleryOption={true}
              className="mb-6"
            />
          ) : (
            <Card 
              className="border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 transition-colors duration-200 cursor-pointer group"
              onClick={() => fileInputRef.current?.click()}
              data-drop-zone="main"
            >
              <CardContent className={cn(
                "text-center",
                responsive.isSmallScreen ? "p-6" : "p-12"
              )}>
                <div className="space-y-6">
                  {/* Upload Icon */}
                  <div className={cn(
                    "mx-auto rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors",
                    responsive.isSmallScreen ? "w-16 h-16" : "w-24 h-24"
                  )}>
                    <Upload className={cn(
                      "text-primary group-hover:scale-110 transition-transform",
                      responsive.isSmallScreen ? "w-8 h-8" : "w-12 h-12"
                    )} />
                  </div>

                  {/* Main Message */}
                  <div className="space-y-2">
                    <h2 className={cn(
                      "font-bold text-foreground",
                      responsive.isSmallScreen ? "text-xl" : "text-3xl"
                    )}>
                      {t('workspace.empty.title')}
                    </h2>
                    <p className={cn(
                      "text-muted-foreground mx-auto",
                      responsive.isSmallScreen ? "text-base max-w-sm" : "text-lg max-w-2xl"
                    )}>
                      {t('workspace.empty.subtitle')}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                    <Button 
                      size={responsive.isSmallScreen ? "default" : "lg"}
                      className={responsive.isSmallScreen ? "px-6" : "px-8"}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="w-5 h-5 mr-2" />
                      {t('workspace.empty.selectFiles')}
                    </Button>
                    <p className="text-sm text-muted-foreground">
                      {t('workspace.empty.orDragDrop')}
                    </p>
                  </div>

                  {/* Supported Formats */}
                  <div className="pt-6">
                    <p className="text-sm text-muted-foreground mb-4">
                      {t('workspace.empty.supportedFormats')}
                    </p>
                    <div className={cn(
                      "flex flex-wrap justify-center",
                      responsive.isSmallScreen ? "gap-3" : "gap-6"
                    )}>
                      {SUPPORTED_FORMATS.map((category) => {
                        const IconComponent = category.icon
                        return (
                          <div key={category.type} className="flex items-center space-x-2">
                            <IconComponent className="w-5 h-5 text-muted-foreground" />
                            <div className="flex space-x-1">
                              {category.formats.map((format) => (
                                <Badge key={format} variant="secondary" className="text-xs">
                                  {format}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Multiple Drop Zones Section */}
          <div className="mt-8">
            <div className="text-center mb-6">
              <h3 className="text-xl font-semibold mb-2">
                {t('workspace.empty.dropZones.title')}
              </h3>
              <p className="text-muted-foreground">
                {t('workspace.empty.dropZones.subtitle')}
              </p>
            </div>
            
            <MultipleDropZones
              zones={dropZones}
              onFileDrop={handleFileDrop}
              onZoneHover={handleZoneHover}
              layout="horizontal"
              showActiveZone={true}
              className="justify-center"
            />
          </div>

          {/* Features Section */}
          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map((feature, index) => {
              const IconComponent = feature.icon
              return (
                <Card key={index} className="border-0 shadow-none bg-muted/30">
                  <CardContent className="p-6 text-center">
                    <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <IconComponent className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="font-semibold mb-2">
                      {t(feature.title)}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {t(feature.description)}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Quick Start Guide */}
          <Card className="mt-8 bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-6">
              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <Zap className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">
                    {t('workspace.empty.quickStart.title')}
                  </h3>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center space-x-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                      <span>{t('workspace.empty.quickStart.step1')}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                      <span>{t('workspace.empty.quickStart.step2')}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                      <span>{t('workspace.empty.quickStart.step3')}</span>
                    </div>
                  </div>
                  <Button variant="link" className="p-0 h-auto mt-3 text-primary">
                    {t('workspace.empty.quickStart.learnMore')}
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileSelect}
        accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.webp,.zip,.rar,.7z"
      />
    </div>
  )
}