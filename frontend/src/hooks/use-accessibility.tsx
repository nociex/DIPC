"use client"

import { useState, useEffect, useCallback, useRef } from 'react'
import { useResponsive } from './use-responsive'

// Accessibility preferences
export interface AccessibilityPreferences {
  // Visual preferences
  highContrast: boolean
  reducedMotion: boolean
  fontSize: 'small' | 'medium' | 'large' | 'extra-large'
  
  // Interaction preferences
  keyboardNavigation: boolean
  screenReader: boolean
  focusVisible: boolean
  
  // Audio preferences
  soundEnabled: boolean
  announcements: boolean
  
  // Motor preferences
  stickyKeys: boolean
  slowKeys: boolean
  mouseKeys: boolean
}

// Focus management
export interface FocusManager {
  currentFocusIndex: number
  focusableElements: HTMLElement[]
  trapFocus: boolean
  restoreFocus: boolean
  previousFocus?: HTMLElement
}

// Screen reader announcements
export interface AnnouncementOptions {
  priority: 'polite' | 'assertive'
  delay?: number
  clear?: boolean
}

// Keyboard navigation
export interface KeyboardNavigation {
  currentIndex: number
  elements: HTMLElement[]
  direction: 'horizontal' | 'vertical' | 'grid'
  wrap: boolean
  skipDisabled: boolean
}

export function useAccessibility() {
  const responsive = useResponsive()
  
  // Accessibility preferences state
  const [preferences, setPreferences] = useState<AccessibilityPreferences>(() => {
    if (typeof window === 'undefined') {
      return {
        highContrast: false,
        reducedMotion: false,
        fontSize: 'medium',
        keyboardNavigation: true,
        screenReader: false,
        focusVisible: true,
        soundEnabled: true,
        announcements: true,
        stickyKeys: false,
        slowKeys: false,
        mouseKeys: false
      }
    }

    // Load from localStorage or detect system preferences
    const saved = localStorage.getItem('accessibility-preferences')
    const defaultPrefs = {
      highContrast: window.matchMedia('(prefers-contrast: high)').matches,
      reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      fontSize: 'medium' as const,
      keyboardNavigation: true,
      screenReader: detectScreenReader(),
      focusVisible: true,
      soundEnabled: !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
      announcements: true,
      stickyKeys: false,
      slowKeys: false,
      mouseKeys: false
    }

    return saved ? { ...defaultPrefs, ...JSON.parse(saved) } : defaultPrefs
  })

  // Focus management state
  const [focusManager, setFocusManager] = useState<FocusManager>({
    currentFocusIndex: -1,
    focusableElements: [],
    trapFocus: false,
    restoreFocus: false
  })

  // Announcement queue
  const [announcementQueue, setAnnouncementQueue] = useState<string[]>([])
  const announcementRef = useRef<HTMLDivElement>(null)

  // Detect screen reader
  function detectScreenReader(): boolean {
    if (typeof window === 'undefined') return false
    
    // Check for common screen reader indicators
    const indicators = [
      'speechSynthesis' in window,
      navigator.userAgent.includes('NVDA'),
      navigator.userAgent.includes('JAWS'),
      navigator.userAgent.includes('VoiceOver'),
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ]
    
    return indicators.some(Boolean)
  }

  // Update preferences
  const updatePreferences = useCallback((updates: Partial<AccessibilityPreferences>) => {
    setPreferences(prev => {
      const newPrefs = { ...prev, ...updates }
      localStorage.setItem('accessibility-preferences', JSON.stringify(newPrefs))
      return newPrefs
    })
  }, [])

  // Apply accessibility styles to document
  useEffect(() => {
    const root = document.documentElement
    
    // High contrast mode
    if (preferences.highContrast) {
      root.classList.add('high-contrast')
    } else {
      root.classList.remove('high-contrast')
    }
    
    // Reduced motion
    if (preferences.reducedMotion) {
      root.classList.add('reduced-motion')
    } else {
      root.classList.remove('reduced-motion')
    }
    
    // Font size
    root.classList.remove('font-small', 'font-medium', 'font-large', 'font-extra-large')
    root.classList.add(`font-${preferences.fontSize}`)
    
    // Focus visible
    if (preferences.focusVisible) {
      root.classList.add('focus-visible')
    } else {
      root.classList.remove('focus-visible')
    }
    
    // Keyboard navigation
    if (preferences.keyboardNavigation) {
      root.classList.add('keyboard-navigation')
    } else {
      root.classList.remove('keyboard-navigation')
    }
  }, [preferences])

  // Screen reader announcement
  const announce = useCallback((message: string, options: AnnouncementOptions = { priority: 'polite' }) => {
    if (!preferences.announcements) return

    if (options.clear) {
      setAnnouncementQueue([])
    }

    const announceMessage = () => {
      setAnnouncementQueue(prev => [...prev, message])
      
      // Clear after announcement
      setTimeout(() => {
        setAnnouncementQueue(prev => prev.filter(msg => msg !== message))
      }, 1000)
    }

    if (options.delay) {
      setTimeout(announceMessage, options.delay)
    } else {
      announceMessage()
    }
  }, [preferences.announcements])

  // Get focusable elements
  const getFocusableElements = useCallback((container: HTMLElement = document.body): HTMLElement[] => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]'
    ].join(', ')

    return Array.from(container.querySelectorAll(focusableSelectors))
      .filter(el => {
        const element = el as HTMLElement
        return element.offsetWidth > 0 && 
               element.offsetHeight > 0 && 
               !element.hidden &&
               window.getComputedStyle(element).visibility !== 'hidden'
      }) as HTMLElement[]
  }, [])

  // Focus management
  const manageFocus = useCallback((container?: HTMLElement) => {
    const elements = getFocusableElements(container)
    setFocusManager(prev => ({
      ...prev,
      focusableElements: elements,
      currentFocusIndex: elements.length > 0 ? 0 : -1
    }))
    return elements
  }, [getFocusableElements])

  // Trap focus within container
  const trapFocus = useCallback((container: HTMLElement, enable: boolean = true) => {
    const elements = getFocusableElements(container)
    
    if (enable) {
      setFocusManager(prev => ({
        ...prev,
        trapFocus: true,
        focusableElements: elements,
        previousFocus: document.activeElement as HTMLElement
      }))
      
      // Focus first element
      if (elements.length > 0) {
        elements[0].focus()
      }
    } else {
      setFocusManager(prev => {
        // Restore previous focus
        if (prev.restoreFocus && prev.previousFocus) {
          prev.previousFocus.focus()
        }
        
        return {
          ...prev,
          trapFocus: false,
          focusableElements: [],
          previousFocus: undefined
        }
      })
    }
  }, [getFocusableElements])

  // Keyboard navigation handler
  const handleKeyboardNavigation = useCallback((
    event: KeyboardEvent,
    elements: HTMLElement[],
    options: Partial<KeyboardNavigation> = {}
  ) => {
    if (!preferences.keyboardNavigation || elements.length === 0) return false

    const {
      direction = 'horizontal',
      wrap = true,
      skipDisabled = true
    } = options

    const currentIndex = elements.findIndex(el => el === document.activeElement)
    let nextIndex = currentIndex

    switch (event.key) {
      case 'ArrowRight':
        if (direction === 'horizontal' || direction === 'grid') {
          nextIndex = currentIndex + 1
        }
        break
      case 'ArrowLeft':
        if (direction === 'horizontal' || direction === 'grid') {
          nextIndex = currentIndex - 1
        }
        break
      case 'ArrowDown':
        if (direction === 'vertical' || direction === 'grid') {
          nextIndex = currentIndex + 1
        }
        break
      case 'ArrowUp':
        if (direction === 'vertical' || direction === 'grid') {
          nextIndex = currentIndex - 1
        }
        break
      case 'Home':
        nextIndex = 0
        break
      case 'End':
        nextIndex = elements.length - 1
        break
      case 'Tab':
        // Let browser handle tab navigation
        return false
      default:
        return false
    }

    // Handle wrapping
    if (wrap) {
      if (nextIndex >= elements.length) nextIndex = 0
      if (nextIndex < 0) nextIndex = elements.length - 1
    } else {
      if (nextIndex >= elements.length || nextIndex < 0) return false
    }

    // Skip disabled elements
    if (skipDisabled) {
      let attempts = 0
      while (attempts < elements.length) {
        const element = elements[nextIndex]
        if (!element.hasAttribute('disabled') && !element.hasAttribute('aria-disabled')) {
          break
        }
        nextIndex = wrap ? (nextIndex + 1) % elements.length : nextIndex + 1
        attempts++
      }
    }

    // Focus the element
    if (nextIndex >= 0 && nextIndex < elements.length) {
      event.preventDefault()
      elements[nextIndex].focus()
      return true
    }

    return false
  }, [preferences.keyboardNavigation])

  // ARIA live region for announcements
  const AriaLiveRegion = useCallback(() => (
    <div
      ref={announcementRef}
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {announcementQueue.map((message, index) => (
        <div key={index}>{message}</div>
      ))}
    </div>
  ), [announcementQueue])

  // Skip link component
  const SkipLink = useCallback(({ href, children }: { href: string; children: React.ReactNode }) => (
    <a
      href={href}
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg"
      onFocus={() => announce('Skip link focused')}
    >
      {children}
    </a>
  ), [announce])

  return {
    // State
    preferences,
    focusManager,
    isScreenReaderActive: preferences.screenReader,
    isHighContrast: preferences.highContrast,
    isReducedMotion: preferences.reducedMotion,
    
    // Actions
    updatePreferences,
    announce,
    manageFocus,
    trapFocus,
    handleKeyboardNavigation,
    getFocusableElements,
    
    // Components
    AriaLiveRegion,
    SkipLink,
    
    // Utilities
    responsive
  }
}

