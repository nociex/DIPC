"use client"

import React from 'react'
import { useTranslation } from '@/lib/i18n/context'
import { cn } from '@/lib/utils'

interface SkipLink {
  id: string
  href: string
  label: string
}

interface SkipLinksProps {
  className?: string
  links?: SkipLink[]
}

export function SkipLinks({ className, links }: SkipLinksProps) {
  const { t } = useTranslation()
  
  // Default skip links if none provided
  const defaultLinks: SkipLink[] = [
    {
      id: 'skip-to-main',
      href: '#main-content',
      label: t('accessibility.skipLinks.main')
    },
    {
      id: 'skip-to-navigation',
      href: '#main-navigation',
      label: t('accessibility.skipLinks.navigation')
    },
    {
      id: 'skip-to-upload',
      href: '#upload-section',
      label: t('accessibility.skipLinks.upload')
    },
    {
      id: 'skip-to-results',
      href: '#results-section',
      label: t('accessibility.skipLinks.results')
    }
  ]
  
  const skipLinks = links || defaultLinks
  
  return (
    <nav
      className={cn("sr-only focus-within:not-sr-only", className)}
      aria-label={t('accessibility.skipLinks.label')}
    >
      <ul className="flex flex-col space-y-2 p-4 bg-background border-b">
        {skipLinks.map((link) => (
          <li key={link.id}>
            <a
              href={link.href}
              className={cn(
                "skip-link inline-block px-4 py-2 rounded-md",
                "bg-primary text-primary-foreground",
                "focus:not-sr-only focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                "hover:bg-primary/90 transition-colors"
              )}
              onClick={(e) => {
                // Smooth scroll to target
                e.preventDefault()
                const target = document.querySelector(link.href)
                if (target) {
                  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  // Focus the target element if it's focusable
                  if (target instanceof HTMLElement && target.tabIndex !== -1) {
                    target.focus()
                  }
                }
              }}
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}

// Individual skip link component for custom usage
interface SkipLinkProps {
  href: string
  children: React.ReactNode
  className?: string
}

export function SkipLink({ href, children, className }: SkipLinkProps) {
  return (
    <a
      href={href}
      className={cn(
        "skip-link",
        "sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50",
        "px-4 py-2 bg-primary text-primary-foreground rounded-md shadow-lg",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        className
      )}
      onClick={(e) => {
        e.preventDefault()
        const target = document.querySelector(href)
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' })
          if (target instanceof HTMLElement && target.tabIndex !== -1) {
            target.focus()
          }
        }
      }}
    >
      {children}
    </a>
  )
}