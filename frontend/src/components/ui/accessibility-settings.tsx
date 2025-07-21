"use client"

import React, { useState } from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { useAccessibility } from '@/hooks/use-accessibility'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { 
  Settings, 
  Eye, 
  Volume2, 
  Keyboard, 
  MousePointer,
  Contrast,
  Type,
  Zap,
  Accessibility,
  Monitor,
  Smartphone,
  Tablet
} from 'lucide-react'

interface AccessibilitySettingsProps {
  className?: string
  compact?: boolean
}

export function AccessibilitySettings({ className, compact = false }: AccessibilitySettingsProps) {
  const { t } = useTranslation()
  const { preferences, updatePreferences, responsive } = useAccessibility()
  const [isOpen, setIsOpen] = useState(false)

  // Font size options
  const fontSizeOptions = [
    { value: 'small', label: t('accessibility.fontSize.small'), size: '14px' },
    { value: 'medium', label: t('accessibility.fontSize.medium'), size: '16px' },
    { value: 'large', label: t('accessibility.fontSize.large'), size: '18px' },
    { value: 'extra-large', label: t('accessibility.fontSize.extraLarge'), size: '20px' }
  ]

  // Settings sections
  const settingSections = [
    {
      id: 'visual',
      title: t('accessibility.visual.title'),
      icon: Eye,
      settings: [
        {
          key: 'highContrast',
          label: t('accessibility.highContrast'),
          description: t('accessibility.highContrast.description'),
          type: 'switch' as const,
          value: preferences.highContrast
        },
        {
          key: 'fontSize',
          label: t('accessibility.fontSize'),
          description: t('accessibility.fontSize.description'),
          type: 'select' as const,
          value: preferences.fontSize,
          options: fontSizeOptions
        },
        {
          key: 'reducedMotion',
          label: t('accessibility.reducedMotion'),
          description: t('accessibility.reducedMotion.description'),
          type: 'switch' as const,
          value: preferences.reducedMotion
        },
        {
          key: 'focusVisible',
          label: t('accessibility.focusVisible'),
          description: t('accessibility.focusVisible.description'),
          type: 'switch' as const,
          value: preferences.focusVisible
        }
      ]
    },
    {
      id: 'interaction',
      title: t('accessibility.interaction.title'),
      icon: MousePointer,
      settings: [
        {
          key: 'keyboardNavigation',
          label: t('accessibility.keyboardNavigation'),
          description: t('accessibility.keyboardNavigation.description'),
          type: 'switch' as const,
          value: preferences.keyboardNavigation
        },
        {
          key: 'stickyKeys',
          label: t('accessibility.stickyKeys'),
          description: t('accessibility.stickyKeys.description'),
          type: 'switch' as const,
          value: preferences.stickyKeys
        },
        {
          key: 'slowKeys',
          label: t('accessibility.slowKeys'),
          description: t('accessibility.slowKeys.description'),
          type: 'switch' as const,
          value: preferences.slowKeys
        }
      ]
    },
    {
      id: 'audio',
      title: t('accessibility.audio.title'),
      icon: Volume2,
      settings: [
        {
          key: 'soundEnabled',
          label: t('accessibility.soundEnabled'),
          description: t('accessibility.soundEnabled.description'),
          type: 'switch' as const,
          value: preferences.soundEnabled
        },
        {
          key: 'announcements',
          label: t('accessibility.announcements'),
          description: t('accessibility.announcements.description'),
          type: 'switch' as const,
          value: preferences.announcements
        }
      ]
    }
  ]

  // Handle setting change
  const handleSettingChange = (key: string, value: any) => {
    updatePreferences({ [key]: value })
  }

  // Render setting control
  const renderSettingControl = (setting: any) => {
    switch (setting.type) {
      case 'switch':
        return (
          <Switch
            checked={setting.value}
            onCheckedChange={(checked) => handleSettingChange(setting.key, checked)}
            aria-describedby={`${setting.key}-description`}
          />
        )
      case 'select':
        return (
          <Select
            value={setting.value}
            onValueChange={(value) => handleSettingChange(setting.key, value)}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {setting.options.map((option: any) => (
                <SelectItem key={option.value} value={option.value}>
                  <div className="flex items-center space-x-2">
                    <span>{option.label}</span>
                    {option.size && (
                      <Badge variant="secondary" className="text-xs">
                        {option.size}
                      </Badge>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      default:
        return null
    }
  }

  // Compact toggle button
  if (compact) {
    return (
      <div className={cn("relative", className)}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          className="h-9 w-9 p-0"
          aria-label={t('accessibility.settings.toggle')}
          aria-expanded={isOpen}
        >
          <Accessibility className="h-4 w-4" />
        </Button>
        
        {isOpen && (
          <Card className="absolute top-full right-0 mt-2 w-80 z-50 shadow-lg">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center space-x-2">
                <Accessibility className="h-4 w-4" />
                <span>{t('accessibility.settings.title')}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Quick toggles */}
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={preferences.highContrast ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleSettingChange('highContrast', !preferences.highContrast)}
                  className="justify-start"
                >
                  <Contrast className="h-3 w-3 mr-2" />
                  {t('accessibility.highContrast.short')}
                </Button>
                <Button
                  variant={preferences.reducedMotion ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleSettingChange('reducedMotion', !preferences.reducedMotion)}
                  className="justify-start"
                >
                  <Zap className="h-3 w-3 mr-2" />
                  {t('accessibility.reducedMotion.short')}
                </Button>
              </div>
              
              {/* Font size selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t('accessibility.fontSize')}
                </label>
                <Select
                  value={preferences.fontSize}
                  onValueChange={(value) => handleSettingChange('fontSize', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {fontSizeOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div className="flex items-center justify-between w-full">
                          <span>{option.label}</span>
                          <Badge variant="secondary" className="ml-2 text-xs">
                            {option.size}
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Device info */}
              <div className="pt-2 border-t">
                <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                  {responsive.deviceType === 'mobile' && <Smartphone className="h-3 w-3" />}
                  {responsive.deviceType === 'tablet' && <Tablet className="h-3 w-3" />}
                  {responsive.deviceType === 'desktop' && <Monitor className="h-3 w-3" />}
                  <span>
                    {t(`accessibility.device.${responsive.deviceType}`)} • 
                    {responsive.isTouchDevice ? t('accessibility.touch') : t('accessibility.mouse')}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  // Full settings panel
  return (
    <Card className={cn("w-full max-w-2xl", className)}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Accessibility className="h-5 w-5" />
          <span>{t('accessibility.settings.title')}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {settingSections.map((section, sectionIndex) => {
          const IconComponent = section.icon
          return (
            <div key={section.id}>
              {sectionIndex > 0 && <Separator className="mb-6" />}
              
              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center space-x-2">
                  <IconComponent className="h-4 w-4" />
                  <span>{section.title}</span>
                </h3>
                
                <div className="space-y-4">
                  {section.settings.map((setting) => (
                    <div key={setting.key} className="flex items-center justify-between">
                      <div className="space-y-1 flex-1">
                        <label 
                          htmlFor={setting.key}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          {setting.label}
                        </label>
                        <p 
                          id={`${setting.key}-description`}
                          className="text-xs text-muted-foreground"
                        >
                          {setting.description}
                        </p>
                      </div>
                      <div className="ml-4">
                        {renderSettingControl(setting)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
        
        {/* System detection info */}
        <Separator />
        <div className="space-y-2">
          <h4 className="text-sm font-medium">{t('accessibility.systemDetection')}</h4>
          <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div className="flex items-center space-x-2">
              {responsive.deviceType === 'mobile' && <Smartphone className="h-3 w-3" />}
              {responsive.deviceType === 'tablet' && <Tablet className="h-3 w-3" />}
              {responsive.deviceType === 'desktop' && <Monitor className="h-3 w-3" />}
              <span>{t(`accessibility.device.${responsive.deviceType}`)}</span>
            </div>
            <div>
              <span>{t('accessibility.screenSize')}: {responsive.width}×{responsive.height}</span>
            </div>
            <div>
              <span>{t('accessibility.touchCapability')}: {t(`accessibility.touch.${responsive.touchCapability}`)}</span>
            </div>
            <div>
              <span>{t('accessibility.orientation')}: {t(`accessibility.orientation.${responsive.orientation}`)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}