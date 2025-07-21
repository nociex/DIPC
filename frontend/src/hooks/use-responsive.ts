"use client"

import { useState, useEffect } from 'react'

// Responsive breakpoints matching Tailwind defaults
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536
} as const

export type Breakpoint = keyof typeof BREAKPOINTS

// Device types for better UX decisions
export type DeviceType = 'mobile' | 'tablet' | 'desktop'

// Touch capability detection
export type TouchCapability = 'touch' | 'no-touch' | 'hybrid'

// Orientation detection
export type Orientation = 'portrait' | 'landscape'

export interface ResponsiveState {
  // Screen dimensions
  width: number
  height: number
  
  // Breakpoint information
  currentBreakpoint: Breakpoint
  isSmallScreen: boolean
  isMediumScreen: boolean
  isLargeScreen: boolean
  
  // Device type
  deviceType: DeviceType
  
  // Touch capabilities
  touchCapability: TouchCapability
  isTouchDevice: boolean
  
  // Orientation
  orientation: Orientation
  
  // Utility functions
  isBreakpoint: (breakpoint: Breakpoint) => boolean
  isAboveBreakpoint: (breakpoint: Breakpoint) => boolean
  isBelowBreakpoint: (breakpoint: Breakpoint) => boolean
}

// Detect touch capability
function detectTouchCapability(): TouchCapability {
  if (typeof window === 'undefined') return 'no-touch'
  
  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0
  const hasPointer = window.matchMedia('(pointer: coarse)').matches
  const hasFinePointer = window.matchMedia('(pointer: fine)').matches
  
  if (hasTouch && hasFinePointer) return 'hybrid'
  if (hasTouch || hasPointer) return 'touch'
  return 'no-touch'
}

// Determine device type based on screen size and touch capability
function getDeviceType(width: number, touchCapability: TouchCapability): DeviceType {
  if (width < BREAKPOINTS.md) return 'mobile'
  if (width < BREAKPOINTS.lg && touchCapability === 'touch') return 'tablet'
  if (width < BREAKPOINTS.xl) return 'tablet'
  return 'desktop'
}

// Get current breakpoint
function getCurrentBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS['2xl']) return '2xl'
  if (width >= BREAKPOINTS.xl) return 'xl'
  if (width >= BREAKPOINTS.lg) return 'lg'
  if (width >= BREAKPOINTS.md) return 'md'
  return 'sm'
}

// Get orientation
function getOrientation(width: number, height: number): Orientation {
  return width > height ? 'landscape' : 'portrait'
}

export function useResponsive(): ResponsiveState {
  const [state, setState] = useState<ResponsiveState>(() => {
    // Initialize with safe defaults for SSR
    const initialWidth = typeof window !== 'undefined' ? window.innerWidth : 1024
    const initialHeight = typeof window !== 'undefined' ? window.innerHeight : 768
    const touchCapability = detectTouchCapability()
    const currentBreakpoint = getCurrentBreakpoint(initialWidth)
    const deviceType = getDeviceType(initialWidth, touchCapability)
    const orientation = getOrientation(initialWidth, initialHeight)
    
    return {
      width: initialWidth,
      height: initialHeight,
      currentBreakpoint,
      isSmallScreen: initialWidth < BREAKPOINTS.md,
      isMediumScreen: initialWidth >= BREAKPOINTS.md && initialWidth < BREAKPOINTS.lg,
      isLargeScreen: initialWidth >= BREAKPOINTS.lg,
      deviceType,
      touchCapability,
      isTouchDevice: touchCapability !== 'no-touch',
      orientation,
      isBreakpoint: (breakpoint: Breakpoint) => currentBreakpoint === breakpoint,
      isAboveBreakpoint: (breakpoint: Breakpoint) => initialWidth >= BREAKPOINTS[breakpoint],
      isBelowBreakpoint: (breakpoint: Breakpoint) => initialWidth < BREAKPOINTS[breakpoint]
    }
  })

  useEffect(() => {
    if (typeof window === 'undefined') return

    const updateState = () => {
      const width = window.innerWidth
      const height = window.innerHeight
      const touchCapability = detectTouchCapability()
      const currentBreakpoint = getCurrentBreakpoint(width)
      const deviceType = getDeviceType(width, touchCapability)
      const orientation = getOrientation(width, height)
      
      setState({
        width,
        height,
        currentBreakpoint,
        isSmallScreen: width < BREAKPOINTS.md,
        isMediumScreen: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
        isLargeScreen: width >= BREAKPOINTS.lg,
        deviceType,
        touchCapability,
        isTouchDevice: touchCapability !== 'no-touch',
        orientation,
        isBreakpoint: (breakpoint: Breakpoint) => currentBreakpoint === breakpoint,
        isAboveBreakpoint: (breakpoint: Breakpoint) => width >= BREAKPOINTS[breakpoint],
        isBelowBreakpoint: (breakpoint: Breakpoint) => width < BREAKPOINTS[breakpoint]
      })
    }

    // Update on resize
    window.addEventListener('resize', updateState)
    
    // Update on orientation change
    window.addEventListener('orientationchange', updateState)
    
    // Initial update
    updateState()

    return () => {
      window.removeEventListener('resize', updateState)
      window.removeEventListener('orientationchange', updateState)
    }
  }, [])

  return state
}

// Hook for media queries
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const mediaQuery = window.matchMedia(query)
    setMatches(mediaQuery.matches)

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches)
    }

    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [query])

  return matches
}

// Predefined media query hooks
export const useIsMobile = () => useMediaQuery(`(max-width: ${BREAKPOINTS.md - 1}px)`)
export const useIsTablet = () => useMediaQuery(`(min-width: ${BREAKPOINTS.md}px) and (max-width: ${BREAKPOINTS.lg - 1}px)`)
export const useIsDesktop = () => useMediaQuery(`(min-width: ${BREAKPOINTS.lg}px)`)
export const useIsTouchDevice = () => useMediaQuery('(pointer: coarse)')
export const useIsLandscape = () => useMediaQuery('(orientation: landscape)')
export const useIsPortrait = () => useMediaQuery('(orientation: portrait)')
export const usePrefersReducedMotion = () => useMediaQuery('(prefers-reduced-motion: reduce)')