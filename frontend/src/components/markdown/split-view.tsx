"use client"

import { useState, useRef, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface SplitViewProps {
  leftPanel: React.ReactNode
  rightPanel: React.ReactNode
  defaultSplitPosition?: number
  minPaneSize?: number
  className?: string
  onSplitChange?: (position: number) => void
}

export function SplitView({
  leftPanel,
  rightPanel,
  defaultSplitPosition = 50,
  minPaneSize = 20,
  className,
  onSplitChange
}: SplitViewProps) {
  const [splitPosition, setSplitPosition] = useState(defaultSplitPosition)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const resizerRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return

    const containerRect = containerRef.current.getBoundingClientRect()
    const newPosition = ((e.clientX - containerRect.left) / containerRect.width) * 100
    
    // Constrain the position within min/max bounds
    const constrainedPosition = Math.max(minPaneSize, Math.min(100 - minPaneSize, newPosition))
    
    setSplitPosition(constrainedPosition)
    onSplitChange?.(constrainedPosition)
  }, [isDragging, minPaneSize, onSplitChange])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  return (
    <div 
      ref={containerRef}
      className={cn("flex h-full w-full relative", className)}
    >
      {/* Left Panel */}
      <div 
        className="flex-shrink-0 overflow-hidden"
        style={{ width: `${splitPosition}%` }}
      >
        {leftPanel}
      </div>

      {/* Resizer */}
      <div
        ref={resizerRef}
        className={cn(
          "w-1 bg-border hover:bg-primary/20 cursor-col-resize flex-shrink-0 relative group transition-colors",
          isDragging && "bg-primary/30"
        )}
        onMouseDown={handleMouseDown}
      >
        <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-primary/10" />
      </div>

      {/* Right Panel */}
      <div 
        className="flex-1 overflow-hidden"
        style={{ width: `${100 - splitPosition}%` }}
      >
        {rightPanel}
      </div>
    </div>
  )
}