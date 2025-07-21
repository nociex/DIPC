"use client"

import { FileText, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LanguageToggle } from '@/components/ui/language-toggle'
import { useTranslation } from '@/lib/i18n/context'
import { AccessibilitySettings } from '@/components/ui/accessibility-settings'

export function Header() {
  const { t } = useTranslation();

  return (
    <header 
      className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
      role="banner"
    >
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText className="h-6 w-6 text-primary" aria-hidden="true" />
          <h1 className="text-xl font-semibold">
            <a href="/" className="hover:opacity-80 transition-opacity">
              Document Intelligence & Parsing Center
            </a>
          </h1>
        </div>
        
        <nav 
          className="flex items-center space-x-4"
          role="navigation"
          aria-label={t('nav.main')}
          id="main-navigation"
        >
          <LanguageToggle />
          <AccessibilitySettings compact />
          <Button 
            variant="ghost" 
            size="sm"
            aria-label={t('nav.settings')}
          >
            <Settings className="h-4 w-4 mr-2" aria-hidden="true" />
            <span className="hidden sm:inline">{t('nav.settings')}</span>
          </Button>
        </nav>
      </div>
    </header>
  )
}