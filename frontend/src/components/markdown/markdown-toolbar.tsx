"use client"

import { useCallback, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Bold, 
  Italic, 
  Heading1, 
  Heading2, 
  Heading3, 
  List, 
  ListOrdered, 
  Link, 
  Code, 
  Quote
} from 'lucide-react'
import { cn } from '@/lib/utils'

export type FormatType = 
  | 'bold' 
  | 'italic' 
  | 'heading1' 
  | 'heading2' 
  | 'heading3'
  | 'unordered-list' 
  | 'ordered-list' 
  | 'link' 
  | 'code' 
  | 'quote'

interface MarkdownToolbarProps {
  onFormat: (type: FormatType, text?: string) => void
  disabled?: boolean
  className?: string
}

interface FormatAction {
  type: FormatType
  icon: React.ComponentType<{ className?: string }>
  label: string
  shortcut?: string
  action: (selectedText: string) => { before: string; after: string; placeholder?: string }
}

export function MarkdownToolbar({ onFormat, disabled = false, className }: MarkdownToolbarProps) {
  const toolbarRef = useRef<HTMLDivElement>(null)

  // Define format actions
  const formatActions: FormatAction[] = [
    {
      type: 'bold',
      icon: Bold,
      label: '加粗',
      shortcut: 'Ctrl+B',
      action: (text) => ({
        before: '**',
        after: '**',
        placeholder: text || '加粗文本'
      })
    },
    {
      type: 'italic',
      icon: Italic,
      label: '斜体',
      shortcut: 'Ctrl+I',
      action: (text) => ({
        before: '*',
        after: '*',
        placeholder: text || '斜体文本'
      })
    },
    {
      type: 'heading1',
      icon: Heading1,
      label: '一级标题',
      shortcut: 'Ctrl+1',
      action: (text) => ({
        before: '# ',
        after: '',
        placeholder: text || '一级标题'
      })
    },
    {
      type: 'heading2',
      icon: Heading2,
      label: '二级标题',
      shortcut: 'Ctrl+2',
      action: (text) => ({
        before: '## ',
        after: '',
        placeholder: text || '二级标题'
      })
    },
    {
      type: 'heading3',
      icon: Heading3,
      label: '三级标题',
      shortcut: 'Ctrl+3',
      action: (text) => ({
        before: '### ',
        after: '',
        placeholder: text || '三级标题'
      })
    },
    {
      type: 'unordered-list',
      icon: List,
      label: '无序列表',
      shortcut: 'Ctrl+U',
      action: (text) => ({
        before: '- ',
        after: '',
        placeholder: text || '列表项'
      })
    },
    {
      type: 'ordered-list',
      icon: ListOrdered,
      label: '有序列表',
      shortcut: 'Ctrl+O',
      action: (text) => ({
        before: '1. ',
        after: '',
        placeholder: text || '列表项'
      })
    },
    {
      type: 'link',
      icon: Link,
      label: '链接',
      shortcut: 'Ctrl+K',
      action: (text) => ({
        before: '[',
        after: '](url)',
        placeholder: text || '链接文本'
      })
    },
    {
      type: 'code',
      icon: Code,
      label: '代码',
      shortcut: 'Ctrl+`',
      action: (text) => ({
        before: '`',
        after: '`',
        placeholder: text || '代码'
      })
    },
    {
      type: 'quote',
      icon: Quote,
      label: '引用',
      shortcut: 'Ctrl+Q',
      action: (text) => ({
        before: '> ',
        after: '',
        placeholder: text || '引用内容'
      })
    }
  ]

  // Handle format button click
  const handleFormatClick = useCallback((action: FormatAction) => {
    if (disabled) return
    
    // Get the currently focused textarea
    const activeElement = document.activeElement as HTMLTextAreaElement
    if (!activeElement || activeElement.tagName !== 'TEXTAREA') {
      // If no textarea is focused, just call onFormat with empty text
      onFormat(action.type, '')
      return
    }

    const start = activeElement.selectionStart
    const end = activeElement.selectionEnd
    const selectedText = activeElement.value.substring(start, end)
    
    const { before, after, placeholder } = action.action(selectedText)
    const textToInsert = selectedText || placeholder || ''
    const fullText = before + textToInsert + after
    
    // Insert the formatted text
    const newValue = 
      activeElement.value.substring(0, start) + 
      fullText + 
      activeElement.value.substring(end)
    
    // Update the textarea value
    activeElement.value = newValue
    
    // Set cursor position
    const newCursorPos = selectedText 
      ? start + fullText.length 
      : start + before.length + textToInsert.length
    
    activeElement.selectionStart = selectedText ? start + before.length : newCursorPos
    activeElement.selectionEnd = selectedText ? start + before.length + textToInsert.length : newCursorPos
    
    // Focus back to textarea
    activeElement.focus()
    
    // Trigger change event
    const event = new Event('input', { bubbles: true })
    activeElement.dispatchEvent(event)
    
    // Call the onFormat callback
    onFormat(action.type, fullText)
  }, [disabled, onFormat])

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (disabled) return
    
    const isCtrlOrCmd = e.ctrlKey || e.metaKey
    if (!isCtrlOrCmd) return

    // Find matching format action by shortcut
    const action = formatActions.find(action => {
      if (!action.shortcut) return false
      
      const shortcutKey = action.shortcut.split('+').pop()?.toLowerCase()
      const eventKey = e.key.toLowerCase()
      
      if (!shortcutKey) return false
      
      // Handle special cases
      if (shortcutKey === '`' && eventKey === '`') return true
      if (shortcutKey === eventKey) return true
      
      // Handle number keys for headings
      if (['1', '2', '3'].includes(shortcutKey) && eventKey === shortcutKey) return true
      
      return false
    })

    if (action) {
      e.preventDefault()
      handleFormatClick(action)
    }
  }, [disabled, formatActions, handleFormatClick])

  // Add global keyboard event listener
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div 
      ref={toolbarRef}
      className={cn(
        "flex items-center space-x-1 p-2 border-b bg-card/50 backdrop-blur-sm",
        disabled && "opacity-50 pointer-events-none",
        className
      )}
    >
      {/* Text formatting group */}
      <div className="flex items-center space-x-1">
        {formatActions.slice(0, 2).map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.type}
              variant="ghost"
              size="sm"
              onClick={() => handleFormatClick(action)}
              disabled={disabled}
              title={`${action.label} (${action.shortcut})`}
              className="h-8 w-8 p-0"
            >
              <Icon className="h-4 w-4" />
            </Button>
          )
        })}
      </div>

      <div className="w-px h-6 bg-border" />

      {/* Heading group */}
      <div className="flex items-center space-x-1">
        {formatActions.slice(2, 5).map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.type}
              variant="ghost"
              size="sm"
              onClick={() => handleFormatClick(action)}
              disabled={disabled}
              title={`${action.label} (${action.shortcut})`}
              className="h-8 w-8 p-0"
            >
              <Icon className="h-4 w-4" />
            </Button>
          )
        })}
      </div>

      <div className="w-px h-6 bg-border" />

      {/* List group */}
      <div className="flex items-center space-x-1">
        {formatActions.slice(5, 7).map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.type}
              variant="ghost"
              size="sm"
              onClick={() => handleFormatClick(action)}
              disabled={disabled}
              title={`${action.label} (${action.shortcut})`}
              className="h-8 w-8 p-0"
            >
              <Icon className="h-4 w-4" />
            </Button>
          )
        })}
      </div>

      <div className="w-px h-6 bg-border" />

      {/* Other formatting group */}
      <div className="flex items-center space-x-1">
        {formatActions.slice(7).map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.type}
              variant="ghost"
              size="sm"
              onClick={() => handleFormatClick(action)}
              disabled={disabled}
              title={`${action.label} (${action.shortcut})`}
              className="h-8 w-8 p-0"
            >
              <Icon className="h-4 w-4" />
            </Button>
          )
        })}
      </div>
    </div>
  )
}