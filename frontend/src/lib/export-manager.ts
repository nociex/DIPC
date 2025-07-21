/**
 * Export Manager - Handles file export functionality for markdown content
 */

export interface ExportOptions {
  format: 'markdown' | 'html'
  filename?: string
  includeMetadata?: boolean
}

export interface ExportResult {
  content: string
  filename: string
  mimeType: string
}

export class ExportManager {
  /**
   * Export content as markdown file
   */
  static async exportMarkdown(content: string, filename?: string): Promise<void> {
    try {
      const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      
      const link = document.createElement('a')
      link.href = url
      link.download = filename || `markdown-export-${Date.now()}.md`
      link.style.display = 'none'
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up the URL object
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export markdown:', error)
      throw new Error('导出Markdown文件失败')
    }
  }

  /**
   * Export content as HTML file
   */
  static async exportHtml(markdownContent: string, filename?: string): Promise<void> {
    try {
      const htmlContent = this.markdownToHtml(markdownContent)
      const fullHtml = this.wrapInHtmlDocument(htmlContent)
      
      const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      
      const link = document.createElement('a')
      link.href = url
      link.download = filename || `markdown-export-${Date.now()}.html`
      link.style.display = 'none'
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Clean up the URL object
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export HTML:', error)
      throw new Error('导出HTML文件失败')
    }
  }

  /**
   * Copy content to clipboard
   */
  static async copyToClipboard(content: string): Promise<void> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        // Use modern clipboard API
        await navigator.clipboard.writeText(content)
      } else {
        // Fallback for older browsers or non-secure contexts
        await this.fallbackCopyToClipboard(content)
      }
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
      throw new Error('复制到剪贴板失败')
    }
  }

  /**
   * Fallback copy method for older browsers
   */
  private static async fallbackCopyToClipboard(content: string): Promise<void> {
    const textArea = document.createElement('textarea')
    textArea.value = content
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    
    try {
      const successful = document.execCommand('copy')
      if (!successful) {
        throw new Error('Copy command failed')
      }
    } finally {
      document.body.removeChild(textArea)
    }
  }

  /**
   * Convert markdown to HTML (basic conversion)
   */
  private static markdownToHtml(markdown: string): string {
    return markdown
      // Headers
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      
      // Bold and italic
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      
      // Code blocks (basic)
      .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
      .replace(/`(.*?)`/gim, '<code>$1</code>')
      
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>')
      
      // Lists
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
      
      // Blockquotes
      .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
      
      // Line breaks and paragraphs
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br>')
      
      // Wrap in paragraphs (basic)
      .split('</p><p>')
      .map(paragraph => paragraph.trim())
      .filter(paragraph => paragraph.length > 0)
      .map(paragraph => {
        // Don't wrap headers, lists, blockquotes, or code blocks in paragraphs
        if (paragraph.match(/^<(h[1-6]|li|blockquote|pre)/)) {
          return paragraph
        }
        return `<p>${paragraph}</p>`
      })
      .join('\n')
      
      // Clean up list formatting
      .replace(/(<li>.*<\/li>)/gims, (match) => {
        // Check if this is part of an unordered list
        if (match.includes('<li>') && !match.includes('<ol>') && !match.includes('<ul>')) {
          return `<ul>${match}</ul>`
        }
        return match
      })
  }

  /**
   * Wrap HTML content in a complete HTML document
   */
  private static wrapInHtmlDocument(content: string): string {
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown Export</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
            line-height: 1.6; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            color: #333;
        }
        h1, h2, h3, h4, h5, h6 { 
            color: #2c3e50; 
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
        h3 { font-size: 1.25em; }
        
        p { margin-bottom: 1em; }
        
        code { 
            background-color: #f8f9fa; 
            padding: 0.2em 0.4em; 
            border-radius: 3px; 
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
        }
        
        pre { 
            background-color: #f8f9fa; 
            padding: 1em; 
            border-radius: 5px; 
            overflow-x: auto;
            border-left: 4px solid #007acc;
        }
        
        pre code { 
            background: none; 
            padding: 0; 
        }
        
        blockquote { 
            border-left: 4px solid #ddd; 
            margin: 1em 0; 
            padding-left: 1em; 
            color: #666;
            font-style: italic;
        }
        
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 1em 0;
        }
        
        th, td { 
            border: 1px solid #ddd; 
            padding: 8px 12px; 
            text-align: left; 
        }
        
        th { 
            background-color: #f2f2f2; 
            font-weight: bold;
        }
        
        ul, ol { 
            margin: 1em 0; 
            padding-left: 2em; 
        }
        
        li { 
            margin-bottom: 0.5em; 
        }
        
        a { 
            color: #007acc; 
            text-decoration: none; 
        }
        
        a:hover { 
            text-decoration: underline; 
        }
        
        .export-info {
            border-top: 1px solid #eee;
            margin-top: 2em;
            padding-top: 1em;
            font-size: 0.9em;
            color: #666;
            text-align: center;
        }
    </style>
</head>
<body>
    ${content}
    <div class="export-info">
        <p>导出时间: ${new Date().toLocaleString('zh-CN')}</p>
        <p>由文档智能解析中心生成</p>
    </div>
</body>
</html>`
  }

  /**
   * Generate filename based on task ID and current timestamp
   */
  static generateFilename(taskId: string, format: 'markdown' | 'html'): string {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')
    const shortTaskId = taskId.length > 8 ? taskId.slice(0, 8) : taskId
    const extension = format === 'markdown' ? 'md' : 'html'
    
    return `task-${shortTaskId}-${timestamp}.${extension}`
  }

  /**
   * Check if clipboard API is supported
   */
  static isClipboardSupported(): boolean {
    return !!(navigator.clipboard && window.isSecureContext) || !!(document.queryCommandSupported && document.queryCommandSupported('copy'))
  }

  /**
   * Check if file download is supported
   */
  static isDownloadSupported(): boolean {
    return !!(document.createElement('a').download !== undefined)
  }
}