// Hook for managing focus within a specific component
export function useFocusManagement(containerRef: React.RefObject<HTMLElement>) {
  const { getFocusableElements, handleKeyboardNavigation } = useAccessibility()
  const [focusableElements, setFocusableElements] = useState<HTMLElement[]>([])

  useEffect(() => {
    if (containerRef.current) {
      const elements = getFocusableElements(containerRef.current)
      setFocusableElements(elements)
    }
  }, [containerRef, getFocusableElements])

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    handleKeyboardNavigation(event.nativeEvent, focusableElements)
  }, [handleKeyboardNavigation, focusableElements])

  return {
    focusableElements,
    handleKeyDown
  }
}

// Hook for ARIA announcements
export function useAnnouncements() {
  const { announce } = useAccessibility()
  
  const announceNavigation = useCallback((location: string) => {
    announce(`Navigated to ${location}`, { priority: 'polite' })
  }, [announce])
  
  const announceAction = useCallback((action: string) => {
    announce(action, { priority: 'assertive' })
  }, [announce])
  
  const announceError = useCallback((error: string) => {
    announce(`Error: ${error}`, { priority: 'assertive' })
  }, [announce])
  
  const announceSuccess = useCallback((message: string) => {
    announce(`Success: ${message}`, { priority: 'polite' })
  }, [announce])

  return {
    announce,
    announceNavigation,
    announceAction,
    announceError,
    announceSuccess
  }
}