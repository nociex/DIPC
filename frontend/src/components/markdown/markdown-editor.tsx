"use client"

import { useRef, useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { MarkdownToolbar, type FormatType } from './markdown-toolbar'

interface MarkdownEditorProps {
  value: string
  onChange: (value: string, operationType?: 'manual' | 'paste' | 'format') => void
  placeholder?: string
  className?: string
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  readOnly?: boolean
  showToolbar?: boolean
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = "在此编辑Markdown内容...",
  className,
  onKeyDown,
  readOnly = false,
  showToolbar = true
}: MarkdownEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [lineNumbers, setLineNumbers] = useState<number[]>([])

  // Update line numbers when content changes
  useEffect(() => {
    const lines = value.split('\n').length
    setLineNumbers(Array.from({ length: lines }, (_, i) => i + 1))
  }, [value])

  // Handle toolbar format actions
  const handleFormat = useCallback((type: FormatType, text?: string) => {
    const textarea = textareaRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = textarea.value.substring(start, end)
    
    let before = ''
    let after = ''
    let placeholder = ''

    // Define format patterns
    switch (type) {
      case 'bold':
        before = '**'
        after = '**'
        placeholder = selectedText || '加粗文本'
        break
      case 'italic':
        before = '*'
        after = '*'
        placeholder = selectedText || '斜体文本'
        break
      case 'heading1':
        before = '# '
        after = ''
        placeholder = selectedText || '一级标题'
        break
      case 'heading2':
        before = '## '
        after = ''
        placeholder = selectedText || '二级标题'
        break
      case 'heading3':
        before = '### '
        after = ''
        placeholder = selectedText || '三级标题'
        break
      case 'unordered-list':
        before = '- '
        after = ''
        placeholder = selectedText || '列表项'
        break
      case 'ordered-list':
        before = '1. '
        after = ''
        placeholder = selectedText || '列表项'
        break
      case 'link':
        before = '['
        after = '](url)'
        placeholder = selectedText || '链接文本'
        break
      case 'code':
        before = '`'
        after = '`'
        placeholder = selectedText || '代码'
        break
      case 'quote':
        before = '> '
        after = ''
        placeholder = selectedText || '引用内容'
        break
    }

    const textToInsert = selectedText || placeholder
    const fullText = before + textToInsert + after
    
    // Insert the formatted text
    const newValue = 
      value.substring(0, start) + 
      fullText + 
      value.substring(end)
    
    onChange(newValue, 'format')
    
    // Set cursor position after insertion
    setTimeout(() => {
      if (selectedText) {
        // If text was selected, select the formatted text
        textarea.selectionStart = start + before.length
        textarea.selectionEnd = start + before.length + textToInsert.length
      } else {
        // If no text was selected, position cursor after the placeholder
        const newCursorPos = start + before.length + textToInsert.length
        textarea.selectionStart = textarea.selectionEnd = newCursorPos
      }
      textarea.focus()
    }, 0)
  }, [value, onChange])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value, 'manual')
  }, [onChange])
  
  const handlePaste = useCallback((e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    // Let the default paste happen, then mark it as paste operation
    setTimeout(() => {
      const textarea = e.currentTarget
      onChange(textarea.value, 'paste')
    }, 0)
  }, [onChange])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle tab insertion
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = e.currentTarget
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newValue = value.substring(0, start) + '  ' + value.substring(end)
      onChange(newValue, 'format')
      
      // Set cursor position after the inserted tab
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2
      }, 0)
      return
    }

    // Handle enter key for list continuation
    if (e.key === 'Enter') {
      const textarea = e.currentTarget
      const start = textarea.selectionStart
      const lines = value.substring(0, start).split('\n')
      const currentLine = lines[lines.length - 1]
      
      // Check for list patterns
      const unorderedListMatch = currentLine.match(/^(\s*)([-*+])\s/)
      const orderedListMatch = currentLine.match(/^(\s*)(\d+)\.\s/)
      
      if (unorderedListMatch) {
        e.preventDefault()
        const [, indent, bullet] = unorderedListMatch
        const newValue = value.substring(0, start) + '\n' + indent + bullet + ' ' + value.substring(start)
        onChange(newValue, 'format')
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + indent.length + bullet.length + 2
        }, 0)
        return
      }
      
      if (orderedListMatch) {
        e.preventDefault()
        const [, indent, number] = orderedListMatch
        const nextNumber = parseInt(number) + 1
        const newValue = value.substring(0, start) + '\n' + indent + nextNumber + '. ' + value.substring(start)
        onChange(newValue, 'format')
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + indent.length + nextNumber.toString().length + 3
        }, 0)
        return
      }
    }

    onKeyDown?.(e)
  }, [value, onChange, onKeyDown])

  const handleScroll = useCallback((e: React.UIEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget
    const lineNumbersEl = textarea.parentElement?.querySelector('.line-numbers') as HTMLElement
    if (lineNumbersEl) {
      lineNumbersEl.scrollTop = textarea.scrollTop
    }
  }, [])

  return (
    <div className={cn("relative flex flex-col h-full bg-card border rounded-md shadow-sm", className)}>
      {/* Toolbar */}
      {showToolbar && !readOnly && (
        <MarkdownToolbar 
          onFormat={handleFormat}
          disabled={readOnly}
          className="border-b bg-card/50"
        />
      )}
      
      {/* Editor Container */}
      <div className="flex flex-1 min-h-0">
        {/* Line Numbers */}
        <div className="line-numbers flex-shrink-0 w-12 bg-muted/20 border-r text-xs text-muted-foreground font-mono overflow-hidden">
          <div className="py-3 px-2 leading-6">
            {lineNumbers.map((num) => (
              <div key={num} className="text-right select-none">
                {num}
              </div>
            ))}
          </div>
        </div>

        {/* Editor */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          onScroll={handleScroll}
          placeholder={placeholder}
          readOnly={readOnly}
          className={cn(
            "flex-1 p-3 bg-transparent border-0 resize-none focus:outline-none font-mono text-sm leading-6",
            "placeholder:text-muted-foreground text-foreground",
            "focus:ring-0 focus:ring-offset-0",
            readOnly && "cursor-default"
          )}
          spellCheck={false}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
        />
      </div>
    </div>
  )
}